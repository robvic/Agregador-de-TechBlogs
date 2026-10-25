from datetime import UTC, datetime

from scripts.models import Article, ProcessedArticle
from scripts.storage import ArticleStore


def article(url: str = "https://example.com/post") -> Article:
    return Article(
        source_id="example",
        source_name="Example",
        title="Post",
        url=url,
        published_at=datetime(2026, 10, 24, tzinfo=UTC),
        content="Article content",
    )


def test_store_deduplicates_and_retries_unsent_articles(tmp_path):
    database = tmp_path / "data" / "articles.sqlite3"
    with ArticleStore(database) as store:
        assert store.add(article())
        assert not store.add(article())
        assert len(store.pending("collected")) == 1
        store.mark_processed(
            article().url,
            ProcessedArticle("Summary", "Dados e IA"),
        )
        assert len(store.pending("collected")) == 0
        assert len(store.pending("processed")) == 1
        store.mark_sent([article().url])
        assert len(store.pending("processed")) == 0

