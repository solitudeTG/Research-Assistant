CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS research_projects (
    project_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS research_projects_user_updated_idx
    ON research_projects (user_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS research_session_projects (
    session_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES research_projects(project_id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS research_session_projects_session_id_idx
    ON research_session_projects (session_id);

CREATE INDEX IF NOT EXISTS research_session_projects_project_id_idx
    ON research_session_projects (project_id);

CREATE TABLE IF NOT EXISTS research_papers (
    paper_id TEXT PRIMARY KEY,
    project_id TEXT REFERENCES research_projects(project_id) ON DELETE SET NULL,
    session_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    authors JSONB NOT NULL DEFAULT '[]'::jsonb,
    abstract TEXT NOT NULL DEFAULT '',
    source_path TEXT NOT NULL,
    parser TEXT NOT NULL,
    source_identity JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE research_papers
    ADD COLUMN IF NOT EXISTS project_id TEXT REFERENCES research_projects(project_id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS research_papers_project_id_idx
    ON research_papers (project_id);

CREATE TABLE IF NOT EXISTS research_chunks (
    chunk_id TEXT PRIMARY KEY,
    paper_id TEXT NOT NULL REFERENCES research_papers(paper_id) ON DELETE CASCADE,
    section TEXT NOT NULL,
    page_start INTEGER,
    page_end INTEGER,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    content_tsv tsvector GENERATED ALWAYS AS (
        to_tsvector('english', coalesce(section, '') || ' ' || coalesce(content, ''))
    ) STORED,
    source_identity JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS research_chunks_paper_id_idx
    ON research_chunks (paper_id);

CREATE INDEX IF NOT EXISTS research_chunks_content_tsv_idx
    ON research_chunks USING GIN (content_tsv);

CREATE TABLE IF NOT EXISTS research_embeddings (
    embedding_id BIGSERIAL PRIMARY KEY,
    chunk_id TEXT NOT NULL REFERENCES research_chunks(chunk_id) ON DELETE CASCADE,
    embedding_model TEXT NOT NULL,
    embedding vector(1536) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (chunk_id, embedding_model)
);

CREATE INDEX IF NOT EXISTS research_embeddings_vector_idx
    ON research_embeddings USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE TABLE IF NOT EXISTS research_evidence_records (
    evidence_id BIGSERIAL PRIMARY KEY,
    chunk_id TEXT NOT NULL REFERENCES research_chunks(chunk_id) ON DELETE CASCADE,
    evidence_type TEXT NOT NULL CHECK (evidence_type IN ('paper', 'database', 'web')),
    quote TEXT NOT NULL,
    section TEXT NOT NULL,
    page_start INTEGER,
    page_end INTEGER,
    source_identity JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (chunk_id, evidence_type, quote)
);

CREATE TABLE IF NOT EXISTS research_citations (
    citation_id BIGSERIAL PRIMARY KEY,
    evidence_id BIGINT NOT NULL REFERENCES research_evidence_records(evidence_id) ON DELETE CASCADE,
    answer_id TEXT NOT NULL,
    citation_label TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS research_citations_answer_id_idx
    ON research_citations (answer_id);

CREATE TABLE IF NOT EXISTS research_report_evidence_map (
    report_id TEXT NOT NULL,
    evidence_id BIGINT NOT NULL REFERENCES research_evidence_records(evidence_id) ON DELETE CASCADE,
    markdown_anchor TEXT NOT NULL,
    claim_text TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (report_id, evidence_id, markdown_anchor)
);

CREATE TABLE IF NOT EXISTS research_audit_results (
    audit_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    subject_type TEXT NOT NULL CHECK (subject_type IN ('answer', 'report')),
    subject_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('approved', 'partial', 'unsupported', 'invalid_source')),
    claim_count INTEGER NOT NULL,
    approved_claim_count INTEGER NOT NULL,
    unsupported_claim_count INTEGER NOT NULL,
    invalid_source_count INTEGER NOT NULL,
    boundaries JSONB NOT NULL DEFAULT '{}'::jsonb,
    claims JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (subject_type, subject_id)
);

CREATE INDEX IF NOT EXISTS research_audit_results_session_id_idx
    ON research_audit_results (session_id);

CREATE INDEX IF NOT EXISTS research_audit_results_status_idx
    ON research_audit_results (status);

CREATE TABLE IF NOT EXISTS research_memory_entries (
    memory_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    user_id TEXT NOT NULL DEFAULT '',
    layer TEXT NOT NULL CHECK (layer IN ('l1', 'l2', 'l3')),
    title TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL,
    source_type TEXT NOT NULL DEFAULT 'memory' CHECK (source_type = 'memory'),
    context_only BOOLEAN NOT NULL DEFAULT true CHECK (context_only = true),
    source_subject_type TEXT,
    source_subject_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE research_memory_entries
    ADD COLUMN IF NOT EXISTS user_id TEXT NOT NULL DEFAULT '';

CREATE INDEX IF NOT EXISTS research_memory_entries_session_layer_created_idx
    ON research_memory_entries (session_id, layer, created_at DESC);

CREATE INDEX IF NOT EXISTS research_memory_entries_user_layer_created_idx
    ON research_memory_entries (user_id, layer, created_at DESC);

CREATE TABLE IF NOT EXISTS research_subagent_definitions (
    name TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    agent_type TEXT NOT NULL DEFAULT 'custom' CHECK (agent_type IN ('system_builtin', 'custom')),
    source TEXT NOT NULL DEFAULT 'registry',
    editable BOOLEAN NOT NULL DEFAULT true,
    description TEXT NOT NULL,
    system_prompt TEXT NOT NULL,
    skill_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
    allowed_tools JSONB NOT NULL DEFAULT '[]'::jsonb,
    input_boundaries JSONB NOT NULL DEFAULT '{}'::jsonb,
    output_boundary TEXT NOT NULL CHECK (output_boundary IN ('context_only', 'process_trace', 'artifact')),
    can_answer_user BOOLEAN NOT NULL DEFAULT false,
    can_write_artifacts BOOLEAN NOT NULL DEFAULT false,
    enabled BOOLEAN NOT NULL DEFAULT true,
    version INTEGER NOT NULL DEFAULT 1,
    validation_status TEXT NOT NULL CHECK (validation_status IN ('passed', 'failed', 'draft', 'disabled', 'system_managed')),
    citation_evidence BOOLEAN NOT NULL DEFAULT false CHECK (citation_evidence = false),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE research_subagent_definitions
    ADD COLUMN IF NOT EXISTS agent_type TEXT NOT NULL DEFAULT 'custom';
ALTER TABLE research_subagent_definitions
    ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'registry';
ALTER TABLE research_subagent_definitions
    ADD COLUMN IF NOT EXISTS editable BOOLEAN NOT NULL DEFAULT true;
ALTER TABLE research_subagent_definitions
    ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb;

DO $$
DECLARE
    constraint_name text;
BEGIN
    SELECT conname INTO constraint_name
    FROM pg_constraint
    WHERE conrelid = 'research_subagent_definitions'::regclass
      AND contype = 'c'
      AND pg_get_constraintdef(oid) LIKE '%validation_status%';

    IF constraint_name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE research_subagent_definitions DROP CONSTRAINT %I', constraint_name);
    END IF;

END $$;

UPDATE research_subagent_definitions
SET validation_status = CASE validation_status
    WHEN 'valid' THEN 'passed'
    WHEN 'invalid' THEN 'failed'
    ELSE validation_status
END
WHERE validation_status IN ('valid', 'invalid');

UPDATE research_subagent_definitions
SET enabled = false,
    metadata = metadata || jsonb_build_object(
        'auto_disabled_reason',
        'custom_agent_requires_passed_validation'
    )
WHERE agent_type = 'custom'
  AND enabled IS TRUE
  AND validation_status <> 'passed';

ALTER TABLE research_subagent_definitions
    ADD CONSTRAINT research_subagent_definitions_validation_status_check
    CHECK (validation_status IN ('passed', 'failed', 'draft', 'disabled', 'system_managed'));

CREATE INDEX IF NOT EXISTS research_subagent_definitions_enabled_idx
    ON research_subagent_definitions (enabled, name);

CREATE TABLE IF NOT EXISTS research_subagent_runs (
    task_id TEXT PRIMARY KEY,
    parent_workflow_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    agent_role TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    input_boundary JSONB NOT NULL DEFAULT '{}'::jsonb,
    output_boundary TEXT NOT NULL CHECK (output_boundary IN ('context_only', 'process_trace', 'artifact')),
    citation_evidence BOOLEAN NOT NULL DEFAULT false CHECK (citation_evidence = false),
    evidence_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
    outputs JSONB NOT NULL DEFAULT '{}'::jsonb,
    warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
    errors JSONB NOT NULL DEFAULT '[]'::jsonb,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS research_subagent_runs_parent_workflow_idx
    ON research_subagent_runs (parent_workflow_id, started_at DESC);

CREATE INDEX IF NOT EXISTS research_subagent_runs_agent_status_idx
    ON research_subagent_runs (agent_name, status);
