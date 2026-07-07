from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from backend.research_assistant.audit import EvidenceAudit
from backend.research_assistant.models import IngestionResult
from backend.research_assistant.subagents import (
    SubagentDefinition,
    validate_subagent_definition,
)

MAX_EVIDENCE_QUOTE_BYTES = 1200


@dataclass(frozen=True)
class PersistSummary:
    paper_id: str
    chunk_count: int
    evidence_record_count: int


@dataclass(frozen=True)
class ResearchProject:
    project_id: str
    user_id: str
    name: str
    description: str
    paper_count: int = 0
    chunk_count: int = 0
    evidence_record_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "paper_count": self.paper_count,
            "chunk_count": self.chunk_count,
            "evidence_record_count": self.evidence_record_count,
            "created_at": _datetime_value(self.created_at),
            "updated_at": _datetime_value(self.updated_at),
        }


@dataclass(frozen=True)
class ResearchProjectPaperAsset:
    paper_id: str
    project_id: str
    session_id: str
    user_id: str
    title: str
    authors: list[str]
    abstract: str
    source_path: str
    parser: str
    source_identity: dict[str, Any]
    chunk_count: int
    evidence_record_count: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def status(self) -> str:
        if self.evidence_record_count > 0 and self.chunk_count > 0:
            return "indexed"
        if self.chunk_count > 0:
            return "parsed"
        return "uploaded"

    @property
    def citation_ready(self) -> bool:
        return self.evidence_record_count > 0

    def to_dict(self) -> dict:
        return {
            "paper_id": self.paper_id,
            "project_id": self.project_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "title": self.title,
            "authors": self.authors,
            "abstract": self.abstract,
            "source_path": self.source_path,
            "parser": self.parser,
            "source_identity": self.source_identity,
            "chunk_count": self.chunk_count,
            "evidence_record_count": self.evidence_record_count,
            "status": self.status,
            "citation_ready": self.citation_ready,
            "created_at": _datetime_value(self.created_at),
            "updated_at": _datetime_value(self.updated_at),
        }


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

    @property
    def partial_claim_count(self) -> int:
        return sum(1 for claim in self.claims if claim.get("status") == "partial")

    def to_dict(self) -> dict:
        return {
            "audit_id": self.audit_id,
            "session_id": self.session_id,
            "subject_type": self.subject_type,
            "subject_id": self.subject_id,
            "status": self.status,
            "claim_count": self.claim_count,
            "approved_claim_count": self.approved_claim_count,
            "partial_claim_count": self.partial_claim_count,
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


async def create_research_project(
    connection: Any,
    *,
    project_id: str,
    user_id: str,
    name: str,
    description: str = "",
) -> ResearchProject:
    row = await connection.fetchrow(
        """
        INSERT INTO research_projects (
            project_id,
            user_id,
            name,
            description,
            updated_at
        )
        VALUES ($1, $2, $3, $4, now())
        RETURNING
            project_id,
            user_id,
            name,
            description,
            created_at,
            updated_at
        """,
        project_id,
        user_id,
        name,
        description,
    )
    return _project_from_row(row)


async def ensure_subagent_definitions(
    connection: Any,
    *,
    definitions: list[SubagentDefinition],
) -> None:
    rows = []
    for definition in definitions:
        validate_subagent_definition(definition)
        rows.append(
            (
                definition.name,
                definition.display_name,
                definition.agent_type,
                definition.source,
                definition.editable,
                definition.description,
                definition.system_prompt,
                _json(definition.skill_refs),
                _json(definition.allowed_tools),
                _json(definition.input_boundaries),
                definition.output_boundary,
                definition.can_answer_user,
                definition.can_write_artifacts,
                definition.enabled,
                definition.version,
                definition.validation_status,
                definition.citation_evidence,
                _json(definition.metadata or {}),
            )
        )

    await connection.executemany(
        """
        INSERT INTO research_subagent_definitions (
            name,
            display_name,
            agent_type,
            source,
            editable,
            description,
            system_prompt,
            skill_refs,
            allowed_tools,
            input_boundaries,
            output_boundary,
            can_answer_user,
            can_write_artifacts,
            enabled,
            version,
            validation_status,
            citation_evidence,
            metadata,
            updated_at
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9::jsonb, $10::jsonb, $11, $12, $13, $14, $15, $16, $17, $18::jsonb, now())
        ON CONFLICT (name) DO NOTHING
        """,
        rows,
    )


async def list_subagent_definitions(
    connection: Any,
    *,
    enabled_only: bool = False,
) -> list[SubagentDefinition]:
    where = "WHERE enabled = true" if enabled_only else ""
    rows = await connection.fetch(
        f"""
        SELECT
            name,
            display_name,
            agent_type,
            source,
            editable,
            description,
            system_prompt,
            skill_refs,
            allowed_tools,
            input_boundaries,
            output_boundary,
            can_answer_user,
            can_write_artifacts,
            enabled,
            version,
            validation_status,
            citation_evidence,
            metadata
        FROM research_subagent_definitions
        {where}
        ORDER BY name
        """
    )
    definitions = [_subagent_definition_from_row(row) for row in rows]
    for definition in definitions:
        validate_subagent_definition(definition)
    return definitions


async def update_subagent_definition(
    connection: Any,
    *,
    name: str,
    updates: dict[str, Any],
) -> SubagentDefinition:
    validation_status = str(updates.get("validation_status") or "draft")
    if bool(updates["enabled"]) and validation_status != "passed":
        raise ValueError("custom Research Agent must pass validation before enablement")

    candidate = SubagentDefinition(
        name=name,
        display_name=str(updates["display_name"]),
        agent_type="custom",
        source="registry",
        editable=True,
        description=str(updates["description"]),
        system_prompt=str(updates["system_prompt"]),
        skill_refs=list(updates["skill_refs"]),
        allowed_tools=list(updates["allowed_tools"]),
        input_boundaries=dict(updates["input_boundaries"]),
        output_boundary=str(updates["output_boundary"]),
        can_answer_user=False,
        can_write_artifacts=False,
        enabled=bool(updates["enabled"]),
        version=1,
        validation_status=validation_status,
        citation_evidence=False,
        metadata=dict(updates.get("metadata") or {}),
    )
    validate_subagent_definition(candidate)

    row = await connection.fetchrow(
        """
        UPDATE research_subagent_definitions
        SET
            display_name = $1,
            description = $2,
            system_prompt = $3,
            skill_refs = $4::jsonb,
            allowed_tools = $5::jsonb,
            input_boundaries = $6::jsonb,
            output_boundary = $7,
            enabled = $8,
            validation_status = $9,
            citation_evidence = $11,
            version = version + 1,
            metadata = $10::jsonb || jsonb_build_object(
                'previous_version', version,
                'rollback_snapshot', jsonb_build_object(
                    'display_name', display_name,
                    'description', description,
                    'system_prompt', system_prompt,
                    'skill_refs', skill_refs,
                    'allowed_tools', allowed_tools,
                    'input_boundaries', input_boundaries,
                    'output_boundary', output_boundary,
                    'enabled', enabled,
                    'validation_status', validation_status,
                    'metadata', metadata
                )
            ),
            updated_at = now()
        WHERE name = $12
          AND agent_type = 'custom'
          AND editable = true
        RETURNING
            name,
            display_name,
            agent_type,
            source,
            editable,
            description,
            system_prompt,
            skill_refs,
            allowed_tools,
            input_boundaries,
            output_boundary,
            can_answer_user,
            can_write_artifacts,
            enabled,
            version,
            validation_status,
            citation_evidence,
            metadata
        """,
        candidate.display_name,
        candidate.description,
        candidate.system_prompt,
        _json(candidate.skill_refs),
        _json(candidate.allowed_tools),
        _json(candidate.input_boundaries),
        candidate.output_boundary,
        candidate.enabled,
        candidate.validation_status,
        _json(candidate.metadata or {}),
        False,
        name,
    )
    if row is None:
        raise ValueError("editable custom Research Agent not found")
    definition = _subagent_definition_from_row(row)
    validate_subagent_definition(definition)
    return definition


async def set_subagent_validation_status(
    connection: Any,
    *,
    name: str,
    status: str,
    validation: dict[str, Any],
    enable: bool = False,
) -> SubagentDefinition:
    if status not in {"passed", "failed", "draft", "disabled"}:
        raise ValueError("validation status is invalid")
    if enable and status != "passed":
        raise ValueError("custom Research Agent can only be enabled after passed validation")
    row = await connection.fetchrow(
        """
        UPDATE research_subagent_definitions
        SET
            validation_status = $1,
            metadata = metadata || jsonb_build_object('validation', $2::jsonb),
            enabled = $3,
            updated_at = now()
        WHERE name = $4
          AND agent_type = 'custom'
          AND editable = true
        RETURNING
            name,
            display_name,
            agent_type,
            source,
            editable,
            description,
            system_prompt,
            skill_refs,
            allowed_tools,
            input_boundaries,
            output_boundary,
            can_answer_user,
            can_write_artifacts,
            enabled,
            version,
            validation_status,
            citation_evidence,
            metadata
        """,
        status,
        _json(validation),
        enable,
        name,
    )
    if row is None:
        raise ValueError("editable custom Research Agent not found")
    definition = _subagent_definition_from_row(row)
    validate_subagent_definition(definition)
    return definition


async def rollback_subagent_definition(
    connection: Any,
    *,
    name: str,
) -> SubagentDefinition:
    row = await connection.fetchrow(
        """
        WITH current_agent AS (
            SELECT
                name,
                metadata->'rollback_snapshot' AS rollback_snapshot,
                version AS previous_version
            FROM research_subagent_definitions
            WHERE name = $1
              AND agent_type = 'custom'
              AND editable = true
              AND metadata ? 'rollback_snapshot'
        )
        UPDATE research_subagent_definitions target
        SET
            display_name = current_agent.rollback_snapshot->>'display_name',
            description = current_agent.rollback_snapshot->>'description',
            system_prompt = current_agent.rollback_snapshot->>'system_prompt',
            skill_refs = current_agent.rollback_snapshot->'skill_refs',
            allowed_tools = current_agent.rollback_snapshot->'allowed_tools',
            input_boundaries = current_agent.rollback_snapshot->'input_boundaries',
            output_boundary = current_agent.rollback_snapshot->>'output_boundary',
            enabled = false,
            validation_status = 'draft',
            metadata = coalesce(current_agent.rollback_snapshot->'metadata', '{}'::jsonb)
                || jsonb_build_object('rolled_back_from_version', current_agent.previous_version),
            version = target.version + 1,
            updated_at = now()
        FROM current_agent
        WHERE target.name = current_agent.name
        RETURNING
            target.name,
            target.display_name,
            target.agent_type,
            target.source,
            target.editable,
            target.description,
            target.system_prompt,
            target.skill_refs,
            target.allowed_tools,
            target.input_boundaries,
            target.output_boundary,
            target.can_answer_user,
            target.can_write_artifacts,
            target.enabled,
            target.version,
            target.validation_status,
            target.citation_evidence,
            target.metadata
        """,
        name,
    )
    if row is None:
        raise ValueError("rollback snapshot not found for editable custom Research Agent")
    definition = _subagent_definition_from_row(row)
    validate_subagent_definition(definition)
    return definition


async def persist_subagent_run(
    connection: Any,
    *,
    task_id: str,
    parent_workflow_id: str,
    agent_name: str,
    agent_role: str,
    status: str,
    input_boundary: dict[str, Any],
    output_boundary: str,
    evidence_refs: list[dict[str, Any]] | None = None,
    outputs: dict[str, Any] | None = None,
    warnings: list[dict[str, Any]] | None = None,
    errors: list[dict[str, Any]] | None = None,
) -> None:
    await connection.execute(
        """
        INSERT INTO research_subagent_runs (
            task_id,
            parent_workflow_id,
            agent_name,
            agent_role,
            status,
            input_boundary,
            output_boundary,
            citation_evidence,
            evidence_refs,
            outputs,
            warnings,
            errors,
            completed_at
        )
        VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8, $9::jsonb, $10::jsonb, $11::jsonb, $12::jsonb,
            CASE WHEN $5 IN ('completed', 'failed', 'cancelled') THEN now() ELSE NULL END)
        ON CONFLICT (task_id) DO UPDATE SET
            parent_workflow_id = EXCLUDED.parent_workflow_id,
            agent_name = EXCLUDED.agent_name,
            agent_role = EXCLUDED.agent_role,
            status = EXCLUDED.status,
            input_boundary = EXCLUDED.input_boundary,
            output_boundary = EXCLUDED.output_boundary,
            citation_evidence = false,
            evidence_refs = EXCLUDED.evidence_refs,
            outputs = EXCLUDED.outputs,
            warnings = EXCLUDED.warnings,
            errors = EXCLUDED.errors,
            completed_at = EXCLUDED.completed_at
        """,
        task_id,
        parent_workflow_id,
        agent_name,
        agent_role,
        status,
        _json(input_boundary),
        output_boundary,
        False,
        _json(evidence_refs or []),
        _json(outputs or {}),
        _json(warnings or []),
        _json(errors or []),
    )


async def list_recent_subagent_runs(
    connection: Any,
    *,
    agent_name: str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    bounded_limit = max(1, min(int(limit), 20))
    rows = await connection.fetch(
        """
        SELECT
            task_id,
            parent_workflow_id,
            agent_name,
            agent_role,
            status,
            input_boundary,
            output_boundary,
            citation_evidence,
            evidence_refs,
            outputs,
            warnings,
            errors,
            started_at,
            completed_at
        FROM research_subagent_runs
        WHERE agent_name = $1
        ORDER BY COALESCE(completed_at, started_at) DESC
        LIMIT $2
        """,
        agent_name,
        bounded_limit,
    )
    return [_subagent_run_from_row(row) for row in rows]


async def list_reader_scope_evidence(
    connection: Any,
    *,
    session_id: str,
    project_id: str | None = None,
    limit: int = 12,
    per_paper_limit: int = 3,
) -> list[dict[str, Any]]:
    rows = await connection.fetch(
        """
        WITH scoped_evidence AS (
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
                dense_rank() OVER (ORDER BY p.updated_at DESC, p.paper_id) AS paper_order,
                row_number() OVER (
                    PARTITION BY c.paper_id
                    ORDER BY COALESCE(er.page_start, c.page_start, 2147483647), er.evidence_id
                ) AS paper_evidence_order
            FROM research_evidence_records er
            JOIN research_chunks c ON c.chunk_id = er.chunk_id
            JOIN research_papers p ON p.paper_id = c.paper_id
            WHERE (p.session_id = $1 OR ($2::text IS NOT NULL AND p.project_id = $2))
              AND er.evidence_type IN ('paper', 'web', 'database')
        )
        SELECT *
        FROM scoped_evidence
        WHERE paper_evidence_order <= $4
        ORDER BY paper_order, paper_evidence_order, evidence_id
        LIMIT $3
        """,
        session_id,
        project_id,
        max(1, int(limit)),
        max(1, int(per_paper_limit)),
    )
    records: list[dict[str, Any]] = []
    for row in rows:
        records.append(
            {
                "evidence_id": int(row["evidence_id"]),
                "chunk_id": str(row["chunk_id"]),
                "paper_id": str(row["paper_id"]),
                "title": str(row["title"]),
                "section": str(row["section"]),
                "page_start": _row_get(row, "page_start"),
                "page_end": _row_get(row, "page_end"),
                "quote": str(row["quote"]),
                "source_type": str(row["evidence_type"]),
                "source_identity": _json_value(_row_get(row, "source_identity"), default={}),
                "evidence_scope": str(_row_get(row, "evidence_scope", "session") or "session"),
            }
        )
    return records


async def list_research_projects(
    connection: Any,
    *,
    user_id: str,
) -> list[ResearchProject]:
    rows = await connection.fetch(
        """
        SELECT
            rp.project_id,
            rp.user_id,
            rp.name,
            rp.description,
            count(DISTINCT p.paper_id)::int AS paper_count,
            count(DISTINCT c.chunk_id)::int AS chunk_count,
            count(DISTINCT er.evidence_id)::int AS evidence_record_count,
            rp.created_at,
            rp.updated_at
        FROM research_projects rp
        LEFT JOIN research_papers p ON p.project_id = rp.project_id
        LEFT JOIN research_chunks c ON c.paper_id = p.paper_id
        LEFT JOIN research_evidence_records er ON er.chunk_id = c.chunk_id
        WHERE rp.user_id = $1
        GROUP BY rp.project_id, rp.user_id, rp.name, rp.description, rp.created_at, rp.updated_at
        ORDER BY rp.updated_at DESC
        """,
        user_id,
    )
    return [_project_from_row(row) for row in rows]


async def list_project_paper_assets(
    connection: Any,
    *,
    project_id: str,
    user_id: str,
) -> list[ResearchProjectPaperAsset]:
    rows = await connection.fetch(
        """
        SELECT
            p.paper_id,
            p.project_id,
            p.session_id,
            p.user_id,
            p.title,
            p.authors,
            p.abstract,
            p.source_path,
            p.parser,
            p.source_identity,
            count(DISTINCT c.chunk_id)::int AS chunk_count,
            count(DISTINCT er.evidence_id)::int AS evidence_record_count,
            p.created_at,
            p.updated_at
        FROM research_papers p
        LEFT JOIN research_chunks c ON c.paper_id = p.paper_id
        LEFT JOIN research_evidence_records er ON er.chunk_id = c.chunk_id
        WHERE p.project_id = $1
            AND p.user_id = $2
        GROUP BY
            p.paper_id,
            p.project_id,
            p.session_id,
            p.user_id,
            p.title,
            p.authors,
            p.abstract,
            p.source_path,
            p.parser,
            p.source_identity,
            p.created_at,
            p.updated_at
        ORDER BY p.updated_at DESC
        """,
        project_id,
        user_id,
    )
    return [_project_paper_asset_from_row(row) for row in rows]


async def upsert_session_research_project(
    connection: Any,
    *,
    session_id: str,
    project_id: str,
    user_id: str,
) -> ResearchProject | None:
    row = await connection.fetchrow(
        """
        WITH binding AS (
            INSERT INTO research_session_projects (
                session_id,
                project_id,
                user_id,
                updated_at
            )
            VALUES ($1, $2, $3, now())
            ON CONFLICT (session_id) DO UPDATE SET
                project_id = EXCLUDED.project_id,
                user_id = EXCLUDED.user_id,
                updated_at = now()
            RETURNING session_id, project_id, user_id
        )
        SELECT
            binding.session_id,
            rp.project_id,
            rp.user_id,
            rp.name,
            rp.description,
            count(DISTINCT p.paper_id)::int AS paper_count,
            count(DISTINCT c.chunk_id)::int AS chunk_count,
            count(DISTINCT er.evidence_id)::int AS evidence_record_count,
            rp.created_at,
            rp.updated_at
        FROM binding
        JOIN research_projects rp ON rp.project_id = binding.project_id
        LEFT JOIN research_papers p ON p.project_id = rp.project_id
        LEFT JOIN research_chunks c ON c.paper_id = p.paper_id
        LEFT JOIN research_evidence_records er ON er.chunk_id = c.chunk_id
        WHERE rp.user_id = $3
        GROUP BY
            binding.session_id,
            rp.project_id,
            rp.user_id,
            rp.name,
            rp.description,
            rp.created_at,
            rp.updated_at
        """,
        session_id,
        project_id,
        user_id,
    )
    if row is None:
        return None
    return _project_from_row(row)


async def get_session_research_project(
    connection: Any,
    *,
    session_id: str,
    user_id: str,
) -> ResearchProject | None:
    row = await connection.fetchrow(
        """
        SELECT
            rsp.session_id,
            rp.project_id,
            rp.user_id,
            rp.name,
            rp.description,
            count(DISTINCT p.paper_id)::int AS paper_count,
            count(DISTINCT c.chunk_id)::int AS chunk_count,
            count(DISTINCT er.evidence_id)::int AS evidence_record_count,
            rp.created_at,
            rp.updated_at
        FROM research_session_projects rsp
        JOIN research_projects rp ON rp.project_id = rsp.project_id
        LEFT JOIN research_papers p ON p.project_id = rp.project_id
        LEFT JOIN research_chunks c ON c.paper_id = p.paper_id
        LEFT JOIN research_evidence_records er ON er.chunk_id = c.chunk_id
        WHERE rsp.session_id = $1
            AND rp.user_id = $2
        GROUP BY
            rsp.session_id,
            rp.project_id,
            rp.user_id,
            rp.name,
            rp.description,
            rp.created_at,
            rp.updated_at
        """,
        session_id,
        user_id,
    )
    if row is None:
        return None
    return _project_from_row(row)


async def persist_ingestion_result(
    connection: Any,
    result: IngestionResult,
    *,
    project_id: str | None = None,
) -> PersistSummary:
    evidence_scope = "project" if project_id else "session"
    async with connection.transaction():
        await connection.execute(
            """
            INSERT INTO research_papers (
                paper_id,
                project_id,
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
            VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8, $9, $10::jsonb, now())
            ON CONFLICT (paper_id) DO UPDATE SET
                project_id = EXCLUDED.project_id,
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
            project_id,
            result.paper.session_id,
            result.paper.user_id,
            _postgres_text(result.paper.title),
            _json(result.paper.authors),
            _postgres_text(result.paper.abstract),
            _postgres_text(result.paper.file_path),
            _postgres_text(result.paper.parser),
            _json(
                {
                    "file_path": result.paper.file_path,
                    "manifest_path": result.artifact.manifest_path,
                    "evidence_preview_path": result.artifact.evidence_preview_path,
                    "evidence_scope": evidence_scope,
                    "project_id": project_id,
                    "session_id": result.paper.session_id,
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
                    _postgres_text(chunk.source.section),
                    chunk.source.page,
                    chunk.source.page,
                    index,
                    _postgres_text(chunk.text),
                    _json(
                        {
                            "paper_id": chunk.source.paper_id,
                            "file_path": chunk.source.file_path,
                            "section": chunk.source.section,
                            "page": chunk.source.page,
                            "evidence_scope": evidence_scope,
                            "project_id": project_id,
                            "session_id": result.paper.session_id,
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
                    _evidence_quote(chunk.text),
                    _postgres_text(chunk.source.section),
                    chunk.source.page,
                    chunk.source.page,
                    _json(
                        {
                            "paper_id": chunk.source.paper_id,
                            "file_path": chunk.source.file_path,
                            "section": chunk.source.section,
                            "page": chunk.source.page,
                            "evidence_scope": evidence_scope,
                            "project_id": project_id,
                            "session_id": result.paper.session_id,
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
            _postgres_text(title),
            _json([]),
            "",
            _postgres_text(url),
            "web-source",
            _json(source_identity),
        )

        chunk_rows = [
            (
                str(chunk["chunk_id"]),
                source_id,
                _postgres_text(chunk.get("section") or "Web"),
                None,
                None,
                index,
                _postgres_text(chunk.get("content") or ""),
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
                _evidence_quote(chunk.get("quote") or chunk.get("content") or ""),
                _postgres_text(chunk.get("section") or "Web"),
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


async def persist_database_evidence_source(
    connection: Any,
    *,
    session_id: str,
    user_id: str,
    source_id: str,
    database_name: str,
    query: str,
    title: str,
    retrieved_at: str,
    chunks: list[dict[str, Any]],
) -> PersistSummary:
    async with connection.transaction():
        source_identity = {
            "source_type": "database",
            "database_name": database_name,
            "query": query,
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
            _postgres_text(title),
            _json([]),
            "",
            _postgres_text(f"database:{database_name}"),
            "database-source",
            _json(source_identity),
        )

        chunk_rows = [
            (
                str(chunk["chunk_id"]),
                source_id,
                _postgres_text(chunk.get("section") or "Database"),
                None,
                None,
                index,
                _postgres_text(chunk.get("content") or ""),
                _json(
                    {
                        **source_identity,
                        "source_id": source_id,
                        "section": str(chunk.get("section") or "Database"),
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
                _evidence_quote(chunk.get("quote") or chunk.get("content") or ""),
                _postgres_text(chunk.get("section") or "Database"),
                None,
                None,
                _json(
                    {
                        **source_identity,
                        "source_id": source_id,
                        "section": str(chunk.get("section") or "Database"),
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
            VALUES ($1, 'database', $2, $3, $4, $5, $6::jsonb)
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
        _postgres_text(title),
        _postgres_text(content),
        _postgres_text(source_subject_type) if source_subject_type is not None else None,
        _postgres_text(source_subject_id) if source_subject_id is not None else None,
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
    return json.dumps(_postgres_text_safe(value), ensure_ascii=False, separators=(",", ":"))


def _postgres_text_safe(value: Any) -> Any:
    if isinstance(value, str):
        return value.replace("\x00", "")
    if isinstance(value, list):
        return [_postgres_text_safe(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_postgres_text_safe(item) for item in value)
    if isinstance(value, dict):
        return {
            _postgres_text_safe(key): _postgres_text_safe(item)
            for key, item in value.items()
        }
    return value


def _postgres_text(value: Any) -> str:
    return str(_postgres_text_safe(value))


def _evidence_quote(value: Any) -> str:
    text = _postgres_text(value).strip()
    if len(text.encode("utf-8")) <= MAX_EVIDENCE_QUOTE_BYTES:
        return text

    marker = "..."
    budget = MAX_EVIDENCE_QUOTE_BYTES - len(marker.encode("utf-8"))
    output: list[str] = []
    used = 0
    for char in text:
        char_size = len(char.encode("utf-8"))
        if used + char_size > budget:
            break
        output.append(char)
        used += char_size
    return "".join(output).rstrip() + marker


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


def _row_get(row: Any, key: str, default: Any = None) -> Any:
    if isinstance(row, dict):
        return row.get(key, default)
    try:
        return row[key]
    except (KeyError, IndexError):
        return default


def _project_from_row(row: Any) -> ResearchProject:
    return ResearchProject(
        project_id=str(row["project_id"]),
        user_id=str(row["user_id"]),
        name=str(row["name"]),
        description=str(row["description"] or ""),
        paper_count=int(_row_get(row, "paper_count", 0) or 0),
        chunk_count=int(_row_get(row, "chunk_count", 0) or 0),
        evidence_record_count=int(_row_get(row, "evidence_record_count", 0) or 0),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _subagent_definition_from_row(row: Any) -> SubagentDefinition:
    validation_status = _normalize_validation_status(str(row["validation_status"]))
    agent_type = str(_row_get(row, "agent_type", "custom"))
    metadata = _json_value(_row_get(row, "metadata", None), default={})
    enabled = bool(row["enabled"])
    if agent_type == "custom" and enabled and validation_status != "passed":
        enabled = False
        metadata = {
            **metadata,
            "auto_disabled_reason": "custom_agent_requires_passed_validation",
        }
    return SubagentDefinition(
        name=str(row["name"]),
        display_name=str(row["display_name"]),
        agent_type=agent_type,
        source=str(_row_get(row, "source", "registry")),
        editable=bool(_row_get(row, "editable", True)),
        description=str(row["description"]),
        system_prompt=str(row["system_prompt"]),
        skill_refs=_json_value(row["skill_refs"], default=[]),
        allowed_tools=_json_value(row["allowed_tools"], default=[]),
        input_boundaries=_json_value(row["input_boundaries"], default={}),
        output_boundary=str(row["output_boundary"]),
        can_answer_user=bool(row["can_answer_user"]),
        can_write_artifacts=bool(row["can_write_artifacts"]),
        enabled=enabled,
        version=int(row["version"] or 1),
        validation_status=validation_status,
        citation_evidence=bool(row["citation_evidence"]),
        metadata=metadata,
    )


def _normalize_validation_status(value: str) -> str:
    return {
        "valid": "passed",
        "invalid": "failed",
    }.get(value, value)


def _iso_datetime(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _subagent_run_from_row(row: Any) -> dict[str, Any]:
    return {
        "task_id": str(row["task_id"]),
        "parent_workflow_id": str(row["parent_workflow_id"]),
        "agent_name": str(row["agent_name"]),
        "agent_role": str(row["agent_role"]),
        "status": str(row["status"]),
        "input_boundary": _json_value(row["input_boundary"], default={}),
        "output_boundary": str(row["output_boundary"]),
        "citation_evidence": bool(row["citation_evidence"]),
        "evidence_refs": _json_value(row["evidence_refs"], default=[]),
        "outputs": _json_value(row["outputs"], default={}),
        "warnings": _json_value(row["warnings"], default=[]),
        "errors": _json_value(row["errors"], default=[]),
        "started_at": _iso_datetime(row["started_at"]),
        "completed_at": _iso_datetime(row["completed_at"]),
    }


def _project_paper_asset_from_row(row: Any) -> ResearchProjectPaperAsset:
    return ResearchProjectPaperAsset(
        paper_id=str(row["paper_id"]),
        project_id=str(row["project_id"]),
        session_id=str(row["session_id"]),
        user_id=str(row["user_id"]),
        title=str(row["title"]),
        authors=_json_value(row["authors"], default=[]),
        abstract=str(row["abstract"] or ""),
        source_path=str(row["source_path"]),
        parser=str(row["parser"]),
        source_identity=_json_value(row["source_identity"], default={}),
        chunk_count=int(row["chunk_count"] or 0),
        evidence_record_count=int(row["evidence_record_count"] or 0),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _datetime_value(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()
