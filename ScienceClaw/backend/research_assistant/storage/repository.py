from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.research_assistant.audit import EvidenceAudit
from backend.research_assistant.models import IngestionResult


@dataclass(frozen=True)
class PersistSummary:
    paper_id: str
    chunk_count: int
    evidence_record_count: int


async def persist_ingestion_result(connection: Any, result: IngestionResult) -> PersistSummary:
    async with connection.transaction():
        await connection.execute(
            """
            INSERT INTO research_papers (
                paper_id,
                session_id,
                user_id,
                title,
                authors,
                abstract,
                source_path,
                parser,
                source_identity,
                updated_at
            )
            VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7, $8, $9::jsonb, now())
            ON CONFLICT (paper_id) DO UPDATE SET
                session_id = EXCLUDED.session_id,
                user_id = EXCLUDED.user_id,
                title = EXCLUDED.title,
                authors = EXCLUDED.authors,
                abstract = EXCLUDED.abstract,
                source_path = EXCLUDED.source_path,
                parser = EXCLUDED.parser,
                source_identity = EXCLUDED.source_identity,
                updated_at = now()
            """,
            result.paper.paper_id,
            result.paper.session_id,
            result.paper.user_id,
            result.paper.title,
            _json(result.paper.authors),
            result.paper.abstract,
            result.paper.file_path,
            result.paper.parser,
            _json(
                {
                    "file_path": result.paper.file_path,
                    "manifest_path": result.artifact.manifest_path,
                    "evidence_preview_path": result.artifact.evidence_preview_path,
                }
            ),
        )

        await connection.executemany(
            """
            INSERT INTO research_chunks (
                chunk_id,
                paper_id,
                section,
                page_start,
                page_end,
                chunk_index,
                content,
                source_identity
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb)
            ON CONFLICT (chunk_id) DO UPDATE SET
                section = EXCLUDED.section,
                page_start = EXCLUDED.page_start,
                page_end = EXCLUDED.page_end,
                chunk_index = EXCLUDED.chunk_index,
                content = EXCLUDED.content,
                source_identity = EXCLUDED.source_identity
            """,
            [
                (
                    chunk.chunk_id,
                    chunk.source.paper_id,
                    chunk.source.section,
                    chunk.source.page,
                    chunk.source.page,
                    index,
                    chunk.text,
                    _json(
                        {
                            "paper_id": chunk.source.paper_id,
                            "file_path": chunk.source.file_path,
                            "section": chunk.source.section,
                            "page": chunk.source.page,
                        }
                    ),
                )
                for index, chunk in enumerate(result.chunks, start=1)
            ],
        )

        await connection.executemany(
            """
            INSERT INTO research_evidence_records (
                chunk_id,
                evidence_type,
                quote,
                section,
                page_start,
                page_end,
                source_identity
            )
            VALUES ($1, 'paper', $2, $3, $4, $5, $6::jsonb)
            ON CONFLICT (chunk_id, evidence_type, quote) DO UPDATE SET
                section = EXCLUDED.section,
                page_start = EXCLUDED.page_start,
                page_end = EXCLUDED.page_end,
                source_identity = EXCLUDED.source_identity
            """,
            [
                (
                    chunk.chunk_id,
                    chunk.text,
                    chunk.source.section,
                    chunk.source.page,
                    chunk.source.page,
                    _json(
                        {
                            "paper_id": chunk.source.paper_id,
                            "file_path": chunk.source.file_path,
                            "section": chunk.source.section,
                            "page": chunk.source.page,
                        }
                    ),
                )
                for chunk in result.chunks
            ],
        )

    return PersistSummary(
        paper_id=result.paper.paper_id,
        chunk_count=len(result.chunks),
        evidence_record_count=len(result.chunks),
    )


async def persist_chunk_embeddings(
    connection: Any,
    *,
    embeddings: list[tuple[str, list[float]]],
    embedding_model: str,
) -> None:
    await connection.executemany(
        """
        INSERT INTO research_embeddings (
            chunk_id,
            embedding_model,
            embedding
        )
        VALUES ($1, $2, $3::vector)
        ON CONFLICT (chunk_id, embedding_model) DO UPDATE SET
            embedding = EXCLUDED.embedding
        """,
        [
            (
                chunk_id,
                embedding_model,
                _vector_literal(vector),
            )
            for chunk_id, vector in embeddings
        ],
    )


async def persist_report_evidence_map(
    connection: Any,
    *,
    report_id: str,
    evidence_rows: list[tuple[int, str, str]],
) -> None:
    await connection.executemany(
        """
        INSERT INTO research_report_evidence_map (
            report_id,
            evidence_id,
            markdown_anchor,
            claim_text
        )
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (report_id, evidence_id, markdown_anchor) DO UPDATE SET
            claim_text = EXCLUDED.claim_text
        """,
        [
            (
                report_id,
                evidence_id,
                markdown_anchor,
                claim_text,
            )
            for evidence_id, markdown_anchor, claim_text in evidence_rows
        ],
    )


async def persist_audit_result(
    connection: Any,
    *,
    audit_id: str,
    session_id: str,
    subject_type: str,
    subject_id: str,
    audit: EvidenceAudit,
) -> None:
    await connection.execute(
        """
        INSERT INTO research_audit_results (
            audit_id,
            session_id,
            subject_type,
            subject_id,
            status,
            claim_count,
            approved_claim_count,
            unsupported_claim_count,
            invalid_source_count,
            boundaries,
            claims,
            updated_at
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10::jsonb, $11::jsonb, now())
        ON CONFLICT (subject_type, subject_id) DO UPDATE SET
            audit_id = EXCLUDED.audit_id,
            session_id = EXCLUDED.session_id,
            status = EXCLUDED.status,
            claim_count = EXCLUDED.claim_count,
            approved_claim_count = EXCLUDED.approved_claim_count,
            unsupported_claim_count = EXCLUDED.unsupported_claim_count,
            invalid_source_count = EXCLUDED.invalid_source_count,
            boundaries = EXCLUDED.boundaries,
            claims = EXCLUDED.claims,
            updated_at = now()
        """,
        audit_id,
        session_id,
        subject_type,
        subject_id,
        audit.status,
        audit.claim_count,
        audit.approved_claim_count,
        audit.unsupported_claim_count,
        audit.invalid_source_count,
        _json(audit.boundaries),
        _json([claim.to_dict() for claim in audit.claims]),
    )


def _json(value: Any) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(str(float(value)) for value in values) + "]"
