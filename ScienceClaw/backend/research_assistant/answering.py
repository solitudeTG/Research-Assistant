from __future__ import annotations

from dataclasses import asdict, dataclass, field

import shortuuid

from backend.research_assistant.audit import EvidenceAudit, audit_evidence_claims
from backend.research_assistant.embeddings import HashingEmbeddingProvider
from backend.research_assistant.storage.database import hybrid_search_evidence_in_database


@dataclass(frozen=True)
class ResearchCitation:
    evidence_id: int
    chunk_id: str
    paper_id: str
    title: str
    section: str
    page_start: int | None
    page_end: int | None
    quote: str
    citation_label: str
    source_type: str = "paper"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ResearchAnswer:
    content: str
    citations: list[ResearchCitation]
    audit: EvidenceAudit | None = None
    answer_id: str = field(default_factory=lambda: f"research-answer-{shortuuid.uuid()}")

    def __post_init__(self) -> None:
        if self.audit is None:
            object.__setattr__(
                self,
                "audit",
                audit_evidence_claims(answer_content=self.content, citations=self.citations),
            )

    @property
    def citation_count(self) -> int:
        return len(self.citations)

    def to_dict(self) -> dict:
        return {
            "answer_id": self.answer_id,
            "content": self.content,
            "citations": [citation.to_dict() for citation in self.citations],
            "citation_count": self.citation_count,
            "audit": self.audit.to_dict() if self.audit else {},
        }


async def answer_research_question(
    *,
    database_url: str,
    session_id: str,
    question: str,
    embedding_dimensions: int,
    embedding_model: str,
    limit: int = 5,
) -> ResearchAnswer:
    provider = HashingEmbeddingProvider(
        dimensions=embedding_dimensions,
        model_name=embedding_model,
    )
    hits = await hybrid_search_evidence_in_database(
        database_url,
        session_id=session_id,
        query_text=question,
        query_embedding=provider.embed_text(question),
        embedding_model=provider.model_name,
        limit=limit,
    )
    citations = [
        ResearchCitation(
            evidence_id=hit.evidence_id,
            chunk_id=hit.chunk_id,
            paper_id=hit.paper_id,
            title=hit.title,
            section=hit.section,
            page_start=hit.page_start,
            page_end=hit.page_end,
            quote=hit.quote,
            citation_label=hit.citation_label,
        )
        for hit in hits
    ]
    content = _compose_extractive_answer(citations)
    return ResearchAnswer(
        content=content,
        citations=citations,
        audit=audit_evidence_claims(answer_content=content, citations=citations),
    )


def _compose_extractive_answer(citations: list[ResearchCitation]) -> str:
    if not citations:
        return (
            "No citation evidence was found in the uploaded papers for this question. "
            "I cannot answer it as a cited research claim yet."
        )
    lines = ["Based on uploaded paper evidence:"]
    for index, citation in enumerate(citations, start=1):
        lines.append(f"{index}. {citation.quote} {citation.citation_label}")
    return "\n".join(lines)
