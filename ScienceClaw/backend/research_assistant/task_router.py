from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal
import re

from backend.research_assistant.admission import should_skip_research_retrieval


ResearchTaskType = Literal["general_chat", "evidence_qa", "whole_paper_summary"]
ResearchTaskDecisionSource = Literal["rule", "rule_fallback", "llm"]
MultiAgentDecisionSource = Literal["supervisor_delegation_guard"]


_WHOLE_PAPER_SUMMARY_PATTERNS = (
    "summarize this paper",
    "summarise this paper",
    "summary of this paper",
    "whole paper",
    "entire paper",
    "main contribution",
    "main contributions",
    "core idea",
    "core ideas",
    "总结这篇论文",
    "总结论文",
    "概括这篇论文",
    "概括论文",
    "这篇论文的核心",
    "核心内容",
    "核心观点",
    "主要观点",
    "主要贡献",
    "全文总结",
    "整篇论文",
    "论文讲了什么",
)


@dataclass(frozen=True)
class ResearchTaskRoute:
    route: ResearchTaskType
    decision_source: ResearchTaskDecisionSource
    needs_retrieval: bool
    scope: str
    confidence: float
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ResearchMultiAgentDecision:
    enabled: bool
    decision_source: MultiAgentDecisionSource
    reason: str
    selected_agents: list[str]
    skipped_agents: list[str]
    trigger: str
    available_agent_types: list[str]
    requires_reader: bool
    requires_auditor: bool
    confidence: float

    def to_dict(self) -> dict:
        return asdict(self)


def classify_research_task(question: str) -> ResearchTaskRoute:
    normalized = _normalize_question(question)
    if should_skip_research_retrieval(question):
        return ResearchTaskRoute(
            route="general_chat",
            decision_source="rule",
            needs_retrieval=False,
            scope="none",
            confidence=1.0,
            reason="deterministic_non_evidence_turn",
        )
    if _has_whole_paper_summary_intent(normalized):
        return ResearchTaskRoute(
            route="whole_paper_summary",
            decision_source="rule",
            needs_retrieval=True,
            scope="current_paper",
            confidence=0.95,
            reason="whole_paper_summary_intent",
        )
    return ResearchTaskRoute(
        route="evidence_qa",
        decision_source="rule_fallback",
        needs_retrieval=True,
        scope="project_or_session",
        confidence=0.6,
        reason="default_research_evidence_qa",
    )


def default_evidence_qa_route() -> ResearchTaskRoute:
    return ResearchTaskRoute(
        route="evidence_qa",
        decision_source="rule_fallback",
        needs_retrieval=True,
        scope="project_or_session",
        confidence=0.6,
        reason="default_research_evidence_qa",
    )


def decide_research_multi_agent(question: str) -> ResearchMultiAgentDecision:
    normalized = _normalize_question(question)
    if should_skip_research_retrieval(question):
        return _multi_agent_decision(
            enabled=False,
            reason="simple_or_non_research_turn",
            trigger="single_agent_simple_turn",
            selected_agents=[],
            confidence=0.95,
        )

    has_multi_material = _has_multi_material_signal(normalized)
    has_synthesis = _has_synthesis_intent(normalized)
    has_audit = _has_audit_intent(normalized)

    requires_reader = has_multi_material and has_synthesis
    requires_auditor = has_audit
    selected_agents: list[str] = []
    if requires_reader:
        selected_agents.append("paper_reader_worker")
    if requires_auditor:
        selected_agents.append("research_auditor")

    if selected_agents:
        if requires_reader and requires_auditor:
            trigger = "two_or_more_material_synthesis_with_boundary_audit"
            reason = "The task has multiple materials plus an evidence-boundary or trust-check requirement."
            confidence = 0.86
        elif requires_reader:
            trigger = "two_or_more_material_synthesis"
            reason = "The task asks Supervisor to synthesize two or more materials."
            confidence = 0.78
        else:
            trigger = "boundary_audit_or_trust_check"
            reason = "The task asks for evidence, boundary, citation, or trust review."
            confidence = 0.74
        return _multi_agent_decision(
            enabled=True,
            reason=reason,
            trigger=trigger,
            selected_agents=selected_agents,
            confidence=confidence,
        )

    return _multi_agent_decision(
        enabled=False,
        reason="no_multi_material_or_audit_requirement_detected",
        trigger="single_agent_default",
        selected_agents=[],
        confidence=0.66,
    )


def _normalize_question(question: str) -> str:
    normalized = " ".join(question.strip().lower().split())
    return re.sub(r"[!！。?,，？]+$", "", normalized).strip()


def _has_whole_paper_summary_intent(normalized_question: str) -> bool:
    return any(pattern in normalized_question for pattern in _WHOLE_PAPER_SUMMARY_PATTERNS)


def _multi_agent_decision(
    *,
    enabled: bool,
    reason: str,
    trigger: str,
    selected_agents: list[str],
    confidence: float,
) -> ResearchMultiAgentDecision:
    all_agents = ["paper_reader_worker", "research_auditor"]
    return ResearchMultiAgentDecision(
        enabled=enabled,
        decision_source="supervisor_delegation_guard",
        reason=reason,
        selected_agents=selected_agents,
        skipped_agents=[agent for agent in all_agents if agent not in selected_agents],
        trigger=trigger,
        available_agent_types=["system_builtin", "custom"],
        requires_reader="paper_reader_worker" in selected_agents,
        requires_auditor="research_auditor" in selected_agents,
        confidence=confidence,
    )


def _has_multi_material_signal(normalized_question: str) -> bool:
    patterns = (
        r"\bmaterial\s*[a-d]\b",
        r"\bpaper\s*[1-4]\b",
        r"\bevidence\s*[1-4]\b",
        r"材料\s*[a-dａ-ｄ一二三四1-4]",
        r"论文\s*[a-dａ-ｄ一二三四1-4]",
        r"证据\s*[a-dａ-ｄ一二三四1-4]",
    )
    signal_count = sum(len(re.findall(pattern, normalized_question, flags=re.IGNORECASE)) for pattern in patterns)
    if signal_count >= 2:
        return True
    return any(
        phrase in normalized_question
        for phrase in (
            "two or more",
            "multiple papers",
            "multiple materials",
            "multi-paper",
            "多篇",
            "多篇论文",
            "多个材料",
            "多份材料",
            "几篇论文",
        )
    )


def _has_synthesis_intent(normalized_question: str) -> bool:
    return any(
        keyword in normalized_question
        for keyword in (
            "synthesis",
            "synthesize",
            "compare",
            "comparison",
            "literature review",
            "survey",
            "综述",
            "综合",
            "对比",
            "比较",
            "归纳",
            "总结",
            "提炼",
            "共同点",
            "差异",
        )
    )


def _has_audit_intent(normalized_question: str) -> bool:
    return any(
        keyword in normalized_question
        for keyword in (
            "audit",
            "boundary",
            "trust",
            "verify",
            "verification",
            "citation",
            "evidence check",
            "审计",
            "边界",
            "可信",
            "核查",
            "检查",
            "校验",
            "引用",
            "证据",
            "结论是否",
        )
    )
