from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
import re

import shortuuid

from backend.research_assistant.audit import EvidenceAudit, audit_evidence_claims
from backend.research_assistant.embeddings import HashingEmbeddingProvider
from backend.research_assistant.storage.database import (
    hybrid_search_evidence_in_database,
    list_memory_entries_from_database,
)

_RECALL_STOP_WORDS = {
    "about",
    "after",
    "also",
    "and",
    "are",
    "can",
    "did",
    "does",
    "for",
    "from",
    "has",
    "have",
    "how",
    "into",
    "that",
    "the",
    "this",
    "what",
    "when",
    "where",
    "which",
    "with",
    "work",
}
_MEMORY_NEGATION_TERMS = {"avoid", "cannot", "don't", "dont", "never", "no", "not", "reject", "without"}


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
    source_identity: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ResearchAnswer:
    content: str
    citations: list[ResearchCitation]
    context_memory: list[dict] = field(default_factory=list)
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

    @property
    def context_memory_count(self) -> int:
        return len(self.context_memory)

    def to_dict(self) -> dict:
        return {
            "answer_id": self.answer_id,
            "content": self.content,
            "citations": [citation.to_dict() for citation in self.citations],
            "citation_count": self.citation_count,
            "context_memory": self.context_memory,
            "context_memory_count": self.context_memory_count,
            "audit": self.audit.to_dict() if self.audit else {},
        }


async def answer_research_question(
    *,
    database_url: str,
    session_id: str,
    user_id: str | None = None,
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
            source_type=hit.source_type,
            source_identity=hit.source_identity,
        )
        for hit in hits
    ]
    context_memory = await _load_context_memory(
        database_url=database_url,
        session_id=session_id,
        user_id=user_id,
        question=question,
    )
    content = _compose_extractive_answer(citations)
    return ResearchAnswer(
        content=content,
        citations=citations,
        context_memory=context_memory,
        audit=audit_evidence_claims(answer_content=content, citations=citations),
    )


def _compose_extractive_answer(citations: list[ResearchCitation]) -> str:
    if not citations:
        return (
            "No citation evidence was found for this question. "
            "I cannot answer it as a cited research claim yet."
        )
    lines = ["Based on citation evidence:"]
    for index, citation in enumerate(citations, start=1):
        lines.append(f"{index}. {citation.quote} {citation.citation_label}")
    return "\n".join(lines)


async def _load_context_memory(
    *,
    database_url: str,
    session_id: str,
    user_id: str | None,
    question: str,
) -> list[dict]:
    memories = await list_memory_entries_from_database(
        database_url,
        session_id=session_id,
        user_id=user_id,
        layer=None,
        limit=5,
    )
    context_rows = []
    for index, memory in enumerate(memories):
        context = memory.to_context_dict()
        if context.get("source_type") != "memory" or context.get("context_only") is not True:
            continue
        relevance_score, matched_terms = _memory_relevance(question=question, context=context)
        if relevance_score <= 0:
            continue
        context_rows.append(
            {
                **context,
                "relevance_score": relevance_score,
                "recall_reason": _memory_recall_reason(context=context, matched_terms=matched_terms),
                "_recall_order": index,
            }
        )
    context_rows.sort(key=lambda row: (-row["relevance_score"], row["_recall_order"]))
    _mark_conflicting_context_memory(context_rows)
    return [{key: value for key, value in row.items() if key != "_recall_order"} for row in context_rows]


def _memory_relevance(*, question: str, context: dict) -> tuple[float, list[str]]:
    question_terms = _recall_terms(question)
    memory_terms = _recall_terms(" ".join([str(context.get("title") or ""), str(context.get("content") or "")]))
    if not question_terms or not memory_terms:
        return 0.0, []
    matched_terms = sorted(question_terms & memory_terms)
    if not matched_terms:
        return 0.0, []
    return round(len(matched_terms) / len(question_terms), 3), matched_terms


def _recall_terms(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-zA-Z0-9]+", text.lower())
        if len(token) > 2 and token not in _RECALL_STOP_WORDS
    }


def _mark_conflicting_context_memory(rows: list[dict]) -> None:
    conflicts: dict[str, set[str]] = {}
    for left_index, left in enumerate(rows):
        left_id = str(left.get("memory_id") or "")
        if not left_id:
            continue
        for right in rows[left_index + 1 :]:
            right_id = str(right.get("memory_id") or "")
            if not right_id:
                continue
            if not _context_memory_conflicts(left, right):
                continue
            conflicts.setdefault(left_id, set()).add(right_id)
            conflicts.setdefault(right_id, set()).add(left_id)

    for row in rows:
        memory_id = str(row.get("memory_id") or "")
        row_conflicts = sorted(conflicts.get(memory_id, set()))
        if not row_conflicts:
            row.setdefault("memory_status", "active")
            continue
        row["memory_status"] = "conflict"
        row["conflicts_with"] = row_conflicts
        row["recall_reason"] = (
            f"{row.get('recall_reason', '').rstrip()} "
            f"conflicts with context-only memory: {', '.join(row_conflicts)}."
        ).strip()


def _context_memory_conflicts(left: dict, right: dict) -> bool:
    left_terms = _memory_topic_terms(left)
    right_terms = _memory_topic_terms(right)
    shared_terms = left_terms & right_terms
    if len(shared_terms) < 3:
        return False
    return _has_memory_negation(left) != _has_memory_negation(right)


def _memory_topic_terms(context: dict) -> set[str]:
    return _recall_terms(" ".join([str(context.get("title") or ""), str(context.get("content") or "")]))


def _has_memory_negation(context: dict) -> bool:
    tokens = set(re.findall(r"[a-zA-Z0-9']+", str(context.get("content") or "").lower()))
    return bool(tokens & _MEMORY_NEGATION_TERMS)


def _memory_recall_reason(*, context: dict, matched_terms: list[str]) -> str:
    layer = context.get("layer") or "research"
    if matched_terms:
        match_text = f"matched question terms: {', '.join(matched_terms[:5])}"
    else:
        match_text = "no direct question-term match"

    source_subject_type = context.get("source_subject_type")
    source_subject_id = context.get("source_subject_id")
    source_text = ""
    if source_subject_type and source_subject_id:
        source_text = f"; source {source_subject_type} {source_subject_id}"

    return f"{layer} memory recalled for this session; {match_text}{source_text}."
