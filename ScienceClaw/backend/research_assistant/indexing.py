from __future__ import annotations

from dataclasses import dataclass

from backend.research_assistant.embeddings import HashingEmbeddingProvider, build_chunk_embeddings
from backend.research_assistant.models import IngestionResult
from backend.research_assistant.storage.database import (
    persist_chunk_embeddings_to_database,
    persist_ingestion_result_to_database,
)


@dataclass(frozen=True)
class IndexingSummary:
    paper_id: str
    chunk_count: int
    evidence_record_count: int
    embedding_count: int
    embedding_model: str


async def index_ingestion_result(
    *,
    database_url: str,
    result: IngestionResult,
    embedding_dimensions: int,
    embedding_model: str = "local-hashing-v1",
) -> IndexingSummary:
    persist_summary = await persist_ingestion_result_to_database(database_url, result)
    provider = HashingEmbeddingProvider(dimensions=embedding_dimensions, model_name=embedding_model)
    embeddings = build_chunk_embeddings(result, provider)
    await persist_chunk_embeddings_to_database(
        database_url,
        embeddings=embeddings,
        embedding_model=provider.model_name,
    )
    return IndexingSummary(
        paper_id=persist_summary.paper_id,
        chunk_count=persist_summary.chunk_count,
        evidence_record_count=persist_summary.evidence_record_count,
        embedding_count=len(embeddings),
        embedding_model=provider.model_name,
    )
