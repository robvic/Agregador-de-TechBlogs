import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from scripts.models import Source


class ConfigurationError(ValueError):
    """Erro de formato ou valor nos arquivos de configuracao."""


@dataclass(frozen=True)
class EmailConfig:
    smtp_host: str
    smtp_port: int
    use_starttls: bool
    recipient: str


@dataclass(frozen=True)
class LlmConfig:
    command: str
    arguments: tuple[str, ...]
    timeout_seconds: int


@dataclass(frozen=True)
class AppConfig:
    frequency_days: int
    database_path: Path
    request_timeout_seconds: int
    max_posts_per_source: int
    max_article_characters: int
    user_agent: str
    categories: tuple[str, ...]
    email: EmailConfig
    llm: LlmConfig


def _read_json(path: Path) -> Any:
    try:
        with path.open(encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError as error:
        raise ConfigurationError(f"Arquivo de configuracao nao encontrado: {path}") from error
    except json.JSONDecodeError as error:
        raise ConfigurationError(
            f"JSON invalido em {path}, linha {error.lineno}, coluna {error.colno}: {error.msg}"
        ) from error


def _positive_int(data: dict[str, Any], key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ConfigurationError(f"'{key}' deve ser um numero inteiro maior que zero.")
    return value


def load_config(config_path: Path, sources_path: Path) -> tuple[AppConfig, list[Source]]:
    raw = _read_json(config_path)
    if not isinstance(raw, dict):
        raise ConfigurationError(f"A configuracao principal em {config_path} deve ser um objeto JSON.")

    categories = raw.get("categories")
    if not isinstance(categories, list) or not categories or not all(
        isinstance(item, str) and item.strip() for item in categories
    ):
        raise ConfigurationError("'categories' deve ser uma lista nao vazia de textos.")
    if len({item.strip() for item in categories}) != len(categories):
        raise ConfigurationError("'categories' nao deve conter categorias duplicadas.")

    email_data = raw.get("email")
    if not isinstance(email_data, dict):
        raise ConfigurationError("'email' deve ser um objeto de configuracao.")

    llm_data = raw.get("llm")
    if not isinstance(llm_data, dict):
        raise ConfigurationError("'llm' deve ser um objeto de configuracao.")
    arguments = llm_data.get("arguments")
    if not isinstance(arguments, list) or not all(isinstance(item, str) for item in arguments):
        raise ConfigurationError("'llm.arguments' deve ser uma lista de textos.")
    if not any("{prompt}" in item for item in arguments):
        raise ConfigurationError("'llm.arguments' deve incluir o marcador {prompt}.")

    database_path = raw.get("database_path")
    user_agent = raw.get("user_agent")
    command = llm_data.get("command")
    if not isinstance(database_path, str) or not database_path.strip():
        raise ConfigurationError("'database_path' deve ser um caminho nao vazio.")
    if not isinstance(user_agent, str) or not user_agent.strip():
        raise ConfigurationError("'user_agent' deve ser um texto nao vazio.")
    if not isinstance(command, str) or not command.strip():
        raise ConfigurationError("'llm.command' deve ser um comando nao vazio.")

    smtp_host = email_data.get("smtp_host")
    recipient = email_data.get("recipient")
    smtp_port = email_data.get("smtp_port")
    starttls = email_data.get("use_starttls")
    if not isinstance(smtp_host, str) or not smtp_host.strip():
        raise ConfigurationError("'email.smtp_host' deve ser um texto nao vazio.")
    if not isinstance(smtp_port, int) or isinstance(smtp_port, bool) or not 1 <= smtp_port <= 65535:
        raise ConfigurationError("'email.smtp_port' deve ser um numero entre 1 e 65535.")
    if not isinstance(starttls, bool):
        raise ConfigurationError("'email.use_starttls' deve ser booleano.")
    if not isinstance(recipient, str):
        raise ConfigurationError("'email.recipient' deve ser um texto.")

    app_config = AppConfig(
        frequency_days=_positive_int(raw, "frequency_days"),
        database_path=Path(database_path),
        request_timeout_seconds=_positive_int(raw, "request_timeout_seconds"),
        max_posts_per_source=_positive_int(raw, "max_posts_per_source"),
        max_article_characters=_positive_int(raw, "max_article_characters"),
        user_agent=user_agent.strip(),
        categories=tuple(category.strip() for category in categories),
        email=EmailConfig(smtp_host.strip(), smtp_port, starttls, recipient.strip()),
        llm=LlmConfig(
            command=command.strip(),
            arguments=tuple(arguments),
            timeout_seconds=_positive_int(llm_data, "timeout_seconds"),
        ),
    )

    raw_sources = _read_json(sources_path)
    if not isinstance(raw_sources, list) or not raw_sources:
        raise ConfigurationError(f"As fontes em {sources_path} devem ser uma lista nao vazia.")

    required_source_fields = (
        "id",
        "name",
        "url",
        "article_selector",
        "title_selector",
        "link_selector",
        "date_selector",
        "content_selector",
    )
    sources: list[Source] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(raw_sources):
        if not isinstance(item, dict):
            raise ConfigurationError(f"A fonte de indice {index} deve ser um objeto JSON.")
        missing = [field for field in required_source_fields if not isinstance(item.get(field), str)]
        if missing:
            raise ConfigurationError(
                f"A fonte de indice {index} tem campos ausentes ou invalidos: {', '.join(missing)}."
            )
        if any(not item[field].strip() for field in required_source_fields):
            raise ConfigurationError(f"A fonte de indice {index} possui campo vazio.")
        source_id = item["id"].strip()
        parsed_url = urlparse(item["url"].strip())
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise ConfigurationError(
                f"A URL da fonte de indice {index} deve usar HTTP ou HTTPS."
            )
        if source_id in seen_ids:
            raise ConfigurationError(f"ID de fonte duplicado: '{source_id}'.")
        seen_ids.add(source_id)
        source_type = item.get("type", "html")
        if source_type not in {"html", "feed"}:
            raise ConfigurationError(f"Tipo invalido na fonte '{source_id}': {source_type!r}.")
        feed_urls = item.get("feed_urls", [])
        if not isinstance(feed_urls, list) or any(
            not isinstance(url, str) or urlparse(url).scheme not in {"http", "https"}
            for url in feed_urls
        ):
            raise ConfigurationError(f"feed_urls invalido na fonte '{source_id}'.")
        max_pages = item.get("max_pages", 1)
        if isinstance(max_pages, bool) or not isinstance(max_pages, int) or not 1 <= max_pages <= 20:
            raise ConfigurationError(f"max_pages deve estar entre 1 e 20 na fonte '{source_id}'.")
        for optional in ("page_param", "next_page_selector", "page_url_template"):
            if not isinstance(item.get(optional, ""), str):
                raise ConfigurationError(f"{optional} invalido na fonte '{source_id}'.")
        sources.append(
            Source(
                id=source_id,
                name=item["name"].strip(),
                url=item["url"].strip(),
                article_selector=item["article_selector"].strip(),
                title_selector=item["title_selector"].strip(),
                link_selector=item["link_selector"].strip(),
                date_selector=item["date_selector"].strip(),
                content_selector=item["content_selector"].strip(),
                type=source_type,
                feed_urls=tuple(url.strip() for url in feed_urls),
                page_param=item.get("page_param", "").strip(),
                next_page_selector=item.get("next_page_selector", "").strip(),
                page_url_template=item.get("page_url_template", "").strip(),
                max_pages=max_pages,
                date_from_article=bool(item.get("date_from_article", False)),
            )
        )

    return app_config, sources
