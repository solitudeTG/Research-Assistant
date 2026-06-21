from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Sequence


@dataclass(frozen=True)
class EvidenceHit:
    evidence_id: int
    chunk_id: str
    paper_id: str
    title: str
    section: str
    page_start: int | None
    page_end: int | None
    quote: str
    rank_score: float
    source_type: str = "paper"
    source_identity: dict[str, Any] = field(default_factory=dict)

    @property
    def citation_label(self) -> str:
        if self.page_start is None:
            return f"[{self.paper_id}:{self.section}]"
        if self.page_end and self.page_end != self.page_start:
            return f"[{self.paper_id}:{self.section}:{self.page_start}-{self.page_end}]"
        return f"[{self.paper_id}:{self.section}:{self.page_start}]"


async def hybrid_search_evidence(
    connection: Any,
    *,
    session_id: str,
    query_text: str,
    query_embedding: Sequence[float],
    embedding_model: str,
    limit: int = 8,
) -> list[EvidenceHit]:
    rows = await connection.fetch(
        """
        WITH lexical_candidates AS (
            SELECT
                c.chunk_id,
                row_number() OVER (
                    ORDER BY ts_rank_cd(c.content_tsv, websearch_to_tsquery('english', $2)) DESC
                ) AS lexical_rank
            FROM research_chunks c
            JOIN research_papers p ON p.paper_id = c.paper_id
            WHERE p.session_id = $1
              AND c.content_tsv @@ websearch_to_tsquery('english', $2)
            LIMIT $5
        ),
        vector_candidates AS (
            SELECT
                e.chunk_id,
                row_number() OVER (
                    ORDER BY e.embedding <=> $3::vector
                ) AS vector_rank
            FROM research_embeddings e
            JOIN research_chunks c ON c.chunk_id = e.chunk_id
            JOIN research_papers p ON p.paper_id = c.paper_id
            WHERE p.session_id = $1
              AND e.embedding_model = $4
            LIMIT $5
        ),
        fused_candidates AS (
            SELECT
                coalesce(l.chunk_id, v.chunk_id) AS chunk_id,
                coalesce(1.0 / (60 + l.lexical_rank), 0) +
                coalesce(1.0 / (60 + v.vector_rank), 0) AS rank_score
            FROM lexical_candidates l
            FULL OUTER JOIN vector_candidates v ON v.chunk_id = l.chunk_id
        )
        SELECT
            er.evidence_id,
            er.chunk_id,
            er.evidence_type,
            c.paper_id,
            p.title,
            er.section,
            er.page_start,
            er.page_end,
            er.quote,
            er.source_identity,
            fc.rank_score
        FROM fused_candidates fc
        JOIN research_evidence_records er ON er.chunk_id = fc.chunk_id
        JOIN research_chunks c ON c.chunk_id = er.chunk_id
        JOIN research_papers p ON p.paper_id = c.paper_id
        WHERE er.evidence_type IN ('paper', 'database', 'web')
        ORDER BY fc.rank_score DESC, er.evidence_id ASC
        LIMIT $5
        """,
        session_id,
        query_text,
        _vector_literal(query_embedding),
        embedding_model,
        limit,
    )
    return [_row_to_hit(row) for row in rows]


def _row_to_hit(row: Any) -> EvidenceHit:
    return EvidenceHit(
        evidence_id=int(row["evidence_id"]),
        chunk_id=str(row["chunk_id"]),
        paper_id=str(row["paper_id"]),
        title=str(row["title"]),
        source_type=str(row["evidence_type"]),
        section=str(row["section"]),
        page_start=row["page_start"],
        page_end=row["page_end"],
        quote=str(row["quote"]),
        rank_score=float(row["rank_score"]),
        source_identity=_json_value(_row_value(row, "source_identity")),
    )


def _vector_literal(values: Sequence[float]) -> str:
    return "[" + ",".join(str(float(value)) for value in values) + "]"


def _json_value(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        return json.loads(value)
    return dict(value)


def _row_value(row: Any, key: str) -> Any:
    if isinstance(row, dict):
        return row.get(key)
    try:
        return row[key]
    except KeyError:
        return None
