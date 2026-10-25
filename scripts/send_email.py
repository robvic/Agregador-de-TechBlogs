import os
import smtplib
from collections.abc import Sequence
from email.message import EmailMessage
from html import escape

from scripts.config import EmailConfig


class EmailDeliveryError(RuntimeError):
    """Erro de configuracao ou envio da compilacao por e-mail."""


def build_email(
    sender: str,
    recipient: str,
    articles: Sequence[dict[str, str]],
) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = f"TechBlogs: {len(articles)} publicacao(oes) nova(s)"
    message["From"] = sender
    message["To"] = recipient

    plain_items = []
    html_items = []
    for article in articles:
        plain_items.append(
            "\n".join(
                (
                    article["title"],
                    f"Fonte: {article['source_name']}",
                    f"Data: {article['published_at']}",
                    f"Categoria: {article['category']}",
                    article["summary"],
                    f"Leia: {article['url']}",
                )
            )
        )
        html_items.append(
            "<article>"
            f'<h2><a href="{escape(article["url"], quote=True)}">'
            f"{escape(article['title'])}</a></h2>"
            f"<p><strong>{escape(article['source_name'])}</strong> "
            f"| {escape(article['published_at'])} | {escape(article['category'])}</p>"
            f"<p>{escape(article['summary'])}</p>"
            "</article>"
        )
    message.set_content("\n\n---\n\n".join(plain_items))
    message.add_alternative(
        "<html><body><h1>Novas publicacoes de tecnologia</h1>"
        + "".join(html_items)
        + "</body></html>",
        subtype="html",
    )
    return message


def send_email(config: EmailConfig, articles: Sequence[dict[str, str]]) -> None:
    if not articles:
        return
    recipient = config.recipient or os.getenv("EMAIL_TO", "").strip()
    sender = os.getenv("SMTP_FROM", os.getenv("SMTP_USER", "")).strip()
    username = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASSWORD", "")
    missing = [
        name
        for name, value in (
            ("email.recipient ou EMAIL_TO", recipient),
            ("SMTP_FROM ou SMTP_USER", sender),
            ("SMTP_USER", username),
            ("SMTP_PASSWORD", password),
        )
        if not value
    ]
    if missing:
        raise EmailDeliveryError(
            "Configuracao de e-mail incompleta. Defina: " + ", ".join(missing) + "."
        )

    try:
        message = build_email(sender, recipient, articles)
    except ValueError as error:
        raise EmailDeliveryError(f"Cabecalho de e-mail invalido: {error}") from error
    try:
        with smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=30) as server:
            server.ehlo()
            if config.use_starttls:
                server.starttls()
                server.ehlo()
            server.login(username, password)
            server.send_message(message)
    except (OSError, smtplib.SMTPException) as error:
        raise EmailDeliveryError(f"Nao foi possivel enviar o e-mail: {error}") from error
