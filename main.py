import argparse
import logging
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

from scripts.config import ConfigurationError, load_config
from scripts.processing import CopilotCliProcessor, ProcessingError
from scripts.scraping import BlogScraper, ScrapingError
from scripts.send_email import EmailDeliveryError, send_email
from scripts.storage import ArticleStore

ROOT = Path(__file__).resolve().parent
logger = logging.getLogger("techblogs")


def run(dry_run: bool = False, send_only: bool = False) -> int:
    load_dotenv(ROOT / ".env")
    config, sources = load_config(ROOT / "configs" / "config.json", ROOT / "configs" / "urls.json")
    now = datetime.now(UTC)
    since = now - timedelta(days=config.frequency_days)
    scraper = BlogScraper(
        user_agent=config.user_agent,
        timeout_seconds=config.request_timeout_seconds,
        max_posts=config.max_posts_per_source,
        max_article_characters=config.max_article_characters,
    )
    processor = CopilotCliProcessor(config.llm, config.categories)
    failed = False

    with ArticleStore(ROOT / config.database_path) as store:
        for source in [] if send_only else sources:
            try:
                for article in scraper.scrape(source, since, now):
                    store.add(article)
            except ScrapingError:
                failed = True
                logger.exception("Falha na coleta da fonte %s.", source.name)

        for article in [] if send_only else store.pending("collected"):
            try:
                processed = processor.process(
                    article["title"],
                    article["url"],
                    article["content"],
                )
                if processed.category not in config.categories:
                    raise ProcessingError(f"Categoria fora da configuracao: {processed.category}")
                store.mark_processed(article["url"], processed)
            except ProcessingError as error:
                failed = True
                store.record_error(article["url"], str(error))
                logger.error("Falha ao processar '%s': %s", article["title"], error)

        pending_email = store.pending("processed")
        if dry_run:
            logger.info(
                "Modo de teste: %d publicacao(oes) aguardam envio; nenhum e-mail foi enviado.",
                len(pending_email),
            )
            return 1 if failed else 0

        if pending_email:
            email_articles = [
                {
                    "title": row["title"],
                    "source_name": row["source_name"],
                    "published_at": row["published_at"],
                    "category": row["category"],
                    "summary": row["summary"],
                    "url": row["url"],
                }
                for row in pending_email
            ]
            try:
                send_email(config.email, email_articles)
            except EmailDeliveryError:
                logger.exception("Falha no envio. Os itens permanecem pendentes para nova tentativa.")
                return 1
            store.mark_sent([row["url"] for row in pending_email])
            logger.info("%d publicacao(oes) enviada(s) por e-mail.", len(pending_email))
        else:
            logger.info("Nenhuma publicacao pendente para envio.")

    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Agrega posts recentes de blogs de tecnologia.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Executa coleta e processamento sem enviar e-mails.",
    )
    parser.add_argument(
        "--send-only",
        action="store_true",
        help="Apenas envia o e-mail com o que ja foi processado, sem coletar nem usar a LLM.",
    )
    args = parser.parse_args()
    if args.dry_run and args.send_only:
        parser.error("--dry-run e --send-only nao podem ser usados juntos.")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        return run(dry_run=args.dry_run, send_only=args.send_only)
    except ConfigurationError as error:
        logger.error("Configuracao invalida: %s", error)
        return 2


if __name__ == "__main__":
    sys.exit(main())
