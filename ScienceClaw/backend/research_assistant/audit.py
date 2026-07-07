from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Iterable, Protocol


CITATION_EVIDENCE_TYPES = ("paper", "web", "database")
CONTEXT_ONLY_TYPES = ("memory", "model_reasoning", "process_trace", "tool_logs")
PARTIAL_SUPPORT_THRESHOLD = 0.35


class CitationLike(Protocol):
    evidence_id: int
    quote: str
    source_type: str
    citation_label: str


@dataclass(frozen=True)
class EvidenceAuditClaim:
    claim_text: str
    status: str
    evidence_ids: list[int]
    notes: list[str]
    support_score: float = 0.0
    claim_id: str = ""
    support_status: str = ""
    semantic_relevance_score: float = 0.0
    source_quality_score: float = 0.0
    cited_evidence: list[dict] | None = None
    rationale: str = ""
    finding_code: str | None = None

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["support_status"] = self.support_status or _support_status_for_legacy_status(self.status)
        payload["semantic_relevance_score"] = self.semantic_relevance_score or self.support_score
        payload["source_quality_score"] = self.source_quality_score
        payload["cited_evidence"] = self.cited_evidence or []
        payload["rationale"] = self.rationale or " ".join(self.notes)
        return payload


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
    def partial_claim_count(self) -> int:
        return sum(1 for claim in self.claims if claim.status == "partial")

    @property
    def invalid_source_count(self) -> int:
        return sum(1 for claim in self.claims if claim.status == "invalid_source")

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "claim_count": self.claim_count,
            "approved_claim_count": self.approved_claim_count,
            "partial_claim_count": self.partial_claim_count,
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

    claims = [
        _with_claim_id(_audit_claim(claim_text, citation_list), index)
        for index, claim_text in enumerate(claim_texts, start=1)
    ]
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
            support_status=_insufficient_support_status(claim_text),
            semantic_relevance_score=0.0,
            source_quality_score=0.0,
            cited_evidence=[],
            finding_code=_no_citation_finding_code(claim_text),
        )

    claim_body = _claim_body_for_support(claim_text, citations)
    cited_labels = _citation_labels_in_claim(claim_text, citations)
    labeled_citations = [citation for citation in citations if getattr(citation, "citation_label", "")]
    if labeled_citations and not cited_labels:
        nearest_evidence_id, nearest_score = _nearest_citation_support(claim_body, citations)
        nearest_citations = _citations_by_evidence_ids(citations, [nearest_evidence_id] if nearest_evidence_id else [])
        notes = []
        if nearest_evidence_id is not None and nearest_score > 0:
            notes.append(f"Nearest citation evidence: {nearest_evidence_id} with lexical support {nearest_score:.2f}.")
        notes.append("No explicit citation label was attached to this claim.")
        return EvidenceAuditClaim(
            claim_text=claim_text,
            status="unsupported",
            evidence_ids=[],
            notes=notes,
            support_score=nearest_score,
            support_status="unsupported",
            semantic_relevance_score=nearest_score,
            source_quality_score=1.0 if nearest_citations else 0.0,
            cited_evidence=_cited_evidence_dicts(nearest_citations),
            finding_code="semantic_support_missing",
        )

    citation_candidates = [
        citation for citation in citations
        if not labeled_citations or getattr(citation, "citation_label", "") in cited_labels
    ]

    invalid_sources = [
        citation.source_type
        for citation in citation_candidates
        if citation.source_type not in CITATION_EVIDENCE_TYPES
    ]
    if invalid_sources:
        finding_code = (
            "context_only_source_used_as_citation"
            if any(source_type in CONTEXT_ONLY_TYPES for source_type in invalid_sources)
            else "invalid_citation_source_type"
        )
        return EvidenceAuditClaim(
            claim_text=claim_text,
            status="invalid_source",
            evidence_ids=[citation.evidence_id for citation in citation_candidates],
            notes=[
                f"{source_type} is context-only and cannot be used as citation evidence."
                for source_type in sorted(set(invalid_sources))
            ],
            support_score=0.0,
            support_status="source_mismatch",
            semantic_relevance_score=0.0,
            source_quality_score=0.0,
            cited_evidence=_cited_evidence_dicts(citation_candidates),
            finding_code=finding_code,
        )

    missing_quote = [
        citation for citation in citation_candidates
        if not str(getattr(citation, "quote", "") or "").strip()
    ]
    if missing_quote:
        return EvidenceAuditClaim(
            claim_text=claim_text,
            status="unsupported",
            evidence_ids=[citation.evidence_id for citation in missing_quote],
            notes=["A cited source is missing the quote needed for semantic audit."],
            support_score=0.0,
            support_status="insufficient_evidence",
            semantic_relevance_score=0.0,
            source_quality_score=0.0,
            cited_evidence=_cited_evidence_dicts(missing_quote),
            finding_code="source_quote_missing",
        )

    matching = [
        citation.evidence_id
        for citation in citation_candidates
        if _citation_directly_supports_claim(claim_body, citation.quote)
    ]
    if matching:
        return EvidenceAuditClaim(
            claim_text=claim_text,
            status="approved",
            evidence_ids=matching,
            notes=[],
            support_score=1.0,
            support_status="supported",
            semantic_relevance_score=1.0,
            source_quality_score=1.0,
            cited_evidence=_cited_evidence_dicts(
                [citation for citation in citation_candidates if citation.evidence_id in matching]
            ),
            finding_code=None,
        )

    joint_matching = _jointly_supporting_citation_ids(claim_body, citation_candidates)
    if joint_matching:
        return EvidenceAuditClaim(
            claim_text=claim_text,
            status="approved",
            evidence_ids=joint_matching,
            notes=["Multiple cited evidence records jointly support this claim."],
            support_score=1.0,
            support_status="supported",
            semantic_relevance_score=1.0,
            source_quality_score=1.0,
            cited_evidence=_cited_evidence_dicts(
                [citation for citation in citation_candidates if citation.evidence_id in joint_matching]
            ),
            finding_code=None,
        )

    nearest_evidence_id, nearest_score = _nearest_citation_support(claim_body, citation_candidates)
    if (
        cited_labels
        and nearest_evidence_id is not None
        and (
            nearest_score >= 0.9
            or (_sentence_count(claim_body) <= 1 and nearest_score >= PARTIAL_SUPPORT_THRESHOLD)
        )
    ):
        return EvidenceAuditClaim(
            claim_text=claim_text,
            status="partial",
            evidence_ids=[nearest_evidence_id],
            notes=["Cited evidence partially supports this synthesized claim."],
            support_score=nearest_score,
            support_status="partial",
            semantic_relevance_score=nearest_score,
            source_quality_score=1.0,
            cited_evidence=_cited_evidence_dicts(
                [citation for citation in citation_candidates if citation.evidence_id == nearest_evidence_id]
            ),
            finding_code="semantic_support_partial",
        )

    nearest_evidence_id, nearest_score = _nearest_citation_support(claim_body, citations)
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
        support_status="unsupported",
        semantic_relevance_score=nearest_score,
        source_quality_score=1.0 if citation_candidates else 0.0,
        cited_evidence=_cited_evidence_dicts(citation_candidates),
        finding_code="semantic_support_mismatch" if cited_labels else "semantic_support_missing",
    )


def _with_claim_id(claim: EvidenceAuditClaim, index: int) -> EvidenceAuditClaim:
    return EvidenceAuditClaim(
        claim_text=claim.claim_text,
        status=claim.status,
        evidence_ids=claim.evidence_ids,
        notes=claim.notes,
        support_score=claim.support_score,
        claim_id=claim.claim_id or f"claim-{index}",
        support_status=claim.support_status,
        semantic_relevance_score=claim.semantic_relevance_score,
        source_quality_score=claim.source_quality_score,
        cited_evidence=claim.cited_evidence,
        rationale=claim.rationale,
        finding_code=claim.finding_code,
    )


def _support_status_for_legacy_status(status: str) -> str:
    if status == "approved":
        return "supported"
    if status == "invalid_source":
        return "source_mismatch"
    if status in {"partial", "unsupported"}:
        return status
    return "insufficient_evidence"


def _insufficient_support_status(claim_text: str) -> str:
    return "insufficient_evidence" if _looks_like_refusal(claim_text) else "unsupported"


def _no_citation_finding_code(claim_text: str) -> str:
    return "insufficient_evidence_should_refuse" if _looks_like_refusal(claim_text) else "semantic_support_missing"


def _looks_like_refusal(claim_text: str) -> bool:
    normalized = claim_text.casefold()
    return any(
        marker in normalized
        for marker in (
            "insufficient citation evidence",
            "no citation evidence",
            "cannot answer it as a cited research claim",
            "no evidence",
        )
    )


def _cited_evidence_dicts(citations: list[CitationLike]) -> list[dict]:
    return [
        {
            "evidence_id": getattr(citation, "evidence_id", None),
            "source_type": getattr(citation, "source_type", ""),
            "paper_id": getattr(citation, "paper_id", ""),
            "title": getattr(citation, "title", ""),
            "section": getattr(citation, "section", ""),
            "page_start": getattr(citation, "page_start", None),
            "page_end": getattr(citation, "page_end", None),
            "chunk_id": getattr(citation, "chunk_id", ""),
            "quote": getattr(citation, "quote", ""),
        }
        for citation in citations
    ]


def _citations_by_evidence_ids(citations: list[CitationLike], evidence_ids: list[int | None]) -> list[CitationLike]:
    id_set = {evidence_id for evidence_id in evidence_ids if evidence_id is not None}
    return [citation for citation in citations if getattr(citation, "evidence_id", None) in id_set]


def _overall_status(claims: list[EvidenceAuditClaim]) -> str:
    if any(claim.status == "invalid_source" for claim in claims):
        return "invalid_source"
    if all(claim.status == "approved" for claim in claims):
        return "approved"
    if any(claim.status in {"approved", "partial"} for claim in claims):
        return "partial"
    return "unsupported"


def _extract_claim_texts(answer_content: str) -> list[str]:
    claims: list[str] = []
    for raw_line in answer_content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if _is_structural_line(line):
            continue
        line = re.sub(r"^\d+[\.)]\s*", "", line).strip()
        if line:
            claims.append(line)
    return claims


def _is_structural_line(line: str) -> bool:
    normalized = line.strip()
    if not normalized:
        return True
    if re.fullmatch(r"[-*_`#\s]+", normalized):
        return True
    without_list_marker = re.sub(r"^[-*+]\s+", "", normalized).strip()
    without_heading_marker = re.sub(r"^#{1,6}\s+", "", without_list_marker).strip()
    without_markdown = re.sub(r"[*_`]+", "", without_heading_marker).strip()
    if without_markdown.endswith(":"):
        return True
    if not re.search(r"[.!?。！？\]]", without_markdown) and len(_audit_terms(without_markdown)) <= 4:
        return True
    return False


def _normalise_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def _remove_citation_labels(claim_text: str, citations: list[CitationLike]) -> str:
    claim_body = claim_text
    for citation in citations:
        label = getattr(citation, "citation_label", "")
        if label:
            claim_body = claim_body.replace(label, "")
    return _normalise_text(claim_body)


def _claim_body_for_support(claim_text: str, citations: list[CitationLike]) -> str:
    claim_body = _remove_citation_labels(claim_text, citations)
    claim_body = re.sub(r"^[-*+]\s+", "", claim_body).strip()
    claim_body = re.sub(r"^\*\*[^*]{1,80}:\*\*\s*", "", claim_body).strip()
    claim_body = re.sub(r"^[a-z][a-z0-9 /_-]{1,80}:\s+", "", claim_body).strip()
    return _normalise_text(claim_body)


def _citation_labels_in_claim(claim_text: str, citations: list[CitationLike]) -> set[str]:
    return {
        citation.citation_label
        for citation in citations
        if getattr(citation, "citation_label", "") and citation.citation_label in claim_text
    }


def _sentence_count(value: str) -> int:
    sentences = [part for part in re.split(r"[.!?。！？]+", value) if part.strip()]
    return len(sentences)


def _citation_directly_supports_claim(claim_body: str, quote: str) -> bool:
    normalised_quote = _normalise_text(quote)
    if claim_body == normalised_quote:
        return True

    claim_terms = _audit_terms(claim_body)
    quote_terms = _audit_terms(quote)
    return bool(claim_terms) and claim_terms <= quote_terms


def _jointly_supporting_citation_ids(claim_body: str, citations: list[CitationLike]) -> list[int]:
    claim_terms = _audit_terms(claim_body)
    if not claim_terms or len(citations) < 2:
        return []

    contributing: list[tuple[int, set[str]]] = []
    for citation in citations:
        supported_terms = claim_terms & _audit_terms(citation.quote)
        if supported_terms:
            contributing.append((citation.evidence_id, supported_terms))

    if len(contributing) < 2:
        return []

    jointly_supported_terms: set[str] = set()
    for _, supported_terms in contributing:
        jointly_supported_terms |= supported_terms

    if claim_terms <= jointly_supported_terms:
        return [evidence_id for evidence_id, _ in contributing]
    return []


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
