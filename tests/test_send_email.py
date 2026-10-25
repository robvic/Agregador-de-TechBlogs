from scripts.send_email import build_email


def test_email_contains_plain_text_and_escapes_html_content():
    message = build_email(
        "sender@example.com",
        "reader@example.com",
        [
            {
                "title": "<script>alert(1)</script>",
                "source_name": "Example",
                "published_at": "2026-10-24",
                "category": "Dados e IA",
                "summary": "<b>Resumo</b>",
                "url": "https://example.com/post?a=1&b=2",
            }
        ],
    )

    html_body = message.get_body(preferencelist=("html",)).get_content()
    plain_body = message.get_body(preferencelist=("plain",)).get_content()
    assert "&lt;script&gt;" in html_body
    assert "<script>" not in html_body
    assert "<b>Resumo</b>" in plain_body
    assert "https://example.com/post?a=1&b=2" in plain_body

