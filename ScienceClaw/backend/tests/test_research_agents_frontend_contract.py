from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend" / "src"


def test_research_agents_frontend_route_api_and_navigation_contract():
    page = FRONTEND / "pages" / "ResearchAgentsPage.vue"
    assert page.exists()

    page_source = page.read_text(encoding="utf-8")
    assert "研究智能体" in page_source
    assert "审计智能体" in page_source
    assert "阅读 Worker" in page_source
    assert "Registry" in page_source
    assert "系统内置" in page_source
    assert "用户自定义" in page_source
    assert "只读" in page_source
    assert "可编辑" in page_source
    assert "刷新" in page_source
    assert "已启用" in page_source
    assert "边界" in page_source
    assert "工具" in page_source
    assert "系统提示词" in page_source
    assert "治理动作" in page_source
    assert "最近运行" in page_source
    assert "验证示例" in page_source
    assert "暂无真实运行记录" in page_source
    assert "运行验证" in page_source
    assert "research_auditor" in page_source
    assert "paper_reader_worker" in page_source
    assert "general-purpose" in page_source
    assert "agent_type" in page_source
    assert "system_builtin" in page_source
    assert "custom" in page_source
    assert "editable" in page_source
    assert "citation_evidence" in page_source
    assert "context_only" in page_source
    assert "process_trace" in page_source

    api_source = (FRONTEND / "api" / "agent.ts").read_text(encoding="utf-8")
    assert "ResearchAgentDefinition" in api_source
    assert "ResearchAgentRun" in api_source
    assert "ResearchAgentValidationResult" in api_source
    assert "listResearchAgents" in api_source
    assert "listResearchAgentRuns" in api_source
    assert "validateResearchAgent" in api_source
    assert "/sessions/research/agents" in api_source

    router_source = (FRONTEND / "main.ts").read_text(encoding="utf-8")
    assert "ResearchAgentsPage" in router_source
    assert "research-agents" in router_source

    left_panel_source = (FRONTEND / "components" / "LeftPanel.vue").read_text(encoding="utf-8")
    assert "handleResearchAgentsTabClick" in left_panel_source
    assert 'title="研究智能体"' in left_panel_source
    assert "/chat/research-agents" in left_panel_source
