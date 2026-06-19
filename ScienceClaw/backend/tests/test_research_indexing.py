from pathlib import Path

import pytest

from backend.research_assistant.indexing import index_ingestion_result
from backend.research_assistant.ingestion import ingest_uploaded_paper


@pytest.mark.asyncio
async def test_index_ingestion_result_persists_embeddings_with_metadata(monkeypatch, tmp_path: Path):
    paper = tmp_path / "paper.md"
    paper.write_text(
        "\n".join(
            [
                "Title: Indexed Evidence",
                "",
                "1 Results",
                "The system indexes paper evidence for hybrid retrieval.",
            ]
        ),
        encoding="utf-8",
    )
    ingestion = ingest_uploaded_paper(
        file_path=paper,
        session_id="session-1",
        user_id="user-1",
        workspace_dir=tmp_path,
    )
    calls = {}

    async def persist_ingestion(database_url, result):
        calls["database_url"] = database_url
        calls["paper_id"] = result.paper.paper_id

        class Summary:
            paper_id = result.paper.paper_id
            chunk_count = len(result.chunks)
            evidence_record_count = len(result.chunks)

        return Summary()

    async def persist_embeddings(database_url, *, embeddings, embedding_model):
        calls["embedding_database_url"] = database_url
        calls["embedding_model"] = embedding_model
        calls["embeddings"] = embeddings

    monkeypatch.setattr("backend.research_assistant.indexing.persist_ingestion_result_to_database", persist_ingestion)
    monkeypatch.setattr("backend.research_assistant.indexing.persist_chunk_embeddings_to_database", persist_embeddings)

    summary = await index_ingestion_result(
        database_url="postgresql://test",
        result=ingestion,
        embedding_dimensions=8,
        embedding_model="local-hashing-v1",
    )

    assert summary.paper_id == ingestion.paper.paper_id
    assert summary.chunk_count == len(ingestion.chunks)
    assert summary.evidence_record_count == len(ingestion.chunks)
    assert summary.embedding_count == len(ingestion.chunks)
    assert summary.embedding_model == "local-hashing-v1"
    assert calls["embedding_database_url"] == "postgresql://test"
    assert len(calls["embeddings"][0][1]) == 8
