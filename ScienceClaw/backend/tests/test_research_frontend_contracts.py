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


def test_agent_api_sends_research_tool_pack_for_tool_save():
    agent_api = (
        Path(__file__).resolve().parents[2]
        / "frontend"
        / "src"
        / "api"
        / "agent.ts"
    ).read_text(encoding="utf-8")

    assert "toolPack: string = 'literature'" in agent_api
    assert "tool_pack: toolPack" in agent_api
    assert "tool_pack: { id: string, label: string, research_workflow: string }" in agent_api


def test_tools_page_surfaces_external_tool_packs():
    frontend_root = Path(__file__).resolve().parents[2] / "frontend" / "src"
    tools_page = (frontend_root / "pages" / "ToolsPage.vue").read_text(encoding="utf-8")
    response_types = (frontend_root / "types" / "response.ts").read_text(encoding="utf-8")

    assert "tool_pack?: { id: string; label: string; research_workflow: string }" in response_types
    assert "selectedToolPack" in tools_page
    assert "tool.tool_pack?.label" in tools_page
    assert "tool.tool_pack?.id === selectedToolPack" in tools_page
    assert "Research workflow" in tools_page


def test_chat_request_can_activate_research_tool_packs():
    frontend_root = Path(__file__).resolve().parents[2] / "frontend" / "src"
    agent_api = (frontend_root / "api" / "agent.ts").read_text(encoding="utf-8")
    chat_page = (frontend_root / "pages" / "ChatPage.vue").read_text(encoding="utf-8")

    assert "active_tool_packs?: string[]" in agent_api
    assert "active_tool_packs: activeResearchToolPacks.value" in chat_page
