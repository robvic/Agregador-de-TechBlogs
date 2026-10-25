import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.error import URLError
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen
from xml.etree.ElementTree import Element

from bs4 import BeautifulSoup
from bs4.element import Tag
from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException
from soupsieve import SelectorSyntaxError

from scripts.models import Article, Source

logger = logging.getLogger(__name__)
Fetcher = Callable[[str], str]

ACCEPT_HEADER = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
MIN_FEED_CONTENT_CHARACTERS = 1500
MONTHS = {
    name: number
    for number, name in enumerate(
        ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), 1
    )
}
TEXT_DATE = re.compile(r"\b([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b")


class ScrapingError(RuntimeError):
    """Erro ao baixar ou interpretar uma fonte."""


@dataclass
class Candidate:
    title: str
    url: str
    published_at: datetime | None
    content: str = ""


def _parse_text_date(value: str) -> datetime | None:
    for match in TEXT_DATE.finditer(value):
        month = MONTHS.get(match.group(1)[:3].lower())
        if month is None:
            continue
        try:
            return datetime(int(match.group(3)), month, int(match.group(2)), tzinfo=UTC)
        except ValueError:
            continue
    return None


def _parse_date(value: str) -> datetime | None:
    value = value.strip()
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError, OverflowError):
            return _parse_text_date(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child_text(element: Element, name: str) -> str:
    for child in element:
        if _local_name(child.tag) == name and child.text:
            return child.text.strip()
    return ""


def _with_page(url: str, param: str, page: int) -> str:
    parts = urlparse(url)
    query = [(k, v) for k, v in parse_qsl(parts.query) if k != param]
    query.append((param, str(page)))
    return urlunparse(parts._replace(query=urlencode(query)))


def _page_date(page: BeautifulSoup) -> datetime | None:
    meta = page.select_one('meta[property="article:published_time"], meta[itemprop="datePublished"]')
    if meta is not None and (parsed := _parse_date(str(meta.get("content", "")))):
        return parsed
    for script in page.select('script[type="application/ld+json"]'):
        found = re.search(r'"datePublished"\s*:\s*"([^"]+)"', script.get_text())
        if found and (parsed := _parse_date(found.group(1))):
            return parsed
    for time_element in page.select("time"):
        value = time_element.get("datetime") or time_element.get_text(" ", strip=True)
        if parsed := _parse_date(str(value)):
            return parsed
    return None


def _page_title(page: BeautifulSoup) -> str:
    heading = page.select_one("h1")
    if heading is not None and heading.get_text(" ", strip=True):
        return heading.get_text(" ", strip=True)
    meta = page.select_one('meta[property="og:title"]')
    if meta is not None and str(meta.get("content", "")).strip():
        return str(meta["content"]).strip()
    return page.title.get_text(" ", strip=True) if page.title else ""


class BlogScraper:
    def __init__(
        self,
        user_agent: str,
        timeout_seconds: int,
        max_posts: int,
        max_article_characters: int,
        fetcher: Fetcher | None = None,
    ) -> None:
        self.user_agent = user_agent
        self.timeout_seconds = timeout_seconds
        self.max_posts = max_posts
        self.max_article_characters = max_article_characters
        self.fetcher = fetcher or self._fetch

    def _fetch(self, url: str) -> str:
        request = Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": ACCEPT_HEADER,
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                return response.read().decode(charset, errors="replace")
        except (URLError, TimeoutError, OSError) as error:
            raise ScrapingError(f"Nao foi possivel acessar {url}: {error}") from error

    def scrape(self, source: Source, since: datetime, until: datetime) -> list[Article]:
        since, until = since.astimezone(UTC), until.astimezone(UTC)
        try:
            if source.type == "feed":
                candidates = self._collect_feed(source, since)
            else:
                candidates = self._collect_html(source, since)
        except (ScrapingError, SelectorSyntaxError, DefusedXmlException) as error:
            raise ScrapingError(f"Falha ao interpretar a listagem de {source.name}: {error}") from error

        articles: list[Article] = []
        for candidate in candidates:
            article = self._build_article(source, candidate, since, until)
            if article is not None:
                articles.append(article)
            if len(articles) >= self.max_posts:
                break
        logger.info("%s: %d publicacao(oes) elegivel(is).", source.name, len(articles))
        return articles

    def _collect_html(self, source: Source, since: datetime) -> list[Candidate]:
        candidates: list[Candidate] = []
        seen: set[str] = set()
        page_url: str | None = source.url
        visited: set[str] = set()
        for page_number in range(1, source.max_pages + 1):
            if page_url is None or page_url in visited:
                break
            visited.add(page_url)
            listing = BeautifulSoup(self.fetcher(page_url), "html.parser")
            dates: list[datetime] = []
            for card in listing.select(source.article_selector):
                candidate = self._parse_card(source, card, page_url)
                if candidate is None or candidate.url in seen:
                    continue
                seen.add(candidate.url)
                candidates.append(candidate)
                if candidate.published_at is not None:
                    dates.append(candidate.published_at)
            # Listagens vem da mais recente para a mais antiga: parar quando toda a pagina saiu da janela.
            if dates and max(dates) < since:
                break
            if source.page_url_template:
                page_url = source.page_url_template.format(page=page_number + 1)
            else:
                page_url = self._next_page(source, listing, page_url)
        return candidates

    def _next_page(self, source: Source, listing: BeautifulSoup, page_url: str) -> str | None:
        if not source.next_page_selector:
            return None
        link = listing.select_one(source.next_page_selector)
        href = link.get("href") if link is not None else None
        if not isinstance(href, str) or not href.strip():
            return None
        return urljoin(page_url, href.strip())

    def _parse_card(self, source: Source, card: Tag, page_url: str) -> Candidate | None:
        link_element = card if card.name == "a" else card.select_one(source.link_selector)
        if link_element is None:
            return None
        href = link_element.get("href")
        if not isinstance(href, str) or not href.strip():
            return None
        url = urljoin(page_url, href.strip())

        title_element = card.select_one(source.title_selector)
        title = ""
        if title_element is not None:
            title = title_element.get_text(" ", strip=True) or str(
                title_element.get("aria-label") or title_element.get("title") or ""
            ).strip()

        published_at: datetime | None = None
        date_element = card.select_one(source.date_selector)
        if date_element is not None:
            published_at = _parse_date(
                str(date_element.get("datetime") or date_element.get_text(" ", strip=True))
            )
        if published_at is None:
            published_at = _parse_text_date(card.get_text(" ", strip=True))
        return Candidate(title=title, url=url, published_at=published_at)

    def _collect_feed(self, source: Source, since: datetime) -> list[Candidate]:
        candidates: dict[str, Candidate] = {}
        for feed_index, feed_url in enumerate((source.url, *source.feed_urls)):
            for page in range(1, source.max_pages + 1):
                url = _with_page(feed_url, source.page_param, page) if source.page_param and page > 1 else feed_url
                try:
                    items = self._parse_feed(url)
                except ScrapingError as error:
                    if feed_index == 0 and page == 1:
                        raise
                    logger.warning("Feed ignorado (%s): %s", source.name, error)
                    break
                new_items = [item for item in items if item.url not in candidates]
                for item in new_items:
                    candidates[item.url] = item
                dates = [item.published_at for item in items if item.published_at is not None]
                paginated = bool(source.page_param)
                if not paginated or not new_items or (dates and max(dates) < since):
                    break
        ordered = list(candidates.values())
        ordered.sort(key=lambda c: c.published_at or datetime.max.replace(tzinfo=UTC), reverse=True)
        return ordered

    def _parse_feed(self, url: str) -> list[Candidate]:
        try:
            root = ElementTree.fromstring(self.fetcher(url).lstrip().encode("utf-8"))
        except ElementTree.ParseError as error:
            raise ScrapingError(f"Feed invalido em {url}: {error}") from error
        items: list[Candidate] = []
        for element in root.iter():
            if _local_name(element.tag) not in {"item", "entry"}:
                continue
            link = _child_text(element, "link")
            if not link:
                for child in element:
                    if _local_name(child.tag) == "link" and child.get("rel", "alternate") == "alternate":
                        link = child.get("href", "")
                        break
            if not link:
                continue
            date_text = (
                _child_text(element, "pubDate")
                or _child_text(element, "published")
                or _child_text(element, "updated")
                or _child_text(element, "date")
            )
            body = _child_text(element, "encoded") or _child_text(element, "content")
            description = _child_text(element, "description") or _child_text(element, "summary")
            text = BeautifulSoup(body or description, "html.parser").get_text(" ", strip=True)
            items.append(
                Candidate(
                    title=_child_text(element, "title"),
                    url=urljoin(url, link.strip()),
                    published_at=_parse_date(date_text),
                    content=text,
                )
            )
        return items

    def _build_article(
        self, source: Source, candidate: Candidate, since: datetime, until: datetime
    ) -> Article | None:
        if urlparse(candidate.url).scheme not in {"http", "https"}:
            logger.warning("URL nao HTTP(S) ignorada (%s): %s", source.name, candidate.url)
            return None
        published_at = candidate.published_at
        if published_at is not None and not since <= published_at <= until:
            return None

        page: BeautifulSoup | None = None
        needs_date = published_at is None and (source.date_from_article or source.type == "html")
        needs_page = (
            needs_date
            or not candidate.title
            or len(candidate.content) < MIN_FEED_CONTENT_CHARACTERS
        )
        if needs_page:
            try:
                page = BeautifulSoup(self.fetcher(candidate.url), "html.parser")
            except ScrapingError as error:
                if not candidate.content or published_at is None or not candidate.title:
                    logger.warning(
                        "Falha ao coletar '%s' (%s): %s", candidate.title or candidate.url, source.name, error
                    )
                    return None
                logger.warning("Usando resumo do feed para '%s': %s", candidate.title, error)

        if page is not None and published_at is None:
            published_at = _page_date(page)
            if published_at is None or not since <= published_at <= until:
                return None
        if published_at is None:
            return None

        title = candidate.title or (_page_title(page) if page is not None else "")
        content = candidate.content
        if page is not None and len(content) < MIN_FEED_CONTENT_CHARACTERS:
            try:
                element = page.select_one(source.content_selector)
            except SelectorSyntaxError as error:
                raise ScrapingError(f"Seletor de conteudo invalido em {source.name}: {error}") from error
            page_text = element.get_text(" ", strip=True) if element is not None else ""
            if len(page_text) > len(content):
                content = page_text
        if not title or not content:
            logger.warning("Publicacao sem titulo/conteudo ignorada (%s): %s", source.name, candidate.url)
            return None
        return Article(
            source_id=source.id,
            source_name=source.name,
            title=title,
            url=candidate.url,
            published_at=published_at,
            content=content[: self.max_article_characters],
        )

