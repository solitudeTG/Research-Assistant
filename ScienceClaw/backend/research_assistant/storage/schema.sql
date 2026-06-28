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
