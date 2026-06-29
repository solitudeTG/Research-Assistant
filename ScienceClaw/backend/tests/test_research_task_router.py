from backend.research_assistant.task_router import classify_research_task


def test_research_task_router_skips_obvious_non_evidence_turns():
    route = classify_research_task("谢谢")

    assert route.route == "general_chat"
    assert route.decision_source == "rule"
    assert route.needs_retrieval is False
    assert route.reason == "deterministic_non_evidence_turn"


def test_research_task_router_detects_whole_paper_summary_requests():
    route = classify_research_task("请总结这篇论文的核心内容与主要观点")

    assert route.route == "whole_paper_summary"
    assert route.decision_source == "rule"
    assert route.needs_retrieval is True
    assert route.scope == "current_paper"
    assert route.reason == "whole_paper_summary_intent"


def test_research_task_router_does_not_skip_chinese_research_questions():
    route = classify_research_task("这篇论文的方法是什么？")

    assert route.route == "evidence_qa"
    assert route.needs_retrieval is True


def test_research_task_router_defaults_local_questions_to_evidence_qa():
    route = classify_research_task("ST-ZF 方法如何抑制干扰？")

    assert route.route == "evidence_qa"
    assert route.decision_source == "rule_fallback"
    assert route.needs_retrieval is True
    assert route.scope == "project_or_session"
