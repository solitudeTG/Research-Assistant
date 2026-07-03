from pathlib import Path


def test_research_store_schema_defines_pgvector_and_evidence_tables():
    schema = (
        Path(__file__).resolve().parents[1]
        / "research_assistant"
        / "storage"
        / "schema.sql"
    )

    assert schema.is_file()
    sql = schema.read_text(encoding="utf-8").lower()

    assert "create extension if not exists vector" in sql
    for table_name in [
        "research_projects",
        "research_papers",
        "research_chunks",
        "research_embeddings",
        "research_evidence_records",
        "research_citations",
        "research_report_evidence_map",
        "research_audit_results",
        "research_memory_entries",
        "research_session_projects",
        "research_subagent_definitions",
        "research_subagent_runs",
    ]:
        assert f"create table if not exists {table_name}" in sql

    assert "tsvector" in sql
    assert "vector(" in sql
    assert "layer text not null check (layer in ('l1', 'l2', 'l3'))" in sql
    assert "source_type text not null default 'memory' check (source_type = 'memory')" in sql
    assert "context_only boolean not null default true check (context_only = true)" in sql
    assert "subject_type text not null check" in sql
    assert "subject_id text not null" in sql
    assert "claims jsonb not null default '[]'::jsonb" in sql
    assert "unique (subject_type, subject_id)" in sql
    assert "project_id text" in sql
    assert "references research_projects(project_id)" in sql
    assert "research_papers_project_id_idx" in sql
    assert "research_session_projects_session_id_idx" in sql
    assert "research_session_projects_project_id_idx" in sql
    assert "name text primary key" in sql
    assert "system_prompt text not null" in sql
    assert "skill_refs jsonb not null default '[]'::jsonb" in sql
    assert "allowed_tools jsonb not null default '[]'::jsonb" in sql
    assert "input_boundaries jsonb not null default '{}'::jsonb" in sql
    assert "output_boundary text not null check" in sql
    assert "can_answer_user boolean not null default false" in sql
    assert "can_write_artifacts boolean not null default false" in sql
    assert "validation_status text not null check" in sql
    assert "task_id text primary key" in sql
    assert "parent_workflow_id text not null" in sql
    assert "agent_name text not null" in sql
    assert "agent_role text not null" in sql
    assert "citation_evidence boolean not null default false check (citation_evidence = false)" in sql
    assert "evidence_refs jsonb not null default '[]'::jsonb" in sql
    assert "research_subagent_runs_parent_workflow_idx" in sql
