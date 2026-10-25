from datetime import UTC, datetime

from scripts.models import Source
from scripts.scraping import BlogScraper, _parse_date


def source() -> Source:
    return Source(
        id="example",
        name="Example",
        url="https://example.com/blog",
        article_selector="article",
        title_selector="h2 a",
        link_selector="a[href]",
        date_selector="time",
        content_selector="main",
    )


def test_scraper_filters_old_articles_and_extracts_content():
    listing = """
    <article><h2><a href="/new">New</a></h2><time datetime="2026-10-24T12:00:00Z"></time></article>
    <article><h2><a href="/old">Old</a></h2><time datetime="2026-09-01T12:00:00Z"></time></article>
    <article><h2><a href="/future">Future</a></h2><time datetime="2026-11-01T12:00:00Z"></time></article>
    """
    pages = {
        "https://example.com/blog": listing,
        "https://example.com/new": "<main>New article content</main>",
    }
    scraper = BlogScraper(
        user_agent="test",
        timeout_seconds=1,
        max_posts=10,
        max_article_characters=100,
        fetcher=pages.__getitem__,
    )

    articles = scraper.scrape(
        source(),
        datetime(2026, 10, 20, tzinfo=UTC),
        datetime(2026, 10, 25, tzinfo=UTC),
    )

    assert len(articles) == 1
    assert articles[0].title == "New"
    assert articles[0].url == "https://example.com/new"
    assert articles[0].content == "New article content"


def test_parse_date_supports_iso_and_rejects_unrecognized_text():
    assert _parse_date("2026-10-24T12:00:00Z") == datetime(
        2026, 10, 24, 12, tzinfo=UTC
    )
    assert _parse_date("recently") is None


def test_parse_date_supports_textual_dates():
    expected = datetime(2026, 10, 22, tzinfo=UTC)
    for text in ("October 22, 2026", "OCT. 22, 2026", "Oct 22, 2026"):
        assert _parse_date(text) == expected


def make_scraper(pages: dict[str, str]) -> BlogScraper:
    return BlogScraper(
        user_agent="test",
        timeout_seconds=1,
        max_posts=10,
        max_article_characters=100,
        fetcher=pages.__getitem__,
    )


WINDOW = (datetime(2026, 10, 20, tzinfo=UTC), datetime(2026, 10, 25, tzinfo=UTC))


def test_feed_source_paginates_and_uses_article_date_fallback():
    feed_page_1 = """<rss><channel>
    <item><title>Recent</title><link>https://example.com/recent</link>
    <pubDate>Fri, 23 Oct 2026 10:00:00 GMT</pubDate></item>
    </channel></rss>"""
    feed_page_2 = """<rss><channel>
    <item><title>Old</title><link>https://example.com/old</link>
    <pubDate>Tue, 01 Sep 2026 10:00:00 GMT</pubDate></item>
    </channel></rss>"""
    feed_source = Source(
        id="feed",
        name="Feed",
        url="https://example.com/feed/",
        article_selector="article",
        title_selector="h1",
        link_selector="a",
        date_selector="time",
        content_selector="main",
        type="feed",
        page_param="paged",
        max_pages=5,
    )
    pages = {
        "https://example.com/feed/": feed_page_1,
        "https://example.com/feed/?paged=2": feed_page_2,
        "https://example.com/recent": "<main>Recent content</main>",
    }

    articles = make_scraper(pages).scrape(feed_source, *WINDOW)

    assert [a.title for a in articles] == ["Recent"]
    assert articles[0].content == "Recent content"


def test_html_source_follows_next_page_and_reads_text_date():
    html_source = Source(
        id="html",
        name="Html",
        url="https://example.com/blog",
        article_selector=".card",
        title_selector="a",
        link_selector="a",
        date_selector=".date",
        content_selector="main",
        next_page_selector="a.next",
    )
    pages = {
        "https://example.com/blog": (
            '<div class="card"><a href="/a">A</a><span class="date">Oct 23, 2026</span></div>'
            '<a class="next" href="/blog/2">Next</a>'
        ),
        "https://example.com/blog/2": (
            '<div class="card"><a href="/b">B</a><span class="date">Oct 21, 2026</span></div>'
        ),
        "https://example.com/a": "<main>Content A</main>",
        "https://example.com/b": "<main>Content B</main>",
    }
    html_source = Source(**{**html_source.__dict__, "max_pages": 3})

    articles = make_scraper(pages).scrape(html_source, *WINDOW)

    assert sorted(a.title for a in articles) == ["A", "B"]
