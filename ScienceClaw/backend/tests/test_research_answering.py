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
                source_type="paper",
                section="Method",
                page_start=2,
                page_end=3,
                quote="Hybrid retrieval combines lexical matching with vector search.",
                rank_score=0.9,
            )
        ]

    async def fake_list_memory(*args, **kwargs):
        return []

    monkeypatch.setattr(
        "backend.research_assistant.answering.hybrid_search_evidence_in_database",
        fake_search,
    )
    monkeypatch.setattr(
        "backend.research_assistant.answering.list_memory_entries_from_database",
        fake_list_memory,
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
    assert answer.answer_id.startswith("research-answer-")
    assert answer.to_dict()["answer_id"] == answer.answer_id
    assert answer.audit.status == "approved"
    assert answer.to_dict()["audit"]["approved_claim_count"] == 1


@pytest.mark.asyncio
async def test_answer_research_question_refuses_when_no_paper_evidence(monkeypatch):
    async def fake_search(*args, **kwargs):
        return []

    async def fake_list_memory(*args, **kwargs):
        return []

    monkeypatch.setattr(
        "backend.research_assistant.answering.hybrid_search_evidence_in_database",
        fake_search,
    )
    monkeypatch.setattr(
        "backend.research_assistant.answering.list_memory_entries_from_database",
        fake_list_memory,
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


@pytest.mark.asyncio
async def test_answer_research_question_returns_context_only_memory_separate_from_citations(monkeypatch):
    async def fake_search(*args, **kwargs):
        return [
            EvidenceHit(
                evidence_id=11,
                chunk_id="chunk-1",
                paper_id="paper-1",
                title="Hybrid Retrieval for Papers",
                source_type="paper",
                section="Method",
                page_start=2,
                page_end=2,
                quote="Hybrid retrieval combines lexical matching with vector search.",
                rank_score=0.9,
            )
        ]

    async def fake_list_memory(database_url, *, session_id, user_id=None, layer=None, limit=20):
        assert database_url == "postgresql://test"
        assert session_id == "session-1"
        assert user_id is None
        assert layer is None
        assert limit == 5

        class Memory:
            def __init__(
                self,
                *,
                memory_id,
                title,
                content,
                source_subject_id,
            ):
                self.memory_id = memory_id
                self.layer = "l2"
                self.title = title
                self.content = content
                self.source_type = "memory"
                self.context_only = True
                self.source_subject_type = "answer"
                self.source_subject_id = source_subject_id

            def to_context_dict(self):
                return {
                    "memory_id": self.memory_id,
                    "layer": self.layer,
                    "title": self.title,
                    "content": self.content,
                    "source_type": self.source_type,
                    "context_only": self.context_only,
                    "source_subject_type": self.source_subject_type,
                    "source_subject_id": self.source_subject_id,
                }

        return [
            Memory(
                memory_id="mem-unrelated",
                title="Report preference",
                content="Keep Markdown report sections compact.",
                source_subject_id="answer-2",
            ),
            Memory(
                memory_id="mem-relevant",
                title="Retrieval preference",
                content="Prefer hybrid retrieval for scholarly terminology.",
                source_subject_id="answer-1",
            ),
        ]

    monkeypatch.setattr(
        "backend.research_assistant.answering.hybrid_search_evidence_in_database",
        fake_search,
    )
    monkeypatch.setattr(
        "backend.research_assistant.answering.list_memory_entries_from_database",
        fake_list_memory,
    )

    answer = await answer_research_question(
        database_url="postgresql://test",
        session_id="session-1",
        question="How does hybrid retrieval work?",
        embedding_dimensions=8,
        embedding_model="local-hashing-v1",
        limit=3,
    )

    payload = answer.to_dict()
    assert answer.citation_count == 1
    assert payload["citation_count"] == 1
    assert payload["context_memory_count"] == 1
    assert payload["context_memory"][0]["memory_id"] == "mem-relevant"
    assert payload["context_memory"][0]["source_type"] == "memory"
    assert payload["context_memory"][0]["context_only"] is True
    assert 0 < payload["context_memory"][0]["relevance_score"] <= 1
    assert "matched question terms: hybrid, retrieval" in payload["context_memory"][0]["recall_reason"]
    assert "source answer answer-1" in payload["context_memory"][0]["recall_reason"]
    assert all(citation["source_type"] == "paper" for citation in payload["citations"])
    assert answer.audit.status == "approved"


@pytest.mark.asyncio
async def test_answer_research_question_marks_conflicting_context_memory(monkeypatch):
    async def fake_search(*args, **kwargs):
        return []

    async def fake_list_memory(*args, **kwargs):
        class Memory:
            def __init__(self, *, memory_id, content):
                self.memory_id = memory_id
                self.layer = "l2"
                self.title = "Hybrid retrieval preference"
                self.content = content
                self.source_type = "memory"
                self.context_only = True
                self.source_subject_type = "answer"
                self.source_subject_id = memory_id.replace("mem-", "answer-")

            def to_context_dict(self):
                return {
                    "memory_id": self.memory_id,
                    "layer": self.layer,
                    "title": self.title,
                    "content": self.content,
                    "source_type": self.source_type,
                    "context_only": self.context_only,
                    "source_subject_type": self.source_subject_type,
                    "source_subject_id": self.source_subject_id,
                }

        return [
            Memory(
                memory_id="mem-prefer",
                content="Prefer hybrid retrieval for literature review synthesis.",
            ),
            Memory(
                memory_id="mem-avoid",
                content="Do not prefer hybrid retrieval for literature review synthesis.",
            ),
        ]

    monkeypatch.setattr(
        "backend.research_assistant.answering.hybrid_search_evidence_in_database",
        fake_search,
    )
    monkeypatch.setattr(
        "backend.research_assistant.answering.list_memory_entries_from_database",
        fake_list_memory,
    )

    answer = await answer_research_question(
        database_url="postgresql://test",
        session_id="session-1",
        question="Should we prefer hybrid retrieval for literature review synthesis?",
        embedding_dimensions=8,
        embedding_model="local-hashing-v1",
        limit=3,
    )

    memories = {memory["memory_id"]: memory for memory in answer.to_dict()["context_memory"]}
    assert memories["mem-prefer"]["memory_status"] == "conflict"
    assert memories["mem-prefer"]["conflicts_with"] == ["mem-avoid"]
    assert memories["mem-avoid"]["memory_status"] == "conflict"
    assert memories["mem-avoid"]["conflicts_with"] == ["mem-prefer"]
    assert "conflicts with context-only memory" in memories["mem-prefer"]["recall_reason"]
    assert "conflicts with context-only memory" in memories["mem-avoid"]["recall_reason"]
    assert answer.citation_count == 0
    assert answer.audit.status == "unsupported"


@pytest.mark.asyncio
async def test_answer_research_question_preserves_web_citation_source_type(monkeypatch):
    async def fake_search(*args, **kwargs):
        return [
            EvidenceHit(
                evidence_id=21,
                chunk_id="web-source-1:chunk-1",
                paper_id="web-source-1",
                title="Evidence Boundaries",
                source_type="web",
                section="Main",
                page_start=None,
                page_end=None,
                quote="Web citation evidence needs a source URL.",
                rank_score=0.8,
            )
        ]

    async def fake_list_memory(*args, **kwargs):
        return []

    monkeypatch.setattr(
        "backend.research_assistant.answering.hybrid_search_evidence_in_database",
        fake_search,
    )
    monkeypatch.setattr(
        "backend.research_assistant.answering.list_memory_entries_from_database",
        fake_list_memory,
    )

    answer = await answer_research_question(
        database_url="postgresql://test",
        session_id="session-1",
        question="What does the web source say about citations?",
        embedding_dimensions=8,
        embedding_model="local-hashing-v1",
        limit=3,
    )

    assert answer.content.startswith("Based on citation evidence:")
    assert "uploaded paper evidence" not in answer.content
    assert answer.citations[0].source_type == "web"
    assert answer.to_dict()["citations"][0]["source_type"] == "web"
    assert answer.audit.status == "approved"


@pytest.mark.asyncio
async def test_answer_research_question_preserves_citation_source_identity(monkeypatch):
    async def fake_search(*args, **kwargs):
        return [
            EvidenceHit(
                evidence_id=21,
                chunk_id="web-source-1:chunk-1",
                paper_id="web-source-1",
                title="Evidence Boundaries",
                source_type="web",
                section="Main",
                page_start=None,
                page_end=None,
                quote="Web citation evidence needs a source URL.",
                rank_score=0.8,
                source_identity={
                    "url": "https://example.org/evidence-boundaries",
                    "retrieved_at": "2026-06-21T10:00:00Z",
                },
            )
        ]

    async def fake_list_memory(*args, **kwargs):
        return []

    monkeypatch.setattr(
        "backend.research_assistant.answering.hybrid_search_evidence_in_database",
        fake_search,
    )
    monkeypatch.setattr(
        "backend.research_assistant.answering.list_memory_entries_from_database",
        fake_list_memory,
    )

    answer = await answer_research_question(
        database_url="postgresql://test",
        session_id="session-1",
        question="What does the web source say about citations?",
        embedding_dimensions=8,
        embedding_model="local-hashing-v1",
        limit=3,
    )

    assert answer.citations[0].source_identity == {
        "url": "https://example.org/evidence-boundaries",
        "retrieved_at": "2026-06-21T10:00:00Z",
    }
    assert answer.to_dict()["citations"][0]["source_identity"]["url"] == "https://example.org/evidence-boundaries"


@pytest.mark.asyncio
async def test_answer_research_question_passes_user_id_to_memory_lookup(monkeypatch):
    async def fake_search(*args, **kwargs):
        return []

    memory_lookup = {}

    async def fake_list_memory(database_url, *, session_id, user_id=None, layer=None, limit=20):
        memory_lookup.update(
            {
                "database_url": database_url,
                "session_id": session_id,
                "user_id": user_id,
                "layer": layer,
                "limit": limit,
            }
        )
        return []

    monkeypatch.setattr(
        "backend.research_assistant.answering.hybrid_search_evidence_in_database",
        fake_search,
    )
    monkeypatch.setattr(
        "backend.research_assistant.answering.list_memory_entries_from_database",
        fake_list_memory,
    )

    await answer_research_question(
        database_url="postgresql://test",
        session_id="session-1",
        user_id="user-1",
        question="What should I remember?",
        embedding_dimensions=8,
        embedding_model="local-hashing-v1",
        limit=3,
    )

    assert memory_lookup == {
        "database_url": "postgresql://test",
        "session_id": "session-1",
        "user_id": "user-1",
        "layer": None,
        "limit": 5,
    }
