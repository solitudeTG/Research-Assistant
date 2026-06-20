from __future__ import annotations

from dataclasses import dataclass

from backend.research_assistant.audit import EvidenceAudit
from backend.research_assistant.models import IngestionResult
from backend.research_assistant.retrieval import EvidenceHit, hybrid_search_evidence
from backend.research_assistant.storage.repository import (
    PersistSummary,
    persist_chunk_embeddings,
    persist_audit_result,
    persist_ingestion_result,
    persist_report_evidence_map,
)


@dataclass(frozen=True)
class ResearchSessionStatus:
    session_id: str
    paper_count: int
    chunk_count: int

    @property
    def has_indexed_papers(self) -> bool:
        return self.paper_count > 0 and self.chunk_count > 0

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "paper_count": self.paper_count,
            "chunk_count": self.chunk_count,
            "has_indexed_papers": self.has_indexed_papers,
        }


async def persist_ingestion_result_to_database(
    database_url: str,
    result: IngestionResult,
) -> PersistSummary:
    import asyncpg

    connection = await asyncpg.connect(database_url)
    try:
        return await persist_ingestion_result(connection, result)
    finally:
        await connection.close()


async def hybrid_search_evidence_in_database(
    database_url: str,
    *,
    session_id: str,
    query_text: str,
    query_embedding: list[float],
    embedding_model: str,
    limit: int = 8,
) -> list[EvidenceHit]:
    import asyncpg

    connection = await asyncpg.connect(database_url)
    try:
        return await hybrid_search_evidence(
            connection,
            session_id=session_id,
            query_text=query_text,
            query_embedding=query_embedding,
            embedding_model=embedding_model,
            limit=limit,
        )
    finally:
        await connection.close()


async def persist_chunk_embeddings_to_database(
    database_url: str,
    *,
    embeddings: list[tuple[str, list[float]]],
    embedding_model: str,
) -> None:
    import asyncpg

    connection = await asyncpg.connect(database_url)
    try:
        await persist_chunk_embeddings(
            connection,
            embeddings=embeddings,
            embedding_model=embedding_model,
        )
    finally:
        await connection.close()


async def persist_report_evidence_map_to_database(
    database_url: str,
    *,
    report_id: str,
    evidence_rows: list[tuple[int, str, str]],
) -> None:
    import asyncpg

    connection = await asyncpg.connect(database_url)
    try:
        await persist_report_evidence_map(
            connection,
            report_id=report_id,
            evidence_rows=evidence_rows,
        )
    finally:
        await connection.close()


async def persist_audit_result_to_database(
    database_url: str,
    *,
    audit_id: str,
    session_id: str,
    subject_type: str,
    subject_id: str,
    audit: EvidenceAudit,
) -> None:
    import asyncpg

    connection = await asyncpg.connect(database_url)
    try:
        await persist_audit_result(
            connection,
            audit_id=audit_id,
            session_id=session_id,
            subject_type=subject_type,
            subject_id=subject_id,
            audit=audit,
        )
    finally:
        await connection.close()


async def get_research_session_status_from_database(
    database_url: str,
    *,
    session_id: str,
) -> ResearchSessionStatus:
    import asyncpg

    connection = await asyncpg.connect(database_url)
    try:
        row = await connection.fetchrow(
            """
            SELECT
                count(DISTINCT p.paper_id)::int AS paper_count,
                count(c.chunk_id)::int AS chunk_count
            FROM research_papers p
            LEFT JOIN research_chunks c ON c.paper_id = p.paper_id
            WHERE p.session_id = $1
            """,
            session_id,
        )
        return ResearchSessionStatus(
            session_id=session_id,
            paper_count=int(row["paper_count"] or 0),
            chunk_count=int(row["chunk_count"] or 0),
        )
    finally:
        await connection.close()
