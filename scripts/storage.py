import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Self

from scripts.models import Article, ProcessedArticle


class ArticleStore:
    def __init__(self, database_path: Path) -> None:
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(database_path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS articles (
                url TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                source_name TEXT NOT NULL,
                title TEXT NOT NULL,
                published_at TEXT NOT NULL,
                content TEXT NOT NULL,
                summary TEXT,
                category TEXT,
                status TEXT NOT NULL CHECK (status IN ('collected', 'processed', 'sent')),
                last_error TEXT,
                collected_at TEXT NOT NULL,
                processed_at TEXT,
                sent_at TEXT
            )
            """
        )
        self.connection.commit()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.connection.close()

    def add(self, article: Article) -> bool:
        cursor = self.connection.execute(
            """
            INSERT INTO articles
                (url, source_id, source_name, title, published_at, content, status, collected_at)
            VALUES (?, ?, ?, ?, ?, ?, 'collected', ?)
            ON CONFLICT(url) DO NOTHING
            """,
            (
                article.url,
                article.source_id,
                article.source_name,
                article.title,
                article.published_at.astimezone(UTC).isoformat(),
                article.content,
                datetime.now(UTC).isoformat(),
            ),
        )
        self.connection.commit()
        return cursor.rowcount == 1

    def pending(self, status: str) -> list[sqlite3.Row]:
        if status not in {"collected", "processed"}:
            raise ValueError(f"Status invalido para consulta: {status}")
        return list(
            self.connection.execute(
                "SELECT * FROM articles WHERE status = ? ORDER BY published_at DESC",
                (status,),
            )
        )

    def mark_processed(self, url: str, result: ProcessedArticle) -> None:
        self.connection.execute(
            """
            UPDATE articles
            SET summary = ?, category = ?, status = 'processed', last_error = NULL,
                processed_at = ?
            WHERE url = ? AND status = 'collected'
            """,
            (result.summary, result.category, datetime.now(UTC).isoformat(), url),
        )
        self.connection.commit()

    def record_error(self, url: str, error: str) -> None:
        self.connection.execute(
            "UPDATE articles SET last_error = ? WHERE url = ?",
            (error[:2000], url),
        )
        self.connection.commit()

    def mark_sent(self, urls: list[str]) -> None:
        if not urls:
            return
        now = datetime.now(UTC).isoformat()
        with self.connection:
            self.connection.executemany(
                """
                UPDATE articles
                SET status = 'sent', sent_at = ?, last_error = NULL
                WHERE url = ? AND status = 'processed'
                """,
                [(now, url) for url in urls],
            )
