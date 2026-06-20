from pathlib import Path

import pytest

from backend.research_assistant.audit import EvidenceAudit, EvidenceAuditClaim
from backend.research_assistant.ingestion import ingest_uploaded_paper
from backend.research_assistant.storage import repository
from backend.research_assistant.storage.repository import (
    persist_chunk_embeddings,
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

    def transaction(self):
        return RecordingTransaction()

    async def execute(self, sql, *args):
        self.executed.append((sql, args))

    async def executemany(self, sql, rows):
        self.executemany_calls.append((sql, rows))


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
