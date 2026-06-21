from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from backend.research_assistant.audit import EvidenceAudit
from backend.research_assistant.models import IngestionResult


@dataclass(frozen=True)
class PersistSummary:
    paper_id: str
    chunk_count: int
    evidence_record_count: int


@dataclass(frozen=True)
class ResearchAuditResult:
    audit_id: str
    session_id: str
    subject_type: str
    subject_id: str
    status: str
    claim_count: int
    approved_claim_count: int
    unsupported_claim_count: int
    invalid_source_count: int
    boundaries: dict[str, Any]
    claims: list[dict[str, Any]]

    def to_dict(self) -> dict:
        return {
            "audit_id": self.audit_id,
            "session_id": self.session_id,
            "subject_type": self.subject_type,
            "subject_id": self.subject_id,
            "status": self.status,
            "claim_count": self.claim_count,
            "approved_claim_count": self.approved_claim_count,
            "unsupported_claim_count": self.unsupported_claim_count,
            "invalid_source_count": self.invalid_source_count,
            "boundaries": self.boundaries,
            "claims": self.claims,
        }


@dataclass(frozen=True)
class ResearchEvidenceRecord:
    evidence_id: int
    evidence_type: str
    chunk_id: str
    paper_id: str
    title: str
    section: str
    page_start: int | None
    page_end: int | None
    quote: str
    chunk_content: str
    source_identity: dict[str, Any]

    def to_dict(self) -> dict:
        return {
            "evidence_id": self.evidence_id,
            "evidence_type": self.evidence_type,
            "chunk_id": self.chunk_id,
            "paper_id": self.paper_id,
            "title": self.title,
            "section": self.section,
            "page_start": self.page_start,
            "page_end": self.page_end,
            "quote": self.quote,
            "chunk_content": self.chunk_content,
            "source_identity": self.source_identity,
        }


@dataclass(frozen=True)
class ResearchMemoryEntry:
    memory_id: str
    session_id: str
    user_id: str
    layer: str
    title: str
    content: str
    source_type: str
    context_only: bool
    source_subject_type: str | None
    source_subject_id: str | None
    created_at: datetime | None = None

    def to_context_dict(self) -> dict:
        return {
            "memory_id": self.memory_id,
            "layer": self.layer,
            "title": self.title,
            "content": self.content,
            "source_type": self.source_type,
            "context_only": self.context_only,
            "source_subject_type": self.source_subject_type,
            "source_subject_id": self.source_subject_id,
        }


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


async def persist_web_evidence_source(
    connection: Any,
    *,
    session_id: str,
    user_id: str,
    source_id: str,
    url: str,
    title: str,
    retrieved_at: str,
    chunks: list[dict[str, Any]],
) -> PersistSummary:
    async with connection.transaction():
        source_identity = {
            "source_type": "web",
            "url": url,
            "retrieved_at": retrieved_at,
        }
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
            source_id,
            session_id,
            user_id,
            title,
            _json([]),
            "",
            url,
            "web-source",
            _json(source_identity),
        )

        chunk_rows = [
            (
                str(chunk["chunk_id"]),
                source_id,
                str(chunk.get("section") or "Web"),
                None,
                None,
                index,
                str(chunk.get("content") or ""),
                _json(
                    {
                        **source_identity,
                        "source_id": source_id,
                        "section": str(chunk.get("section") or "Web"),
                    }
                ),
            )
            for index, chunk in enumerate(chunks, start=1)
        ]
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
            chunk_rows,
        )

        evidence_rows = [
            (
                str(chunk["chunk_id"]),
                str(chunk.get("quote") or chunk.get("content") or ""),
                str(chunk.get("section") or "Web"),
                None,
                None,
                _json(
                    {
                        **source_identity,
                        "source_id": source_id,
                        "section": str(chunk.get("section") or "Web"),
                    }
                ),
            )
            for chunk in chunks
        ]
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
            VALUES ($1, 'web', $2, $3, $4, $5, $6::jsonb)
            ON CONFLICT (chunk_id, evidence_type, quote) DO UPDATE SET
                section = EXCLUDED.section,
                page_start = EXCLUDED.page_start,
                page_end = EXCLUDED.page_end,
                source_identity = EXCLUDED.source_identity
            """,
            evidence_rows,
        )

    return PersistSummary(
        paper_id=source_id,
        chunk_count=len(chunks),
        evidence_record_count=len(chunks),
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


async def get_audit_result(
    connection: Any,
    *,
    session_id: str,
    subject_type: str,
    subject_id: str,
) -> ResearchAuditResult | None:
    row = await connection.fetchrow(
        """
        SELECT
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
            claims
        FROM research_audit_results
        WHERE session_id = $1
            AND subject_type = $2
            AND subject_id = $3
        """,
        session_id,
        subject_type,
        subject_id,
    )
    if row is None:
        return None
    return ResearchAuditResult(
        audit_id=row["audit_id"],
        session_id=row["session_id"],
        subject_type=row["subject_type"],
        subject_id=row["subject_id"],
        status=row["status"],
        claim_count=int(row["claim_count"]),
        approved_claim_count=int(row["approved_claim_count"]),
        unsupported_claim_count=int(row["unsupported_claim_count"]),
        invalid_source_count=int(row["invalid_source_count"]),
        boundaries=_json_value(row["boundaries"], default={}),
        claims=_json_value(row["claims"], default=[]),
    )


async def get_evidence_record(
    connection: Any,
    *,
    session_id: str,
    evidence_id: int,
) -> ResearchEvidenceRecord | None:
    row = await connection.fetchrow(
        """
        SELECT
            er.evidence_id,
            er.evidence_type,
            er.chunk_id,
            c.paper_id,
            p.title,
            er.section,
            er.page_start,
            er.page_end,
            er.quote,
            c.content AS chunk_content,
            er.source_identity
        FROM research_evidence_records er
        JOIN research_chunks c ON c.chunk_id = er.chunk_id
        JOIN research_papers p ON p.paper_id = c.paper_id
        WHERE p.session_id = $1
            AND er.evidence_id = $2
            AND er.evidence_type IN ('paper', 'database', 'web')
        """,
        session_id,
        evidence_id,
    )
    if row is None:
        return None
    return ResearchEvidenceRecord(
        evidence_id=int(row["evidence_id"]),
        evidence_type=str(row["evidence_type"]),
        chunk_id=str(row["chunk_id"]),
        paper_id=str(row["paper_id"]),
        title=str(row["title"]),
        section=str(row["section"]),
        page_start=row["page_start"],
        page_end=row["page_end"],
        quote=str(row["quote"]),
        chunk_content=str(row["chunk_content"]),
        source_identity=_json_value(row["source_identity"], default={}),
    )


async def persist_memory_entry(
    connection: Any,
    *,
    memory_id: str,
    session_id: str,
    user_id: str,
    layer: str,
    title: str,
    content: str,
    source_subject_type: str | None = None,
    source_subject_id: str | None = None,
) -> None:
    await connection.execute(
        """
        INSERT INTO research_memory_entries (
            memory_id,
            session_id,
            user_id,
            layer,
            title,
            content,
            source_type,
            context_only,
            source_subject_type,
            source_subject_id,
            updated_at
        )
        VALUES ($1, $2, $3, $4, $5, $6, 'memory', true, $7, $8, now())
        ON CONFLICT (memory_id) DO UPDATE SET
            session_id = EXCLUDED.session_id,
            user_id = EXCLUDED.user_id,
            layer = EXCLUDED.layer,
            title = EXCLUDED.title,
            content = EXCLUDED.content,
            source_type = 'memory',
            context_only = true,
            source_subject_type = EXCLUDED.source_subject_type,
            source_subject_id = EXCLUDED.source_subject_id,
            updated_at = now()
        """,
        memory_id,
        session_id,
        user_id,
        _normalise_memory_layer(layer),
        title,
        content,
        source_subject_type,
        source_subject_id,
    )


async def list_memory_entries(
    connection: Any,
    *,
    session_id: str,
    user_id: str | None = None,
    layer: str | None = None,
    limit: int = 20,
) -> list[ResearchMemoryEntry]:
    row_limit = max(1, min(limit, 100))
    rows = await connection.fetch(
        """
        SELECT
            memory_id,
            session_id,
            user_id,
            layer,
            title,
            content,
            source_type,
            context_only,
            source_subject_type,
            source_subject_id,
            created_at
        FROM research_memory_entries
        WHERE (
                session_id = $1
                OR ($2::text IS NOT NULL AND user_id = $2 AND layer IN ('l2', 'l3'))
            )
            AND ($3::text IS NULL OR layer = $3)
            AND source_type = 'memory'
            AND context_only = true
        ORDER BY created_at DESC
        LIMIT $4
        """,
        session_id,
        user_id,
        _normalise_memory_layer(layer) if layer else None,
        row_limit,
    )
    return [
        ResearchMemoryEntry(
            memory_id=row["memory_id"],
            session_id=row["session_id"],
            user_id=row["user_id"],
            layer=row["layer"],
            title=row["title"],
            content=row["content"],
            source_type=row["source_type"],
            context_only=bool(row["context_only"]),
            source_subject_type=row["source_subject_type"],
            source_subject_id=row["source_subject_id"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


async def delete_memory_entry(
    connection: Any,
    *,
    session_id: str,
    memory_id: str,
) -> bool:
    status = await connection.execute(
        """
        DELETE FROM research_memory_entries
        WHERE session_id = $1
            AND memory_id = $2
            AND source_type = 'memory'
            AND context_only = true
        """,
        session_id,
        memory_id,
    )
    return str(status).upper().endswith(" 1")


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _json_value(value: Any, *, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, str):
        return json.loads(value)
    return value


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(str(float(value)) for value in values) + "]"


def _normalise_memory_layer(layer: str) -> str:
    normalised = layer.strip().lower()
    if normalised not in {"l1", "l2", "l3"}:
        raise ValueError("memory layer must be one of L1, L2, or L3")
    return normalised
