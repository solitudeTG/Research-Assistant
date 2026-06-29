from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal
import re

from backend.research_assistant.admission import should_skip_research_retrieval


ResearchTaskType = Literal["general_chat", "evidence_qa", "whole_paper_summary"]
ResearchTaskDecisionSource = Literal["rule", "rule_fallback", "llm"]


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


def _normalize_question(question: str) -> str:
    normalized = " ".join(question.strip().lower().split())
    return re.sub(r"[!！。?,，？]+$", "", normalized).strip()


def _has_whole_paper_summary_intent(normalized_question: str) -> bool:
    return any(pattern in normalized_question for pattern in _WHOLE_PAPER_SUMMARY_PATTERNS)
