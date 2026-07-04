from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from backend.research_assistant.audit import EvidenceAudit
from backend.research_assistant.models import IngestionResult
from backend.research_assistant.retrieval import EvidenceHit, hybrid_search_evidence
from backend.research_assistant.subagents import (
    SubagentDefinition,
    default_subagent_definitions,
)
from backend.research_assistant.storage.repository import (
    PersistSummary,
    ResearchAuditResult,
    ResearchEvidenceRecord,
    ResearchMemoryEntry,
    ResearchProject,
    ResearchProjectPaperAsset,
    create_research_project,
    delete_memory_entry,
    ensure_subagent_definitions,
    get_audit_result,
    get_evidence_record,
    get_session_research_project,
    list_subagent_definitions,
    list_recent_subagent_runs,
    list_project_paper_assets,
    list_memory_entries,
    list_research_projects,
    persist_chunk_embeddings,
    persist_audit_result,
    persist_database_evidence_source,
    persist_web_evidence_source,
    persist_ingestion_result,
    persist_memory_entry,
    persist_report_evidence_map,
    persist_subagent_run,
    update_subagent_definition,
    upsert_session_research_project,
)


async def ensure_research_schema_in_database(database_url: str) -> None:
    import asyncpg

    schema_path = Path(__file__).with_name("schema.sql")
    schema_sql = schema_path.read_text(encoding="utf-8")
    connection = await asyncpg.connect(database_url)
    try:
        await connection.execute(schema_sql)
    finally:
        await connection.close()


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
    *,
    project_id: str | None = None,
) -> PersistSummary:
    import asyncpg

    connection = await asyncpg.connect(database_url)
    try:
        return await persist_ingestion_result(connection, result, project_id=project_id)
    finally:
        await connection.close()


async def create_research_project_in_database(
    database_url: str,
    *,
    project_id: str,
    user_id: str,
    name: str,
    description: str = "",
) -> ResearchProject:
    import asyncpg

    connection = await asyncpg.connect(database_url)
    try:
        return await create_research_project(
            connection,
            project_id=project_id,
            user_id=user_id,
            name=name,
            description=description,
        )
    finally:
        await connection.close()


async def list_research_projects_from_database(
    database_url: str,
    *,
    user_id: str,
) -> list[ResearchProject]:
    import asyncpg

    connection = await asyncpg.connect(database_url)
    try:
        return await list_research_projects(connection, user_id=user_id)
    finally:
        await connection.close()


async def ensure_subagent_definitions_in_database(
    database_url: str,
    *,
    definitions: list[SubagentDefinition] | None = None,
) -> None:
    import asyncpg

    connection = await asyncpg.connect(database_url)
    try:
        await ensure_subagent_definitions(
            connection,
            definitions=definitions or default_subagent_definitions(),
        )
    finally:
        await connection.close()


async def list_subagent_definitions_from_database(
    database_url: str,
    *,
    enabled_only: bool = False,
) -> list[SubagentDefinition]:
    import asyncpg

    connection = await asyncpg.connect(database_url)
    try:
        return await list_subagent_definitions(connection, enabled_only=enabled_only)
    finally:
        await connection.close()


async def update_subagent_definition_in_database(
    database_url: str,
    *,
    name: str,
    updates: dict,
) -> SubagentDefinition:
    import asyncpg

    connection = await asyncpg.connect(database_url)
    try:
        return await update_subagent_definition(connection, name=name, updates=updates)
    finally:
        await connection.close()


async def persist_subagent_run_to_database(
    database_url: str,
    *,
    task_id: str,
    parent_workflow_id: str,
    agent_name: str,
    agent_role: str,
    status: str,
    input_boundary: dict,
    output_boundary: str,
    evidence_refs: list[dict] | None = None,
    outputs: dict | None = None,
    warnings: list[dict] | None = None,
    errors: list[dict] | None = None,
) -> None:
    import asyncpg

    connection = await asyncpg.connect(database_url)
    try:
        await persist_subagent_run(
            connection,
            task_id=task_id,
            parent_workflow_id=parent_workflow_id,
            agent_name=agent_name,
            agent_role=agent_role,
            status=status,
            input_boundary=input_boundary,
            output_boundary=output_boundary,
            evidence_refs=evidence_refs,
            outputs=outputs,
            warnings=warnings,
            errors=errors,
        )
    finally:
        await connection.close()


async def list_recent_subagent_runs_from_database(
    database_url: str,
    *,
    agent_name: str,
    limit: int = 5,
) -> list[dict]:
    import asyncpg

    connection = await asyncpg.connect(database_url)
    try:
        return await list_recent_subagent_runs(connection, agent_name=agent_name, limit=limit)
    finally:
        await connection.close()


async def list_project_paper_assets_from_database(
    database_url: str,
    *,
    project_id: str,
    user_id: str,
) -> list[ResearchProjectPaperAsset]:
    import asyncpg

    connection = await asyncpg.connect(database_url)
    try:
        return await list_project_paper_assets(
            connection,
            project_id=project_id,
            user_id=user_id,
        )
    finally:
        await connection.close()


async def upsert_session_research_project_in_database(
    database_url: str,
    *,
    session_id: str,
    project_id: str,
    user_id: str,
) -> ResearchProject | None:
    import asyncpg

    connection = await asyncpg.connect(database_url)
    try:
        return await upsert_session_research_project(
            connection,
            session_id=session_id,
            project_id=project_id,
            user_id=user_id,
        )
    finally:
        await connection.close()


async def get_session_research_project_from_database(
    database_url: str,
    *,
    session_id: str,
    user_id: str,
) -> ResearchProject | None:
    import asyncpg

    connection = await asyncpg.connect(database_url)
    try:
        return await get_session_research_project(
            connection,
            session_id=session_id,
            user_id=user_id,
        )
    finally:
        await connection.close()


async def hybrid_search_evidence_in_database(
    database_url: str,
    *,
    session_id: str,
    project_id: str | None = None,
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
            project_id=project_id,
            query_text=query_text,
            query_embedding=query_embedding,
            embedding_model=embedding_model,
            limit=limit,
        )
    finally:
        await connection.close()


async def list_whole_paper_evidence_in_database(
    database_url: str,
    *,
    session_id: str,
    project_id: str | None = None,
    limit: int = 24,
    per_section_limit: int = 3,
) -> list[EvidenceHit]:
    import asyncpg

    connection = await asyncpg.connect(database_url)
    try:
        rows = await connection.fetch(
            """
            WITH target_paper AS (
                SELECT p.paper_id
                FROM research_papers p
                WHERE (p.session_id = $1 OR ($2::text IS NOT NULL AND p.project_id = $2))
                ORDER BY
                    CASE WHEN p.session_id = $1 THEN 0 ELSE 1 END,
                    p.updated_at DESC,
                    p.created_at DESC,
                    p.paper_id DESC
                LIMIT 1
            )
            , paper_evidence AS (
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
                    CASE WHEN p.project_id IS NULL THEN 'session' ELSE 'project' END AS evidence_scope,
                    row_number() OVER (
                        PARTITION BY COALESCE(NULLIF(er.section, ''), 'Paper')
                        ORDER BY
                            COALESCE(er.page_start, c.page_start, 2147483647),
                            er.evidence_id
                    ) AS section_evidence_order,
                    min(COALESCE(er.page_start, c.page_start, 2147483647)) OVER (
                        PARTITION BY COALESCE(NULLIF(er.section, ''), 'Paper')
                    ) AS section_first_page
                FROM target_paper tp
                JOIN research_papers p ON p.paper_id = tp.paper_id
                JOIN research_chunks c ON c.paper_id = p.paper_id
                JOIN research_evidence_records er ON er.chunk_id = c.chunk_id
                WHERE er.evidence_type = 'paper'
            )
            SELECT
                evidence_id,
                chunk_id,
                evidence_type,
                paper_id,
                title,
                section,
                page_start,
                page_end,
                quote,
                source_identity,
                evidence_scope,
                row_number() OVER (
                    ORDER BY section_first_page, section_evidence_order, evidence_id
                )::float AS paper_order
            FROM paper_evidence
            WHERE section_evidence_order <= $4
            ORDER BY
                section_first_page,
                section_evidence_order,
                evidence_id
            LIMIT $3
            """,
            session_id,
            project_id,
            limit,
            per_section_limit,
        )
        hits = []
        for row in rows:
            hit = EvidenceHit(
                evidence_id=int(row["evidence_id"]),
                chunk_id=str(row["chunk_id"]),
                paper_id=str(row["paper_id"]),
                title=str(row["title"]),
                source_type=str(row["evidence_type"]),
                section=str(row["section"]),
                page_start=row["page_start"],
                page_end=row["page_end"],
                quote=str(row["quote"]),
                rank_score=1.0 / float(row["paper_order"]),
                source_identity=_source_identity_dict(row["source_identity"]),
                evidence_scope=str(_row_value(row, "evidence_scope") or "session"),
            )
            hits.append(hit)
        return hits
    finally:
        await connection.close()


def _source_identity_dict(value: object) -> dict:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        return json.loads(value)
    return dict(value)  # type: ignore[arg-type]


def _row_value(row: object, key: str, default: object = None) -> object:
    if isinstance(row, dict):
        return row.get(key, default)
    try:
        return row[key]  # type: ignore[index]
    except KeyError:
        return default


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


async def persist_web_evidence_source_to_database(
    database_url: str,
    *,
    session_id: str,
    user_id: str,
    source_id: str,
    url: str,
    title: str,
    retrieved_at: str,
    chunks: list[dict],
) -> PersistSummary:
    import asyncpg

    connection = await asyncpg.connect(database_url)
    try:
        return await persist_web_evidence_source(
            connection,
            session_id=session_id,
            user_id=user_id,
            source_id=source_id,
            url=url,
            title=title,
            retrieved_at=retrieved_at,
            chunks=chunks,
        )
    finally:
        await connection.close()


async def persist_database_evidence_source_to_database(
    database_url: str,
    *,
    session_id: str,
    user_id: str,
    source_id: str,
    database_name: str,
    query: str,
    title: str,
    retrieved_at: str,
    chunks: list[dict],
) -> PersistSummary:
    import asyncpg

    connection = await asyncpg.connect(database_url)
    try:
        return await persist_database_evidence_source(
            connection,
            session_id=session_id,
            user_id=user_id,
            source_id=source_id,
            database_name=database_name,
            query=query,
            title=title,
            retrieved_at=retrieved_at,
            chunks=chunks,
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


async def persist_memory_entry_to_database(
    database_url: str,
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
    import asyncpg

    connection = await asyncpg.connect(database_url)
    try:
        await persist_memory_entry(
            connection,
            memory_id=memory_id,
            session_id=session_id,
            user_id=user_id,
            layer=layer,
            title=title,
            content=content,
            source_subject_type=source_subject_type,
            source_subject_id=source_subject_id,
        )
    finally:
        await connection.close()


async def get_audit_result_from_database(
    database_url: str,
    *,
    session_id: str,
    subject_type: str,
    subject_id: str,
) -> ResearchAuditResult | None:
    import asyncpg

    connection = await asyncpg.connect(database_url)
    try:
        return await get_audit_result(
            connection,
            session_id=session_id,
            subject_type=subject_type,
            subject_id=subject_id,
        )
    finally:
        await connection.close()


async def get_evidence_record_from_database(
    database_url: str,
    *,
    session_id: str,
    evidence_id: int,
) -> ResearchEvidenceRecord | None:
    import asyncpg

    connection = await asyncpg.connect(database_url)
    try:
        return await get_evidence_record(
            connection,
            session_id=session_id,
            evidence_id=evidence_id,
        )
    finally:
        await connection.close()


async def list_memory_entries_from_database(
    database_url: str,
    *,
    session_id: str,
    user_id: str | None = None,
    layer: str | None = None,
    limit: int = 20,
) -> list[ResearchMemoryEntry]:
    import asyncpg

    connection = await asyncpg.connect(database_url)
    try:
        return await list_memory_entries(
            connection,
            session_id=session_id,
            user_id=user_id,
            layer=layer,
            limit=limit,
        )
    finally:
        await connection.close()


async def delete_memory_entry_from_database(
    database_url: str,
    *,
    session_id: str,
    memory_id: str,
) -> bool:
    import asyncpg

    connection = await asyncpg.connect(database_url)
    try:
        return await delete_memory_entry(
            connection,
            session_id=session_id,
            memory_id=memory_id,
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
