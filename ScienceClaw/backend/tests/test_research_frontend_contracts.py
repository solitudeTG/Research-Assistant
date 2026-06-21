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


def test_agent_api_exposes_web_and_database_evidence_ingestion():
    agent_api = (
        Path(__file__).resolve().parents[2]
        / "frontend"
        / "src"
        / "api"
        / "agent.ts"
    ).read_text(encoding="utf-8")

    assert "export async function ingestWebEvidenceSource" in agent_api
    assert "`/sessions/${sessionId}/research/web-evidence`" in agent_api
    assert "export async function ingestDatabaseEvidenceSource" in agent_api
    assert "`/sessions/${sessionId}/research/database-evidence`" in agent_api


def test_chat_page_surfaces_source_evidence_ingestion_controls():
    chat_page = (
        Path(__file__).resolve().parents[2]
        / "frontend"
        / "src"
        / "pages"
        / "ChatPage.vue"
    ).read_text(encoding="utf-8")

    assert "Ingest citation evidence" in chat_page
    assert "sourceEvidenceKind === 'web'" in chat_page
    assert "sourceEvidenceKind === 'database'" in chat_page
    assert "agentApi.ingestWebEvidenceSource" in chat_page
    assert "agentApi.ingestDatabaseEvidenceSource" in chat_page


def test_chat_message_surfaces_context_memory_conflicts():
    frontend_root = Path(__file__).resolve().parents[2] / "frontend" / "src"
    chat_message = (frontend_root / "components" / "ChatMessage.vue").read_text(encoding="utf-8")
    message_types = (frontend_root / "types" / "message.ts").read_text(encoding="utf-8")
    agent_api = (frontend_root / "api" / "agent.ts").read_text(encoding="utf-8")

    assert "memory.memory_status === 'conflict'" in chat_message
    assert "Conflicts with" in chat_message
    assert "memory.conflicts_with" in chat_message
    assert "memory_status?: 'active' | 'conflict'" in message_types
    assert "conflicts_with?: string[]" in message_types
    assert "memory_status?: 'active' | 'conflict'" in agent_api
    assert "conflicts_with?: string[]" in agent_api


def test_chat_page_sends_user_confirmation_for_tool_save():
    frontend_root = Path(__file__).resolve().parents[2] / "frontend" / "src"
    chat_page = (frontend_root / "pages" / "ChatPage.vue").read_text(encoding="utf-8")
    agent_api = (frontend_root / "api" / "agent.ts").read_text(encoding="utf-8")

    assert "saveToolFromSession(" in chat_page
    assert "pendingToolSave.value,\n      true,\n      pendingToolReplaces.value || undefined" in chat_page
    assert "user_confirmed: userConfirmed" in agent_api
