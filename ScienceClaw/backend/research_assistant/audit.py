from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Iterable, Protocol


CITATION_EVIDENCE_TYPES = ("paper",)
CONTEXT_ONLY_TYPES = ("memory", "model_reasoning", "process_trace", "tool_logs")


class CitationLike(Protocol):
    evidence_id: int
    quote: str
    source_type: str


@dataclass(frozen=True)
class EvidenceAuditClaim:
    claim_text: str
    status: str
    evidence_ids: list[int]
    notes: list[str]
    support_score: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceAudit:
    status: str
    claims: list[EvidenceAuditClaim]
    boundaries: dict[str, list[str]]

    @property
    def claim_count(self) -> int:
        return len(self.claims)

    @property
    def approved_claim_count(self) -> int:
        return sum(1 for claim in self.claims if claim.status == "approved")

    @property
    def unsupported_claim_count(self) -> int:
        return sum(1 for claim in self.claims if claim.status == "unsupported")

    @property
    def invalid_source_count(self) -> int:
        return sum(1 for claim in self.claims if claim.status == "invalid_source")

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "claim_count": self.claim_count,
            "approved_claim_count": self.approved_claim_count,
            "unsupported_claim_count": self.unsupported_claim_count,
            "invalid_source_count": self.invalid_source_count,
            "boundaries": self.boundaries,
            "claims": [claim.to_dict() for claim in self.claims],
        }


def audit_evidence_claims(
    *,
    answer_content: str,
    citations: Iterable[CitationLike],
) -> EvidenceAudit:
    citation_list = list(citations)
    claim_texts = _extract_claim_texts(answer_content)
    if not claim_texts:
        claim_texts = [answer_content.strip()] if answer_content.strip() else ["No answer content."]

    claims = [_audit_claim(claim_text, citation_list) for claim_text in claim_texts]
    return EvidenceAudit(
        status=_overall_status(claims),
        claims=claims,
        boundaries={
            "citation_evidence": list(CITATION_EVIDENCE_TYPES),
            "context_only": list(CONTEXT_ONLY_TYPES),
        },
    )


def _audit_claim(claim_text: str, citations: list[CitationLike]) -> EvidenceAuditClaim:
    if not citations:
        return EvidenceAuditClaim(
            claim_text=claim_text,
            status="unsupported",
            evidence_ids=[],
            notes=["No citation evidence was attached to this claim."],
            support_score=0.0,
        )

    invalid_sources = [
        citation.source_type
        for citation in citations
        if citation.source_type not in CITATION_EVIDENCE_TYPES
    ]
    if invalid_sources:
        return EvidenceAuditClaim(
            claim_text=claim_text,
            status="invalid_source",
            evidence_ids=[citation.evidence_id for citation in citations],
            notes=[
                f"{source_type} is context-only and cannot be used as citation evidence."
                for source_type in sorted(set(invalid_sources))
            ],
            support_score=0.0,
        )

    matching = [
        citation.evidence_id
        for citation in citations
        if _normalise_text(citation.quote) in _normalise_text(claim_text)
        or citation.quote.strip() == claim_text.strip()
    ]
    if matching:
        return EvidenceAuditClaim(
            claim_text=claim_text,
            status="approved",
            evidence_ids=matching,
            notes=[],
            support_score=1.0,
        )

    nearest_evidence_id, nearest_score = _nearest_citation_support(claim_text, citations)
    notes = []
    if nearest_evidence_id is not None and nearest_score > 0:
        notes.append(f"Nearest citation evidence: {nearest_evidence_id} with lexical support {nearest_score:.2f}.")
    notes.append("No attached citation quote directly supports this claim.")
    return EvidenceAuditClaim(
        claim_text=claim_text,
        status="unsupported",
        evidence_ids=[],
        notes=notes,
        support_score=nearest_score,
    )


def _overall_status(claims: list[EvidenceAuditClaim]) -> str:
    if any(claim.status == "invalid_source" for claim in claims):
        return "invalid_source"
    if all(claim.status == "approved" for claim in claims):
        return "approved"
    if any(claim.status == "approved" for claim in claims):
        return "partial"
    return "unsupported"


def _extract_claim_texts(answer_content: str) -> list[str]:
    claims: list[str] = []
    for raw_line in answer_content.splitlines():
        line = raw_line.strip()
        if not line or line.endswith(":"):
            continue
        line = re.sub(r"^\d+[\.)]\s*", "", line).strip()
        if line:
            claims.append(line)
    return claims


def _normalise_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def _nearest_citation_support(claim_text: str, citations: list[CitationLike]) -> tuple[int | None, float]:
    scored = [
        (citation.evidence_id, _lexical_support_score(claim_text, citation.quote))
        for citation in citations
    ]
    if not scored:
        return None, 0.0
    evidence_id, score = max(scored, key=lambda item: item[1])
    return evidence_id, score


def _lexical_support_score(claim_text: str, quote: str) -> float:
    claim_terms = _audit_terms(claim_text)
    quote_terms = _audit_terms(quote)
    if not claim_terms or not quote_terms:
        return 0.0
    return round(len(claim_terms & quote_terms) / len(claim_terms), 3)


def _audit_terms(value: str) -> set[str]:
    stop_words = {
        "about",
        "also",
        "and",
        "are",
        "based",
        "does",
        "for",
        "from",
        "has",
        "have",
        "into",
        "paper",
        "say",
        "says",
        "the",
        "this",
        "uploaded",
        "what",
        "with",
    }
    return {
        token
        for token in re.findall(r"[a-zA-Z0-9]+", value.casefold())
        if len(token) > 2 and token not in stop_words
    }
