import json

import pytest

from scripts.config import ConfigurationError, load_config


def test_loads_default_configs():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    config, sources = load_config(root / "configs/config.json", root / "configs/urls.json")

    assert config.frequency_days == 7
    assert len(config.categories) == 6
    assert len(sources) == 10


def test_rejects_duplicate_source_ids(tmp_path):
    config_path = tmp_path / "config.json"
    source_path = tmp_path / "sources.json"
    config_path.write_text(
        json.dumps(
            {
                "frequency_days": 7,
                "database_path": "test.sqlite",
                "request_timeout_seconds": 20,
                "max_posts_per_source": 10,
                "max_article_characters": 1000,
                "user_agent": "test",
                "categories": ["IA"],
                "email": {
                    "smtp_host": "localhost",
                    "smtp_port": 587,
                    "use_starttls": True,
                    "recipient": "",
                },
                "llm": {
                    "command": "copilot",
                    "arguments": ["-p", "{prompt}"],
                    "timeout_seconds": 10,
                },
            }
        ),
        encoding="utf-8",
    )
    source = {
        "id": "duplicate",
        "name": "Blog",
        "url": "https://example.com",
        "article_selector": "article",
        "title_selector": "h2",
        "link_selector": "a",
        "date_selector": "time",
        "content_selector": "article",
    }
    source_path.write_text(json.dumps([source, source]), encoding="utf-8")

    with pytest.raises(ConfigurationError, match="duplicado"):
        load_config(config_path, source_path)
