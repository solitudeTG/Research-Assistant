from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Literal, Sequence

from backend.research_assistant.retrieval import EvidenceHit

MIN_EVIDENCE_RELEVANCE_SCORE = 0.015
MIN_ACCEPTED_EVIDENCE_COUNT = 1

_SKIP_UTTERANCES = {
    "thanks",
    "thank you",
    "thx",
    "谢谢",
    "多谢",
    "继续",
    "continue",
    "rewrite",
    "rewrite this paragraph",
}


AdmissionDecision = Literal["skipped", "accepted", "insufficient"]


@dataclass(frozen=True)
class EvidenceAdmissionResult:
    decision: AdmissionDecision
    top_k: int
    threshold: float
    min_accepted_count: int
    accepted_hits: list[EvidenceHit] = field(default_factory=list)
    rejected_count: int = 0
    highest_score: float | None = None
    reason: str = ""

    @property
    def accepted_count(self) -> int:
        return len(self.accepted_hits)

    def to_dict(self) -> dict:
        return {
            "decision": self.decision,
            "top_k": self.top_k,
            "threshold": self.threshold,
            "min_accepted_count": self.min_accepted_count,
            "accepted_count": self.accepted_count,
            "rejected_count": self.rejected_count,
            "highest_score": self.highest_score,
            "reason": self.reason,
        }


def should_skip_research_retrieval(question: str) -> bool:
    normalized = " ".join(question.strip().lower().split())
    normalized = re.sub(r"[!！。.,，?？]+$", "", normalized).strip()
    if not normalized:
        return True
    if normalized in _SKIP_UTTERANCES:
        return True
    if normalized.startswith("rewrite ") and len(normalized.split()) <= 8:
        return True
    return False


def skipped_admission_result() -> EvidenceAdmissionResult:
    return EvidenceAdmissionResult(
        decision="skipped",
        top_k=0,
        threshold=MIN_EVIDENCE_RELEVANCE_SCORE,
        min_accepted_count=MIN_ACCEPTED_EVIDENCE_COUNT,
        accepted_hits=[],
        rejected_count=0,
        highest_score=None,
        reason="deterministic_non_evidence_turn",
    )


def admit_evidence_hits(hits: Sequence[EvidenceHit]) -> EvidenceAdmissionResult:
    hit_list = list(hits)
    accepted = [
        hit
        for hit in hit_list
        if float(hit.rank_score) >= MIN_EVIDENCE_RELEVANCE_SCORE
    ]
    highest_score = max((float(hit.rank_score) for hit in hit_list), default=None)
    if len(accepted) >= MIN_ACCEPTED_EVIDENCE_COUNT:
        return EvidenceAdmissionResult(
            decision="accepted",
            top_k=len(hit_list),
            threshold=MIN_EVIDENCE_RELEVANCE_SCORE,
            min_accepted_count=MIN_ACCEPTED_EVIDENCE_COUNT,
            accepted_hits=accepted,
            rejected_count=len(hit_list) - len(accepted),
            highest_score=highest_score,
            reason="accepted_relevance_threshold",
        )
    return EvidenceAdmissionResult(
        decision="insufficient",
        top_k=len(hit_list),
        threshold=MIN_EVIDENCE_RELEVANCE_SCORE,
        min_accepted_count=MIN_ACCEPTED_EVIDENCE_COUNT,
        accepted_hits=[],
        rejected_count=len(hit_list),
        highest_score=highest_score,
        reason="below_relevance_or_count_threshold",
    )
