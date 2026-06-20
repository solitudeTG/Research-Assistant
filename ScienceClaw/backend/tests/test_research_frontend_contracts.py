from pathlib import Path


def test_chat_citation_card_renders_citation_source_type():
    chat_message = (
        Path(__file__).resolve().parents[2]
        / "frontend"
        / "src"
        / "components"
        / "ChatMessage.vue"
    ).read_text(encoding="utf-8")

    assert "{{ citation.source_type }}" in chat_message
    assert "                    paper\n" not in chat_message
