from pathlib import Path

from backend.research_assistant.embeddings import (
    HashingEmbeddingProvider,
    build_chunk_embeddings,
)
from backend.research_assistant.ingestion import ingest_uploaded_paper


def test_hashing_embedding_provider_is_deterministic_and_normalized():
    provider = HashingEmbeddingProvider(dimensions=16)

    first = provider.embed_text("hybrid retrieval evidence")
    second = provider.embed_text("hybrid retrieval evidence")

    assert first == second
    assert len(first) == 16
    assert any(value != 0 for value in first)
    assert max(abs(value) for value in first) <= 1.0


def test_build_chunk_embeddings_keeps_chunk_identity(tmp_path: Path):
    paper = tmp_path / "paper.md"
    paper.write_text(
        "\n".join(
            [
                "Title: Evidence Search",
                "",
                "1 Method",
                "Hybrid retrieval needs vectors and full-text evidence.",
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
    provider = HashingEmbeddingProvider(dimensions=8)

    embeddings = build_chunk_embeddings(ingestion, provider)

    assert embeddings
    assert embeddings[0][0] == ingestion.chunks[0].chunk_id
    assert len(embeddings[0][1]) == 8
