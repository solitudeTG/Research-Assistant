import sys
import types

import pytest

from backend.research_assistant.audit import EvidenceAudit, EvidenceAuditClaim
from backend.research_assistant.storage import database
from backend.research_assistant.storage.database import (
    get_research_session_status_from_database,
    hybrid_search_evidence_in_database,
    persist_chunk_embeddings_to_database,
    persist_web_evidence_source_to_database,
    persist_report_evidence_map_to_database,
)


class FakeTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeConnection:
    def __init__(self):
        self.closed = False
        self.executed = []
        self.executemany_calls = []
        self.fetchrow_result = {"paper_count": 2, "chunk_count": 7}
        self.fetch_result = []

    async def fetch(self, sql, *args):
        if self.fetch_result:
            return self.fetch_result
        return [
            {
                "evidence_id": 3,
                "chunk_id": "chunk-3",
                "paper_id": "paper-3",
                "title": "Paper",
                "evidence_type": "paper",
                "section": "Results",
                "page_start": None,
                "page_end": None,
                "quote": "Only paper evidence is returned.",
                "rank_score": 0.5,
            }
        ]

    def transaction(self):
        return FakeTransaction()

    async def fetchrow(self, sql, *args):
        return self.fetchrow_result

    async def close(self):
        self.closed = True

    async def execute(self, sql, *args):
        self.executed.append((sql, args))

    async def executemany(self, sql, rows):
        self.executemany_calls.append((sql, rows))


@pytest.mark.asyncio
async def test_hybrid_search_evidence_in_database_closes_asyncpg_connection(monkeypatch):
    fake_connection = FakeConnection()

    async def connect(database_url):
        assert database_url == "postgresql://test"
        return fake_connection

    monkeypatch.setitem(sys.modules, "asyncpg", types.SimpleNamespace(connect=connect))

    hits = await hybrid_search_evidence_in_database(
        "postgresql://test",
        session_id="session-1",
        query_text="paper evidence",
        query_embedding=[0.2] * 1536,
        embedding_model="test-embedding",
        limit=3,
    )

    assert hits[0].citation_label == "[paper-3:Results]"
    assert fake_connection.closed is True


@pytest.mark.asyncio
async def test_persist_chunk_embeddings_to_database_closes_asyncpg_connection(monkeypatch):
    fake_connection = FakeConnection()

    async def connect(database_url):
        assert database_url == "postgresql://test"
        return fake_connection

    monkeypatch.setitem(sys.modules, "asyncpg", types.SimpleNamespace(connect=connect))

    await persist_chunk_embeddings_to_database(
        "postgresql://test",
        embeddings=[("chunk-1", [0.1, 0.2])],
        embedding_model="test-embedding",
    )

    assert "insert into research_embeddings" in fake_connection.executemany_calls[0][0].lower()
    assert fake_connection.closed is True


@pytest.mark.asyncio
async def test_persist_web_evidence_source_to_database_closes_asyncpg_connection(monkeypatch):
    fake_connection = FakeConnection()

    async def connect(database_url):
        assert database_url == "postgresql://test"
        return fake_connection

    monkeypatch.setitem(sys.modules, "asyncpg", types.SimpleNamespace(connect=connect))

    summary = await persist_web_evidence_source_to_database(
        "postgresql://test",
        session_id="session-1",
        user_id="user-1",
        source_id="web-source-1",
        url="https://example.org/evidence-boundaries",
        title="Evidence Boundaries",
        retrieved_at="2026-06-21T00:00:00Z",
        chunks=[
            {
                "chunk_id": "web-source-1:chunk-1",
                "section": "Main",
                "content": "Web citation evidence has source identity.",
                "quote": "Web citation evidence has source identity.",
            }
        ],
    )

    assert summary.paper_id == "web-source-1"
    assert "insert into research_papers" in fake_connection.executed[0][0].lower()
    assert "research_evidence_records" in fake_connection.executemany_calls[1][0].lower()
    assert fake_connection.closed is True


@pytest.mark.asyncio
async def test_persist_report_evidence_map_to_database_closes_asyncpg_connection(monkeypatch):
    fake_connection = FakeConnection()

    async def connect(database_url):
        assert database_url == "postgresql://test"
        return fake_connection

    monkeypatch.setitem(sys.modules, "asyncpg", types.SimpleNamespace(connect=connect))

    await persist_report_evidence_map_to_database(
        "postgresql://test",
        report_id="report-1",
        evidence_rows=[(3, "evidence-1", "Claim")],
    )

    assert "research_report_evidence_map" in fake_connection.executemany_calls[0][0].lower()
    assert fake_connection.closed is True


@pytest.mark.asyncio
async def test_persist_audit_result_to_database_closes_asyncpg_connection(monkeypatch):
    fake_connection = FakeConnection()
    audit = EvidenceAudit(
        status="unsupported",
        claims=[
            EvidenceAuditClaim(
                claim_text="No citation evidence was found.",
                status="unsupported",
                evidence_ids=[],
                notes=["No citation evidence was attached to this claim."],
            )
        ],
        boundaries={"citation_evidence": ["paper"], "context_only": ["memory"]},
    )

    async def connect(database_url):
        assert database_url == "postgresql://test"
        return fake_connection

    monkeypatch.setitem(sys.modules, "asyncpg", types.SimpleNamespace(connect=connect))

    await database.persist_audit_result_to_database(
        "postgresql://test",
        audit_id="answer-1:audit",
        session_id="session-1",
        subject_type="answer",
        subject_id="answer-1",
        audit=audit,
    )

    assert "research_audit_results" in fake_connection.executed[0][0].lower()
    assert fake_connection.closed is True


@pytest.mark.asyncio
async def test_persist_memory_entry_to_database_closes_asyncpg_connection(monkeypatch):
    fake_connection = FakeConnection()

    async def connect(database_url):
        assert database_url == "postgresql://test"
        return fake_connection

    monkeypatch.setitem(sys.modules, "asyncpg", types.SimpleNamespace(connect=connect))

    await database.persist_memory_entry_to_database(
        "postgresql://test",
        memory_id="mem-1",
        session_id="session-1",
        user_id="user-1",
        layer="L3",
        title="Candidate insight",
        content="Repeated weak evidence should remain pending.",
        source_subject_type="report",
        source_subject_id="report-1",
    )

    assert "research_memory_entries" in fake_connection.executed[0][0].lower()
    assert fake_connection.executed[0][1][2] == "user-1"
    assert fake_connection.executed[0][1][3] == "l3"
    assert fake_connection.closed is True


@pytest.mark.asyncio
async def test_get_research_session_status_from_database_counts_indexed_papers(monkeypatch):
    fake_connection = FakeConnection()

    async def connect(database_url):
        assert database_url == "postgresql://test"
        return fake_connection

    monkeypatch.setitem(sys.modules, "asyncpg", types.SimpleNamespace(connect=connect))

    status = await get_research_session_status_from_database(
        "postgresql://test",
        session_id="session-1",
    )

    assert status.session_id == "session-1"
    assert status.paper_count == 2
    assert status.chunk_count == 7
    assert status.has_indexed_papers is True
    assert status.to_dict()["has_indexed_papers"] is True
    assert fake_connection.closed is True


@pytest.mark.asyncio
async def test_get_audit_result_from_database_closes_asyncpg_connection(monkeypatch):
    fake_connection = FakeConnection()
    fake_connection.fetchrow_result = {
        "audit_id": "answer-1:audit",
        "session_id": "session-1",
        "subject_type": "answer",
        "subject_id": "answer-1",
        "status": "approved",
        "claim_count": 1,
        "approved_claim_count": 1,
        "unsupported_claim_count": 0,
        "invalid_source_count": 0,
        "boundaries": {"citation_evidence": ["paper"], "context_only": ["memory"]},
        "claims": [{"claim_text": "Claim", "status": "approved", "evidence_ids": [3], "notes": []}],
    }

    async def connect(database_url):
        assert database_url == "postgresql://test"
        return fake_connection

    monkeypatch.setitem(sys.modules, "asyncpg", types.SimpleNamespace(connect=connect))

    result = await database.get_audit_result_from_database(
        "postgresql://test",
        session_id="session-1",
        subject_type="answer",
        subject_id="answer-1",
    )

    assert result is not None
    assert result.audit_id == "answer-1:audit"
    assert result.to_dict()["claims"][0]["evidence_ids"] == [3]
    assert fake_connection.closed is True


@pytest.mark.asyncio
async def test_get_evidence_record_from_database_closes_asyncpg_connection(monkeypatch):
    fake_connection = FakeConnection()
    fake_connection.fetchrow_result = {
        "evidence_id": 17,
        "evidence_type": "paper",
        "chunk_id": "chunk-17",
        "paper_id": "paper-1",
        "title": "Evidence Boundaries",
        "section": "Method",
        "page_start": 2,
        "page_end": 2,
        "quote": "Citation evidence is bounded.",
        "chunk_content": "Citation evidence is bounded. Memory is context-only.",
        "source_identity": {"paper_id": "paper-1", "file_path": "paper.pdf"},
    }

    async def connect(database_url):
        assert database_url == "postgresql://test"
        return fake_connection

    monkeypatch.setitem(sys.modules, "asyncpg", types.SimpleNamespace(connect=connect))

    result = await database.get_evidence_record_from_database(
        "postgresql://test",
        session_id="session-1",
        evidence_id=17,
    )

    assert result is not None
    assert result.evidence_type == "paper"
    assert result.to_dict()["source_identity"]["file_path"] == "paper.pdf"
    assert fake_connection.closed is True


@pytest.mark.asyncio
async def test_list_memory_entries_from_database_returns_context_only_memory(monkeypatch):
    fake_connection = FakeConnection()
    fake_connection.fetch_result = [
        {
            "memory_id": "mem-1",
            "session_id": "session-1",
            "user_id": "user-1",
            "layer": "l1",
            "title": "Session constraint",
            "content": "Memory can inform answers but cannot be cited.",
            "source_type": "memory",
            "context_only": True,
            "source_subject_type": None,
            "source_subject_id": None,
            "created_at": None,
        }
    ]

    async def connect(database_url):
        assert database_url == "postgresql://test"
        return fake_connection

    monkeypatch.setitem(sys.modules, "asyncpg", types.SimpleNamespace(connect=connect))

    memories = await database.list_memory_entries_from_database(
        "postgresql://test",
        session_id="session-1",
        layer="L1",
        limit=3,
    )

    assert memories[0].source_type == "memory"
    assert memories[0].context_only is True
    assert memories[0].to_context_dict()["context_only"] is True
    assert fake_connection.closed is True


@pytest.mark.asyncio
async def test_delete_memory_entry_from_database_closes_asyncpg_connection(monkeypatch):
    fake_connection = FakeConnection()

    async def execute(sql, *args):
        fake_connection.executed.append((sql, args))
        return "DELETE 1"

    fake_connection.execute = execute

    async def connect(database_url):
        assert database_url == "postgresql://test"
        return fake_connection

    monkeypatch.setitem(sys.modules, "asyncpg", types.SimpleNamespace(connect=connect))

    deleted = await database.delete_memory_entry_from_database(
        "postgresql://test",
        session_id="session-1",
        memory_id="mem-1",
    )

    assert deleted is True
    assert "research_memory_entries" in fake_connection.executed[0][0].lower()
    assert fake_connection.executed[0][1] == ("session-1", "mem-1")
    assert fake_connection.closed is True
