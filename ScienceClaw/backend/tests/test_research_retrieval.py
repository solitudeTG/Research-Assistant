import pytest

from backend.research_assistant.retrieval import hybrid_search_evidence


class FetchingConnection:
    def __init__(self):
        self.calls = []

    async def fetch(self, sql, *args):
        self.calls.append((sql, args))
        return [
            {
                "evidence_id": 7,
                "chunk_id": "chunk-1",
                "paper_id": "paper-1",
                "title": "Hybrid Retrieval for Papers",
                "evidence_type": "web",
                "section": "Method",
                "page_start": 3,
                "page_end": 4,
                "quote": "PostgreSQL full-text search and pgvector both contribute evidence.",
                "evidence_scope": "project",
                "rank_score": 0.91,
            }
        ]


@pytest.mark.asyncio
async def test_hybrid_search_evidence_returns_citable_paper_chunks():
    connection = FetchingConnection()

    hits = await hybrid_search_evidence(
        connection,
        session_id="session-1",
        query_text="hybrid retrieval evidence",
        query_embedding=[0.1] * 1536,
        embedding_model="test-embedding",
        limit=5,
    )

    assert len(hits) == 1
    assert hits[0].evidence_id == 7
    assert hits[0].paper_id == "paper-1"
    assert hits[0].section == "Method"
    assert hits[0].quote.startswith("PostgreSQL full-text search")
    assert hits[0].source_type == "web"
    assert hits[0].evidence_scope == "project"
    assert hits[0].citation_label == "[paper-1:Method:3-4]"

    sql, args = connection.calls[0]
    normalized_sql = sql.lower()
    assert "evidence_type in ('paper', 'database', 'web')" in normalized_sql
    assert "er.evidence_type = 'web'" in normalized_sql
    assert "er.source_identity->>'url'" in normalized_sql
    assert "er.evidence_type = 'database'" in normalized_sql
    assert "er.source_identity->>'database_name'" in normalized_sql
    assert "er.source_identity->>'query'" in normalized_sql
    assert "content_tsv @@ websearch_to_tsquery" in normalized_sql
    assert "embedding <=> $3::vector" in normalized_sql
    assert "research_evidence_records" in normalized_sql
    assert args[0] == "session-1"
    assert args[1] == "hybrid retrieval evidence"
    assert args[3] == "test-embedding"


@pytest.mark.asyncio
async def test_hybrid_search_evidence_can_scope_to_project():
    connection = FetchingConnection()

    await hybrid_search_evidence(
        connection,
        session_id="session-1",
        project_id="project-1",
        query_text="hybrid retrieval evidence",
        query_embedding=[0.1] * 1536,
        embedding_model="test-embedding",
        limit=5,
    )

    sql, args = connection.calls[0]
    normalized_sql = sql.lower()
    assert "p.session_id = $1" in normalized_sql
    assert "$6::text is not null and p.project_id = $6" in normalized_sql
    assert args[0] == "session-1"
    assert args[5] == "project-1"
