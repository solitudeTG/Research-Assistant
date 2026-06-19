CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS research_papers (
    paper_id TEXT PRIMARY KEY,
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
