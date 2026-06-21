from pathlib import Path

import pytest

from backend.research_assistant.audit import EvidenceAudit, EvidenceAuditClaim
from backend.research_assistant.ingestion import ingest_uploaded_paper
from backend.research_assistant.storage import repository
from backend.research_assistant.storage.repository import (
    persist_chunk_embeddings,
    persist_database_evidence_source,
    persist_web_evidence_source,
    persist_ingestion_result,
    persist_report_evidence_map,
)


class RecordingTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class RecordingConnection:
    def __init__(self):
        self.executed = []
        self.executemany_calls = []
        self.fetchrow_calls = []
        self.fetchrow_result = None
        self.fetch_calls = []
        self.fetch_result = []

    def transaction(self):
        return RecordingTransaction()

    async def execute(self, sql, *args):
        self.executed.append((sql, args))

    async def executemany(self, sql, rows):
        self.executemany_calls.append((sql, rows))

    async def fetchrow(self, sql, *args):
        self.fetchrow_calls.append((sql, args))
        return self.fetchrow_result

    async def fetch(self, sql, *args):
        self.fetch_calls.append((sql, args))
        return self.fetch_result


@pytest.mark.asyncio
async def test_persist_ingestion_result_writes_paper_chunks_and_evidence(tmp_path: Path):
    paper_path = tmp_path / "sample.md"
    paper_path.write_text(
        "\n".join(
            [
                "Title: Hybrid Retrieval for Papers",
                "Authors: Ada Lovelace",
                "Abstract: Hybrid retrieval keeps lexical and semantic evidence.",
                "",
                "1 Introduction",
                "PostgreSQL full-text search helps citation recall.",
                "",
                "2 Method",
                "pgvector stores semantic evidence candidates.",
            ]
        ),
        encoding="utf-8",
    )
    ingestion = ingest_uploaded_paper(
        file_path=paper_path,
        session_id="session-1",
        user_id="user-1",
        workspace_dir=tmp_path,
    )
    connection = RecordingConnection()

    summary = await persist_ingestion_result(connection, ingestion)

    assert summary.paper_id == ingestion.paper.paper_id
    assert summary.chunk_count == len(ingestion.chunks)
    assert summary.evidence_record_count == len(ingestion.chunks)
    assert any("insert into research_papers" in sql.lower() for sql, _ in connection.executed)
    assert any("insert into research_chunks" in sql.lower() for sql, _ in connection.executemany_calls)
    assert any("insert into research_evidence_records" in sql.lower() for sql, _ in connection.executemany_calls)
    evidence_sql = next(
        sql.lower()
        for sql, _ in connection.executemany_calls
        if "insert into research_evidence_records" in sql.lower()
    )
    assert "on conflict" in evidence_sql


@pytest.mark.asyncio
async def test_persist_web_evidence_source_writes_source_chunks_and_web_evidence():
    connection = RecordingConnection()

    summary = await persist_web_evidence_source(
        connection,
        session_id="session-1",
        user_id="user-1",
        source_id="web-source-1",
        url="https://example.org/evidence-boundaries",
        title="Evidence Boundaries on the Web",
        retrieved_at="2026-06-21T00:00:00Z",
        chunks=[
            {
                "chunk_id": "web-source-1:chunk-1",
                "section": "Main",
                "content": "Web evidence must preserve source identity.",
                "quote": "Web evidence must preserve source identity.",
            }
        ],
    )

    assert summary.paper_id == "web-source-1"
    assert summary.chunk_count == 1
    assert summary.evidence_record_count == 1
    assert any("insert into research_papers" in sql.lower() for sql, _ in connection.executed)
    paper_sql, paper_args = connection.executed[0]
    assert "parser" in paper_sql.lower()
    assert paper_args[0:8] == (
        "web-source-1",
        "session-1",
        "user-1",
        "Evidence Boundaries on the Web",
        "[]",
        "",
        "https://example.org/evidence-boundaries",
        "web-source",
    )
    assert '"source_type":"web"' in paper_args[8]
    chunk_sql, chunk_rows = connection.executemany_calls[0]
    assert "insert into research_chunks" in chunk_sql.lower()
    assert chunk_rows[0][0:7] == (
        "web-source-1:chunk-1",
        "web-source-1",
        "Main",
        None,
        None,
        1,
        "Web evidence must preserve source identity.",
    )
    assert '"url":"https://example.org/evidence-boundaries"' in chunk_rows[0][7]
    evidence_sql, evidence_rows = connection.executemany_calls[1]
    assert "insert into research_evidence_records" in evidence_sql.lower()
    assert "'web'" in evidence_sql.lower()
    assert evidence_rows[0][0:5] == (
        "web-source-1:chunk-1",
        "Web evidence must preserve source identity.",
        "Main",
        None,
        None,
    )


@pytest.mark.asyncio
async def test_persist_database_evidence_source_writes_source_chunks_and_database_evidence():
    connection = RecordingConnection()

    summary = await persist_database_evidence_source(
        connection,
        session_id="session-1",
        user_id="user-1",
        source_id="database-source-1",
        database_name="OpenAlex",
        query="topic:evidence-boundaries",
        title="OpenAlex Evidence Boundary Results",
        retrieved_at="2026-06-21T00:00:00Z",
        chunks=[
            {
                "chunk_id": "database-source-1:chunk-1",
                "section": "Result row",
                "content": "Database evidence must preserve query identity.",
                "quote": "Database evidence must preserve query identity.",
            }
        ],
    )

    assert summary.paper_id == "database-source-1"
    assert summary.chunk_count == 1
    assert summary.evidence_record_count == 1
    paper_sql, paper_args = connection.executed[0]
    assert "insert into research_papers" in paper_sql.lower()
    assert paper_args[0:8] == (
        "database-source-1",
        "session-1",
        "user-1",
        "OpenAlex Evidence Boundary Results",
        "[]",
        "",
        "database:OpenAlex",
        "database-source",
    )
    assert '"source_type":"database"' in paper_args[8]
    assert '"database_name":"OpenAlex"' in paper_args[8]
    assert '"query":"topic:evidence-boundaries"' in paper_args[8]
    chunk_sql, chunk_rows = connection.executemany_calls[0]
    assert "insert into research_chunks" in chunk_sql.lower()
    assert chunk_rows[0][0:7] == (
        "database-source-1:chunk-1",
        "database-source-1",
        "Result row",
        None,
        None,
        1,
        "Database evidence must preserve query identity.",
    )
    evidence_sql, evidence_rows = connection.executemany_calls[1]
    assert "insert into research_evidence_records" in evidence_sql.lower()
    assert "'database'" in evidence_sql.lower()
    assert evidence_rows[0][0:5] == (
        "database-source-1:chunk-1",
        "Database evidence must preserve query identity.",
        "Result row",
        None,
        None,
    )


@pytest.mark.asyncio
async def test_persist_chunk_embeddings_writes_pgvector_rows():
    connection = RecordingConnection()

    await persist_chunk_embeddings(
        connection,
        embeddings=[
            ("chunk-1", [0.1, 0.2, 0.3]),
            ("chunk-2", [0.4, 0.5, 0.6]),
        ],
        embedding_model="test-embedding",
    )

    sql, rows = connection.executemany_calls[0]
    assert "insert into research_embeddings" in sql.lower()
    assert "on conflict" in sql.lower()
    assert rows == [
        ("chunk-1", "test-embedding", "[0.1,0.2,0.3]"),
        ("chunk-2", "test-embedding", "[0.4,0.5,0.6]"),
    ]


@pytest.mark.asyncio
async def test_persist_report_evidence_map_upserts_rows():
    connection = RecordingConnection()

    await persist_report_evidence_map(
        connection,
        report_id="report-1",
        evidence_rows=[(3, "evidence-1", "Claim text")],
    )

    sql, rows = connection.executemany_calls[0]
    assert "insert into research_report_evidence_map" in sql.lower()
    assert "on conflict" in sql.lower()
    assert rows == [("report-1", 3, "evidence-1", "Claim text")]


@pytest.mark.asyncio
async def test_persist_audit_result_upserts_claim_boundaries():
    connection = RecordingConnection()
    audit = EvidenceAudit(
        status="approved",
        claims=[
            EvidenceAuditClaim(
                claim_text="Hybrid retrieval improves recall.",
                status="approved",
                evidence_ids=[17],
                notes=[],
            )
        ],
        boundaries={
            "citation_evidence": ["paper"],
            "context_only": ["memory", "model_reasoning", "process_trace", "tool_logs"],
        },
    )

    await repository.persist_audit_result(
        connection,
        audit_id="audit-1",
        session_id="session-1",
        subject_type="report",
        subject_id="report-1",
        audit=audit,
    )

    sql, args = connection.executed[0]
    assert "insert into research_audit_results" in sql.lower()
    assert "on conflict (subject_type, subject_id)" in sql.lower()
    assert args[0:9] == (
        "audit-1",
        "session-1",
        "report",
        "report-1",
        "approved",
        1,
        1,
        0,
        0,
    )
    assert '"citation_evidence":["paper"]' in args[9]
    assert '"claim_text":"Hybrid retrieval improves recall."' in args[10]


@pytest.mark.asyncio
async def test_get_audit_result_reads_session_scoped_subject():
    connection = RecordingConnection()
    connection.fetchrow_result = {
        "audit_id": "report-1:audit",
        "session_id": "session-1",
        "subject_type": "report",
        "subject_id": "report-1",
        "status": "approved",
        "claim_count": 1,
        "approved_claim_count": 1,
        "unsupported_claim_count": 0,
        "invalid_source_count": 0,
        "boundaries": '{"citation_evidence":["paper"],"context_only":["memory"]}',
        "claims": '[{"claim_text":"Claim","status":"approved","evidence_ids":[17],"notes":[]}]',
    }

    result = await repository.get_audit_result(
        connection,
        session_id="session-1",
        subject_type="report",
        subject_id="report-1",
    )

    sql, args = connection.fetchrow_calls[0]
    assert "from research_audit_results" in sql.lower()
    assert "session_id = $1" in sql.lower()
    assert "subject_type = $2" in sql.lower()
    assert "subject_id = $3" in sql.lower()
    assert args == ("session-1", "report", "report-1")
    assert result is not None
    assert result.audit_id == "report-1:audit"
    assert result.claims[0]["evidence_ids"] == [17]
    assert result.to_dict()["boundaries"]["citation_evidence"] == ["paper"]


@pytest.mark.asyncio
async def test_get_audit_result_returns_none_when_missing():
    connection = RecordingConnection()

    result = await repository.get_audit_result(
        connection,
        session_id="session-1",
        subject_type="answer",
        subject_id="missing-answer",
    )

    assert result is None


@pytest.mark.asyncio
async def test_get_evidence_record_reads_session_scoped_paper_evidence():
    connection = RecordingConnection()
    connection.fetchrow_result = {
        "evidence_id": 17,
        "evidence_type": "paper",
        "chunk_id": "chunk-17",
        "paper_id": "paper-1",
        "title": "Evidence Boundaries",
        "section": "Method",
        "page_start": 2,
        "page_end": 3,
        "quote": "Citation evidence is bounded.",
        "chunk_content": "Citation evidence is bounded. Memory is context-only.",
        "source_identity": '{"paper_id":"paper-1","file_path":"paper.pdf","section":"Method","page":2}',
    }

    result = await repository.get_evidence_record(
        connection,
        session_id="session-1",
        evidence_id=17,
    )

    sql, args = connection.fetchrow_calls[0]
    assert "from research_evidence_records" in sql.lower()
    assert "join research_papers" in sql.lower()
    assert "p.session_id = $1" in sql.lower()
    assert "er.evidence_id = $2" in sql.lower()
    assert args == ("session-1", 17)
    assert result is not None
    assert result.evidence_id == 17
    assert result.evidence_type == "paper"
    assert result.paper_id == "paper-1"
    assert result.source_identity["file_path"] == "paper.pdf"
    assert result.to_dict()["chunk_content"].startswith("Citation evidence")


@pytest.mark.asyncio
async def test_get_evidence_record_returns_none_when_missing():
    connection = RecordingConnection()

    result = await repository.get_evidence_record(
        connection,
        session_id="session-1",
        evidence_id=999,
    )

    assert result is None


@pytest.mark.asyncio
async def test_persist_memory_entry_forces_context_only_memory_boundary():
    connection = RecordingConnection()

    await repository.persist_memory_entry(
        connection,
        memory_id="mem-1",
        session_id="session-1",
        user_id="user-1",
        layer="L2",
        title="Confirmed retrieval preference",
        content="Prefer hybrid retrieval for scholarly terminology.",
        source_subject_type="answer",
        source_subject_id="answer-1",
    )

    sql, args = connection.executed[0]
    assert "insert into research_memory_entries" in sql.lower()
    assert "source_type" in sql.lower()
    assert "context_only" in sql.lower()
    assert "on conflict (memory_id)" in sql.lower()
    assert args == (
        "mem-1",
        "session-1",
        "user-1",
        "l2",
        "Confirmed retrieval preference",
        "Prefer hybrid retrieval for scholarly terminology.",
        "answer",
        "answer-1",
    )


@pytest.mark.asyncio
async def test_list_memory_entries_returns_context_only_memory_contexts():
    connection = RecordingConnection()
    connection.fetch_result = [
        {
            "memory_id": "mem-1",
            "session_id": "session-1",
            "user_id": "user-1",
            "layer": "l2",
            "title": "Confirmed retrieval preference",
            "content": "Prefer hybrid retrieval for scholarly terminology.",
            "source_type": "memory",
            "context_only": True,
            "source_subject_type": "answer",
            "source_subject_id": "answer-1",
            "created_at": None,
        }
    ]

    memories = await repository.list_memory_entries(
        connection,
        session_id="session-1",
        layer="L2",
        limit=5,
    )

    sql, args = connection.fetch_calls[0]
    assert "from research_memory_entries" in sql.lower()
    assert "session_id = $1" in sql.lower()
    assert "user_id = $2" in sql.lower()
    assert "layer in ('l2', 'l3')" in sql.lower()
    assert "layer = $3" in sql.lower()
    assert "context_only = true" in sql.lower()
    assert args == ("session-1", None, "l2", 5)
    assert len(memories) == 1
    assert memories[0].source_type == "memory"
    assert memories[0].context_only is True
    assert memories[0].to_context_dict() == {
        "memory_id": "mem-1",
        "layer": "l2",
        "title": "Confirmed retrieval preference",
        "content": "Prefer hybrid retrieval for scholarly terminology.",
        "source_type": "memory",
        "context_only": True,
        "source_subject_type": "answer",
        "source_subject_id": "answer-1",
    }


@pytest.mark.asyncio
async def test_list_memory_entries_can_include_same_user_l2_l3_across_sessions():
    connection = RecordingConnection()
    connection.fetch_result = [
        {
            "memory_id": "mem-cross-session",
            "session_id": "session-2",
            "user_id": "user-1",
            "layer": "l2",
            "title": "Confirmed retrieval preference",
            "content": "Prefer hybrid retrieval for scholarly terminology.",
            "source_type": "memory",
            "context_only": True,
            "source_subject_type": "answer",
            "source_subject_id": "answer-1",
            "created_at": None,
        }
    ]

    memories = await repository.list_memory_entries(
        connection,
        session_id="session-1",
        user_id="user-1",
        layer="L2",
        limit=10,
    )

    sql, args = connection.fetch_calls[0]
    assert "user_id = $2" in sql.lower()
    assert "layer in ('l2', 'l3')" in sql.lower()
    assert args == ("session-1", "user-1", "l2", 10)
    assert memories[0].memory_id == "mem-cross-session"
    assert memories[0].session_id == "session-2"
    assert memories[0].user_id == "user-1"


@pytest.mark.asyncio
async def test_delete_memory_entry_deletes_session_scoped_context_only_memory():
    connection = RecordingConnection()

    async def execute(sql, *args):
        connection.executed.append((sql, args))
        return "DELETE 1"

    connection.execute = execute

    deleted = await repository.delete_memory_entry(
        connection,
        session_id="session-1",
        memory_id="mem-1",
    )

    sql, args = connection.executed[0]
    assert deleted is True
    assert "delete from research_memory_entries" in sql.lower()
    assert "session_id = $1" in sql.lower()
    assert "memory_id = $2" in sql.lower()
    assert "source_type = 'memory'" in sql.lower()
    assert "context_only = true" in sql.lower()
    assert args == ("session-1", "mem-1")


@pytest.mark.asyncio
async def test_delete_memory_entry_returns_false_when_no_row_deleted():
    connection = RecordingConnection()

    async def execute(sql, *args):
        connection.executed.append((sql, args))
        return "DELETE 0"

    connection.execute = execute

    deleted = await repository.delete_memory_entry(
        connection,
        session_id="session-1",
        memory_id="missing-memory",
    )

    assert deleted is False
