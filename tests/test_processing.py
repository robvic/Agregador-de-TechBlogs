import subprocess

import pytest

from scripts.config import LlmConfig
from scripts.models import ProcessedArticle
from scripts.processing import CopilotCliProcessor, ProcessingError


def test_copilot_processor_parses_json_and_validates_category(monkeypatch):
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args[0],
            0,
            stdout='result: {"summary": "Resumo fiel", "category": "Dados e IA"}',
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    processor = CopilotCliProcessor(
        LlmConfig("copilot", ("-p", "{prompt}"), 10),
        ("Dados e IA", "Segurança"),
    )

    result = processor.process("Post", "https://example.com/post", "Texto")

    assert result == ProcessedArticle("Resumo fiel", "Dados e IA")


def test_copilot_processor_rejects_invalid_category(monkeypatch):
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args[0],
            0,
            stdout='{"summary": "Resumo", "category": "Outra"}',
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    processor = CopilotCliProcessor(
        LlmConfig("copilot", ("-p", "{prompt}"), 10),
        ("Dados e IA",),
    )

    with pytest.raises(ProcessingError, match="Categoria invalida"):
        processor.process("Post", "https://example.com/post", "Texto")

