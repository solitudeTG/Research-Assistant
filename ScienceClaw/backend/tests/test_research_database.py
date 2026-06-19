import sys
import types

import pytest

from backend.research_assistant.storage.database import (
    get_research_session_status_from_database,
    hybrid_search_evidence_in_database,
    persist_chunk_embeddings_to_database,
    persist_report_evidence_map_to_database,
)


class FakeConnection:
    def __init__(self):
        self.closed = False
        self.executemany_calls = []

    async def fetch(self, sql, *args):
        return [
            {
                "evidence_id": 3,
                "chunk_id": "chunk-3",
                "paper_id": "paper-3",
                "title": "Paper",
                "section": "Results",
                "page_start": None,
                "page_end": None,
                "quote": "Only paper evidence is returned.",
                "rank_score": 0.5,
            }
        ]

    async def fetchrow(self, sql, *args):
        return {"paper_count": 2, "chunk_count": 7}

    async def close(self):
        self.closed = True

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
