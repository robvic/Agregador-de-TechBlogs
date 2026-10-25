from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Source:
    id: str
    name: str
    url: str
    article_selector: str
    title_selector: str
    link_selector: str
    date_selector: str
    content_selector: str
    type: str = "html"
    feed_urls: tuple[str, ...] = ()
    page_param: str = ""
    next_page_selector: str = ""
    page_url_template: str = ""
    max_pages: int = 1
    date_from_article: bool = False


@dataclass(frozen=True)
class Article:
    source_id: str
    source_name: str
    title: str
    url: str
    published_at: datetime
    content: str


@dataclass(frozen=True)
class ProcessedArticle:
    summary: str
    category: str

