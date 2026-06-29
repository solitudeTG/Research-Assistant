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


def test_frontend_exposes_research_library_project_contracts():
    frontend_root = Path(__file__).resolve().parents[2] / "frontend" / "src"
    agent_api = (frontend_root / "api" / "agent.ts").read_text(encoding="utf-8")
    main_ts = (frontend_root / "main.ts").read_text(encoding="utf-8")
    left_panel = (frontend_root / "components" / "LeftPanel.vue").read_text(encoding="utf-8")
    library_page = frontend_root / "pages" / "ResearchLibraryPage.vue"

    assert "export interface ResearchProject" in agent_api
    assert "export interface ResearchProjectPaperAsset" in agent_api
    assert "export async function createResearchProject" in agent_api
    assert "export async function listResearchProjects" in agent_api
    assert "export async function listResearchProjectPapers" in agent_api
    assert "export async function uploadResearchProjectPaper" in agent_api
    assert "`/sessions/research/projects`" in agent_api
    assert "`/sessions/research/projects/${projectId}/papers`" in agent_api

    assert "ResearchLibraryPage" in main_ts
    assert "research-library" in main_ts
    assert "handleResearchLibraryTabClick" in left_panel
    assert "BookOpen" in left_panel
    assert library_page.is_file()


def test_research_library_page_uses_chinese_workbench_copy():
    frontend_root = Path(__file__).resolve().parents[2] / "frontend" / "src"
    library_page = (frontend_root / "pages" / "ResearchLibraryPage.vue").read_text(encoding="utf-8")
    left_panel = (frontend_root / "components" / "LeftPanel.vue").read_text(encoding="utf-8")

    for copy in ["研究库", "研究课题", "新建课题", "上传论文", "可引用证据", "暂无论文"]:
        assert copy in library_page
    assert 'title="研究库"' in left_panel

    for stale_copy in ["Research Library", "New Project", "Create Project", "Upload Paper", "No papers in this project"]:
        assert stale_copy not in library_page


def test_static_chat_routes_are_declared_before_session_id_route():
    main_ts = (
        Path(__file__).resolve().parents[2]
        / "frontend"
        / "src"
        / "main.ts"
    ).read_text(encoding="utf-8")

    session_route_index = main_ts.index("path: ':sessionId'")
    for route_path in ["path: 'skills'", "path: 'tools'", "path: 'science-tools/:toolName'", "path: 'research-library'", "path: 'tasks'"]:
        assert main_ts.index(route_path) < session_route_index


def test_frontend_exposes_session_project_binding_contracts():
    frontend_root = Path(__file__).resolve().parents[2] / "frontend" / "src"
    agent_api = (frontend_root / "api" / "agent.ts").read_text(encoding="utf-8")
    chat_page = (frontend_root / "pages" / "ChatPage.vue").read_text(encoding="utf-8")

    assert "export interface SessionResearchProjectBinding" in agent_api
    assert "export async function setSessionResearchProject" in agent_api
    assert "export async function getSessionResearchProject" in agent_api
    assert "`/sessions/${sessionId}/research/project`" in agent_api

    assert "researchProjectOptions" in chat_page
    assert "selectedResearchProjectId" in chat_page
    assert "currentResearchProject" in chat_page
    assert "loadSessionResearchProject" in chat_page
    assert "handleResearchProjectChange" in chat_page
    assert "agentApi.setSessionResearchProject" in chat_page
    assert "agentApi.getSessionResearchProject" in chat_page
    assert "课题上下文" in chat_page


def test_frontend_exposes_chat_to_library_promotion_contract():
    frontend_root = Path(__file__).resolve().parents[2] / "frontend" / "src"
    agent_api = (frontend_root / "api" / "agent.ts").read_text(encoding="utf-8")
    chat_message = (frontend_root / "components" / "ChatMessage.vue").read_text(encoding="utf-8")
    chat_page = (frontend_root / "pages" / "ChatPage.vue").read_text(encoding="utf-8")

    assert "export interface ResearchLibraryPromotionResult" in agent_api
    assert "export async function promoteChatPaperToLibrary" in agent_api
    assert "`/sessions/${sessionId}/research/library/promote`" in agent_api
    assert "researchLibraryPromotionCandidate" in chat_message
    assert "加入研究库" in chat_message
    assert "emit('promoteToResearchLibrary'" in chat_message
    assert "@promoteToResearchLibrary=\"handlePromoteToResearchLibrary\"" in chat_page
    assert "agentApi.promoteChatPaperToLibrary" in chat_page


def test_agent_api_exposes_source_quality_ingestion_result_contract():
    agent_api = (
        Path(__file__).resolve().parents[2]
        / "frontend"
        / "src"
        / "api"
        / "agent.ts"
    ).read_text(encoding="utf-8")

    assert "SourceQualityMetadata" in agent_api
    assert "source_quality: SourceQualityMetadata" in agent_api


def test_chat_page_surfaces_source_evidence_ingestion_controls():
    chat_page = (
        Path(__file__).resolve().parents[2]
        / "frontend"
        / "src"
        / "pages"
        / "ChatPage.vue"
    ).read_text(encoding="utf-8")

    assert "导入引用证据" in chat_page
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


def test_frontend_types_expose_research_context_boundaries():
    frontend_root = Path(__file__).resolve().parents[2] / "frontend" / "src"
    message_types = (frontend_root / "types" / "message.ts").read_text(encoding="utf-8")
    agent_api = (frontend_root / "api" / "agent.ts").read_text(encoding="utf-8")

    assert "export interface ResearchContextBoundaries" in message_types
    assert "context_boundaries?: ResearchContextBoundaries" in message_types
    assert "export interface ResearchContextBoundaries" in agent_api
    assert "context_boundaries?: ResearchContextBoundaries" in agent_api


def test_chat_message_surfaces_research_context_boundary_manifest():
    chat_message = (
        Path(__file__).resolve().parents[2]
        / "frontend"
        / "src"
        / "components"
        / "ChatMessage.vue"
    ).read_text(encoding="utf-8")

    assert "researchContextBoundaries" in chat_message
    assert "Context boundary manifest" in chat_message
    assert "context_boundaries" in chat_message
    assert "Model reasoning" in chat_message
    assert "Process trace" in chat_message


def test_chat_message_surfaces_report_reader_summary_metadata():
    frontend_root = Path(__file__).resolve().parents[2] / "frontend" / "src"
    chat_message = (frontend_root / "components" / "ChatMessage.vue").read_text(encoding="utf-8")
    message_types = (frontend_root / "types" / "message.ts").read_text(encoding="utf-8")
    agent_api = (frontend_root / "api" / "agent.ts").read_text(encoding="utf-8")

    assert "export interface ResearchReportReaderSummary" in message_types
    assert "reader_summary?: ResearchReportReaderSummary" in message_types
    assert "export interface ResearchReportReaderSummary" in agent_api
    assert "reader_summary?: ResearchReportReaderSummary" in agent_api
    assert "reportReaderSummary" in chat_message
    assert "Report reader summary" in chat_message
    assert "reportReaderSummary.status" in chat_message
    assert "reportReaderSummary.evidence_basis" in chat_message
    assert "reportReaderSummary.memory_boundary" in chat_message
    assert "reportReaderSummary.next_action" in chat_message


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


def test_activity_panel_surfaces_source_quality_trace_metadata():
    frontend_root = Path(__file__).resolve().parents[2] / "frontend" / "src"
    event_types = (frontend_root / "types" / "event.ts").read_text(encoding="utf-8")
    activity_panel = (frontend_root / "components" / "ActivityPanel.vue").read_text(encoding="utf-8")

    assert "export interface SourceQualityMetadata" in event_types
    assert "source_quality?: SourceQualityMetadata" in event_types
    assert "sourceQualitySteps" in activity_panel
    assert "Source quality" in activity_panel
    assert "citation_grade" in activity_panel
    assert "identity_incomplete" in activity_panel
    assert "citation_evidence=true" in activity_panel
    assert "quality.missing_fields" in activity_panel
    assert "quality_warnings?: string[]" in event_types
    assert "quality.quality_warnings" in activity_panel
    assert "warnings=" in activity_panel


def test_activity_panel_surfaces_evidence_admission_trace_metadata():
    frontend_root = Path(__file__).resolve().parents[2] / "frontend" / "src"
    event_types = (frontend_root / "types" / "event.ts").read_text(encoding="utf-8")
    message_types = (frontend_root / "types" / "message.ts").read_text(encoding="utf-8")
    agent_api = (frontend_root / "api" / "agent.ts").read_text(encoding="utf-8")
    activity_panel = (frontend_root / "components" / "ActivityPanel.vue").read_text(encoding="utf-8")

    assert "export interface EvidenceAdmissionMetadata" in event_types
    assert "evidence_admission?: EvidenceAdmissionMetadata" in event_types
    assert "evidence_admission?: EvidenceAdmissionMetadata" in message_types
    assert "evidence_admission?: EvidenceAdmissionMetadata" in agent_api
    assert "evidenceAdmissionSteps" in activity_panel
    assert "Evidence admission" in activity_panel
    assert "admission.decision" in activity_panel
    assert "threshold={{ admission.threshold }}" in activity_panel
    assert "accepted={{ admission.accepted_count }}" in activity_panel
    assert "rejected={{ admission.rejected_count }}" in activity_panel


def test_left_panel_new_task_uses_canonical_chat_route_from_research_library():
    frontend_root = Path(__file__).resolve().parents[2] / "frontend" / "src"
    left_panel = (frontend_root / "components" / "LeftPanel.vue").read_text(encoding="utf-8")
    library_handler_start = left_panel.index("const handleResearchLibraryTabClick = () =>")
    library_handler_end = left_panel.index("const handleToolsTabClick", library_handler_start)
    library_handler_source = left_panel[library_handler_start:library_handler_end]
    handler_start = left_panel.index("const handleNewTaskClick = async () =>")
    handler_end = left_panel.index("const handleSessionDeleted", handler_start)
    handler_source = left_panel[handler_start:handler_end]

    assert "toggleLeftPanel()" not in library_handler_source
    assert "router.push('/chat/research-library')" in library_handler_source
    assert "showNewSessionProjectPicker.value = true" in handler_source
    assert "router.push('/')" not in handler_source


def test_research_library_route_hides_chat_session_drawer():
    left_panel = (
        Path(__file__).resolve().parents[2]
        / "frontend"
        / "src"
        / "components"
        / "LeftPanel.vue"
    ).read_text(encoding="utf-8")

    assert "shouldShowSessionDrawer" in left_panel
    assert "v-if=\"shouldShowSessionDrawer\"" in left_panel
    assert "leftPanelWidth" in left_panel
    assert "isResearchLibraryActive.value ? '60px'" in left_panel
    assert "isResearchLibraryActive.value && !isLeftPanelShow.value" not in left_panel


def test_new_task_flow_can_choose_research_project_before_chat_start():
    frontend_root = Path(__file__).resolve().parents[2] / "frontend" / "src"
    left_panel = (frontend_root / "components" / "LeftPanel.vue").read_text(encoding="utf-8")
    home_page = (frontend_root / "pages" / "HomePage.vue").read_text(encoding="utf-8")
    chat_page = (frontend_root / "pages" / "ChatPage.vue").read_text(encoding="utf-8")

    assert "showNewSessionProjectPicker" in left_panel
    assert "newSessionProjectId" in left_panel
    assert "loadNewSessionProjects" in left_panel
    assert "handleStartNewSession" in left_panel
    assert "agentApi.listResearchProjects" in left_panel
    assert "query: newSessionProjectId.value ? { project_id: newSessionProjectId.value } : {}" in left_panel

    assert "selectedResearchProjectId" in home_page
    assert "route.query.project_id" in home_page
    assert "agentApi.listResearchProjects" in home_page
    assert "agentApi.setSessionResearchProject(sessionId, selectedResearchProjectId.value)" in home_page
    assert "不关联课题" in home_page
    assert "所属课题" in home_page

    pending_start = chat_page.index("if (pending?.message)")
    pending_end = chat_page.index("} else {", pending_start)
    pending_source = chat_page[pending_start:pending_end]
    assert "await loadSessionResearchProject(sessionId.value)" in pending_source
    assert pending_source.index("await loadSessionResearchProject(sessionId.value)") < pending_source.index("chat(pending.message")


def test_research_chat_controls_use_chinese_user_facing_copy():
    frontend_root = Path(__file__).resolve().parents[2] / "frontend" / "src"
    chat_page = (frontend_root / "pages" / "ChatPage.vue").read_text(encoding="utf-8")
    chat_message = (frontend_root / "components" / "ChatMessage.vue").read_text(encoding="utf-8")

    assert "未关联课题" in chat_page
    assert "课题上下文" in chat_page
    assert "引用证据" in chat_page
    assert "工具关闭" in chat_page
    assert "加入研究库" in chat_message
    assert "生成 Markdown 研究报告" in chat_message

    assert "No Project" not in chat_page
    assert "Project context" not in chat_page
    assert "No linked Project" not in chat_page
    assert "citation records" not in chat_page
    assert "Tools off" not in chat_page
    assert "Add to Research Library" not in chat_message
    assert "Generate Markdown research report" not in chat_message


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

    assert "引用证据模式" in chat_page
    assert "Paper evidence mode" not in chat_page
