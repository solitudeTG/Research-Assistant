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
    assert "Resolve conflict" in chat_message
    assert "memory.memory_status === 'conflict' ? 'Resolve conflict' : 'Forget'" in chat_message
    assert "memory_status?: 'active' | 'conflict'" in message_types
    assert "conflicts_with?: string[]" in message_types
    assert "context_memory_conflict_count?: number" in message_types
    assert "memory_status?: 'active' | 'conflict'" in agent_api
    assert "conflicts_with?: string[]" in agent_api
    assert "context_memory_conflict_count?: number" in agent_api


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
    assert "researchToolPackOptions" in chat_page
    assert "{ id: 'literature'" in chat_page
    assert "{ id: 'evidence'" in chat_page
    assert "{ id: 'reporting'" in chat_page
    assert "{ id: 'memory'" in chat_page
    assert "selectedResearchToolPacks" in chat_page
    assert "toggleResearchToolPack" in chat_page
    assert "computed<string[]>(() => [])" not in chat_page


def test_frontend_tool_trace_types_accept_result_contract_metadata():
    frontend_root = Path(__file__).resolve().parents[2] / "frontend" / "src"
    event_types = (frontend_root / "types" / "event.ts").read_text(encoding="utf-8")
    message_types = (frontend_root / "types" / "message.ts").read_text(encoding="utf-8")

    assert "result_contract?: ToolResultContract" in event_types
    assert "tool_pack?: ResearchToolPackMetadata" in event_types
    assert "export interface ToolResultContract" in event_types
    assert "result_contract?: ToolResultContract" in message_types
    assert "tool_pack?: ResearchToolPackMetadata" in message_types


def test_activity_panel_surfaces_runtime_result_summary():
    frontend_root = Path(__file__).resolve().parents[2] / "frontend" / "src"
    event_types = (frontend_root / "types" / "event.ts").read_text(encoding="utf-8")
    message_types = (frontend_root / "types" / "message.ts").read_text(encoding="utf-8")
    activity_panel = (frontend_root / "components" / "ActivityPanel.vue").read_text(encoding="utf-8")

    assert "export interface ToolRuntimeResultSummary" in event_types
    assert "runtime_result_summary?: ToolRuntimeResultSummary" in event_types
    assert "runtime_result_summary?: ToolRuntimeResultSummary" in message_types
    assert "result_sha256: string" in event_types
    assert "Runtime summary" in activity_panel
    assert "result_sha256" in activity_panel
    assert "context_boundary" in activity_panel
    assert "citation_evidence" in activity_panel


def test_agent_api_exposes_persisted_runtime_result_audit_view():
    frontend_root = Path(__file__).resolve().parents[2] / "frontend" / "src"
    agent_api = (frontend_root / "api" / "agent.ts").read_text(encoding="utf-8")

    assert "export interface RuntimeResultAuditItem" in agent_api
    assert "export interface RuntimeResultAudit" in agent_api
    assert "export interface RuntimeResultAuditExportManifest" in agent_api
    assert "export async function listRuntimeResultAudit" in agent_api
    assert "export async function exportRuntimeResultAudit" in agent_api
    assert "filters?: RuntimeResultAuditFilters" in agent_api
    assert "tool_pack_id" in agent_api
    assert "result_sha256" in agent_api
    assert "export_manifest: RuntimeResultAuditExportManifest" in agent_api
    assert "artifact_path: string" in agent_api
    assert "round_files: RoundFileInfo[]" in agent_api
    assert "`/sessions/${sessionId}/research/runtime-results`" in agent_api
    assert "`/sessions/${sessionId}/research/runtime-results/export`" in agent_api
    assert "context_boundary: 'process_trace'" in agent_api
    assert "citation_evidence: false" in agent_api


def test_activity_panel_surfaces_persisted_runtime_result_audit_view():
    frontend_root = Path(__file__).resolve().parents[2] / "frontend" / "src"
    chat_page = (frontend_root / "pages" / "ChatPage.vue").read_text(encoding="utf-8")
    activity_panel = (frontend_root / "components" / "ActivityPanel.vue").read_text(encoding="utf-8")

    assert "runtimeResultAudit" in chat_page
    assert "agentApi.listRuntimeResultAudit" in chat_page
    assert ":runtimeAudit=\"runtimeResultAudit\"" in chat_page
    assert "runtimeAudit" in activity_panel
    assert "Recovered runtime audit" in activity_panel
    assert "process_trace" in activity_panel
    assert "citation_evidence=false" in activity_panel
    assert "result_sha256" in activity_panel


def test_activity_panel_surfaces_recovered_runtime_audit_details():
    frontend_root = Path(__file__).resolve().parents[2] / "frontend" / "src"
    activity_panel = (frontend_root / "components" / "ActivityPanel.vue").read_text(encoding="utf-8")

    assert "Recovered runtime detail" in activity_panel
    assert "item.summary.tool_pack?.label" in activity_panel
    assert "item.summary.result_contract?.kind" in activity_panel
    assert "item.summary.truncated" in activity_panel
    assert "safeStringify(item.summary.preview)" in activity_panel


def test_activity_panel_filters_recovered_runtime_audit_by_tool_pack():
    frontend_root = Path(__file__).resolve().parents[2] / "frontend" / "src"
    activity_panel = (frontend_root / "components" / "ActivityPanel.vue").read_text(encoding="utf-8")

    assert "selectedRuntimeAuditPack" in activity_panel
    assert "runtimeAuditPackOptions" in activity_panel
    assert "visibleRuntimeAuditItems" in activity_panel
    assert "runtime-audit-pack-filter" in activity_panel
    assert "All packs" in activity_panel
    assert "item.summary.tool_pack?.id === selectedRuntimeAuditPack" in activity_panel
    assert "pack={{ item.summary.tool_pack?.label || 'Unpacked' }}" in activity_panel


def test_activity_panel_can_export_recovered_runtime_audit_artifact():
    frontend_root = Path(__file__).resolve().parents[2] / "frontend" / "src"
    chat_page = (frontend_root / "pages" / "ChatPage.vue").read_text(encoding="utf-8")
    activity_panel = (frontend_root / "components" / "ActivityPanel.vue").read_text(encoding="utf-8")

    assert "runtime-audit-export" in activity_panel
    assert "@click.stop=\"handleRuntimeAuditExport\"" in activity_panel
    assert "emit('exportRuntimeAudit'" in activity_panel
    assert "@exportRuntimeAudit=\"handleRuntimeAuditExport\"" in chat_page
    assert "agentApi.exportRuntimeResultAudit" in chat_page
    assert "refreshRuntimeResultAudit(sessionId.value)" in chat_page


def test_tool_panel_surfaces_runtime_result_summary():
    frontend_root = Path(__file__).resolve().parents[2] / "frontend" / "src"
    tool_panel = (frontend_root / "components" / "ToolPanelContent.vue").read_text(encoding="utf-8")

    assert "runtime_result_summary" in tool_panel
    assert "Runtime summary" in tool_panel
    assert "result_sha256" in tool_panel
    assert "context_boundary" in tool_panel
    assert "citation_evidence" in tool_panel


def test_chat_answer_error_uses_citation_evidence_wording():
    chat_page = (
        Path(__file__).resolve().parents[2]
        / "frontend"
        / "src"
        / "pages"
        / "ChatPage.vue"
    ).read_text(encoding="utf-8")

    assert "Failed to answer from citation evidence" in chat_page
    assert "Failed to answer from paper evidence" not in chat_page


def test_chat_research_mode_tooltip_uses_citation_evidence_wording():
    chat_page = (
        Path(__file__).resolve().parents[2]
        / "frontend"
        / "src"
        / "pages"
        / "ChatPage.vue"
    ).read_text(encoding="utf-8")

    assert "Citation evidence mode" in chat_page
    assert "Paper evidence mode" not in chat_page
