import pytest

from backend.research_assistant.answering import answer_research_question
from backend.research_assistant.retrieval import EvidenceHit


@pytest.mark.asyncio
async def test_answer_research_question_uses_only_citation_evidence(monkeypatch):
    async def fake_search(database_url, *, session_id, query_text, query_embedding, embedding_model, limit):
        assert database_url == "postgresql://test"
        assert session_id == "session-1"
        assert query_text == "How does hybrid retrieval work?"
        assert len(query_embedding) == 8
        assert embedding_model == "local-hashing-v1"
        assert limit == 3
        return [
            EvidenceHit(
                evidence_id=11,
                chunk_id="chunk-1",
                paper_id="paper-1",
                title="Hybrid Retrieval for Papers",
                section="Method",
                page_start=2,
                page_end=3,
                quote="Hybrid retrieval combines lexical matching with vector search.",
                rank_score=0.9,
            )
        ]

    monkeypatch.setattr(
        "backend.research_assistant.answering.hybrid_search_evidence_in_database",
        fake_search,
    )

    answer = await answer_research_question(
        database_url="postgresql://test",
        session_id="session-1",
        question="How does hybrid retrieval work?",
        embedding_dimensions=8,
        embedding_model="local-hashing-v1",
        limit=3,
    )

    assert "Hybrid retrieval combines lexical matching with vector search. [paper-1:Method:2-3]" in answer.content
    assert answer.citations[0].evidence_id == 11
    assert answer.citations[0].chunk_id == "chunk-1"
    assert answer.citations[0].quote.startswith("Hybrid retrieval")
    assert answer.citations[0].source_type == "paper"
    assert answer.citation_count == 1
    assert answer.audit.status == "approved"
    assert answer.to_dict()["audit"]["approved_claim_count"] == 1


@pytest.mark.asyncio
async def test_answer_research_question_refuses_when_no_paper_evidence(monkeypatch):
    async def fake_search(*args, **kwargs):
        return []

    monkeypatch.setattr(
        "backend.research_assistant.answering.hybrid_search_evidence_in_database",
        fake_search,
    )

    answer = await answer_research_question(
        database_url="postgresql://test",
        session_id="session-1",
        question="What did the paper conclude?",
        embedding_dimensions=8,
        embedding_model="local-hashing-v1",
        limit=3,
    )

    assert answer.citation_count == 0
    assert "No citation evidence" in answer.content
    assert answer.audit.status == "unsupported"
    assert answer.to_dict()["audit"]["unsupported_claim_count"] == 1
