from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend" / "src"


def test_research_agents_frontend_route_api_and_navigation_contract():
    page = FRONTEND / "pages" / "ResearchAgentsPage.vue"
    assert page.exists()

    page_source = page.read_text(encoding="utf-8")

    assert "Research Agents" in page_source
    assert "BaseInfo" in page_source
    assert "CapabilityAccess" in page_source
    assert "SkillBindingSelector" in page_source
    assert "ToolBindingSelector" in page_source
    assert "RecentRunsCollapsed" in page_source
    assert "sidePanelExpanded" in page_source
    assert "saveAgentEdits" in page_source
    assert "toggleAgentEnabled" in page_source
    assert "toggleAgentAvailability" in page_source
    assert "defaultSelectedAgentName" in page_source
    assert "agent.editable && agent.agent_type === 'custom'" in page_source

    # The page is a governed authoring console, not a raw Registry row editor.
    assert "input_boundaries_text" not in page_source
    assert "metadata_text" not in page_source
    assert "formattedGovernance" not in page_source
    assert "editDraft.output_boundary" not in page_source
    assert "Input boundaries JSON" not in page_source
    assert "Metadata JSON" not in page_source
    assert "输出边界" not in page_source
    assert "启停" not in page_source
    assert "统一输入输出协议" not in page_source
    assert "运行验证" not in page_source
    assert "发布启用" not in page_source
    assert "停用" not in page_source
    assert "回滚" not in page_source
    assert "rollbackAgent" not in page_source
    assert "rollbackResearchAgent" not in page_source
    assert "enabled: false," not in page_source
    assert "skill_refs_text" not in page_source
    assert "allowed_tools_text" not in page_source
    assert "commaList" not in page_source

    api_source = (FRONTEND / "api" / "agent.ts").read_text(encoding="utf-8")
    assert "ResearchAgentDefinition" in api_source
    assert "ResearchAgentCapabilityItem" in api_source
    assert "ResearchAgentCapabilities" in api_source
    assert "ResearchAgentRun" in api_source
    assert "ResearchAgentValidationResult" in api_source
    assert "listResearchAgents" in api_source
    assert "listResearchAgentRuns" in api_source
    assert "validateResearchAgent" in api_source
    assert "ResearchAgentUpdateRequest" in api_source
    assert "updateResearchAgent" in api_source
    assert "listResearchAgentCapabilities" in api_source
    assert "/sessions/research/agents" in api_source
    assert "/sessions/research/agents/capabilities" in api_source
    assert "`/sessions/research/agents/${encodeURIComponent(agentName)}`" in api_source

    activity_panel_source = (FRONTEND / "components" / "ActivityPanel.vue").read_text(encoding="utf-8")
    assert "delegation_decision" in activity_panel_source
    assert "multi_agent_decision" in activity_panel_source
    assert "decision_source" in activity_panel_source
    assert "trigger=" in activity_panel_source
    assert "reason=" in activity_panel_source

    router_source = (FRONTEND / "main.ts").read_text(encoding="utf-8")
    assert "ResearchAgentsPage" in router_source
    assert "research-agents" in router_source

    left_panel_source = (FRONTEND / "components" / "LeftPanel.vue").read_text(encoding="utf-8")
    assert "handleResearchAgentsTabClick" in left_panel_source
    assert "/chat/research-agents" in left_panel_source
