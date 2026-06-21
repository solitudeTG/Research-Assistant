import importlib
import hashlib
import json
import sys
import types
from pathlib import Path

import pytest

from backend.research_assistant.answering import ResearchAnswer, ResearchCitation


class FakeSession:
    def __init__(self, *, user_id="user-1", vm_root_dir=None):
        self.user_id = user_id
        self.events = []
        self.vm_root_dir = Path(vm_root_dir or ".")
        self.save_count = 0
        self.status = "pending"

    async def save(self):
        self.save_count += 1


class FakeUpload:
    filename = "paper.pdf"
    content_type = "application/pdf"

    async def read(self):
        return b"%PDF-1.4\nfake"


class FakeStorageSummary:
    def __init__(self, *, paper_id="web-source-1", chunk_count=1, evidence_record_count=1):
        self.paper_id = paper_id
        self.chunk_count = chunk_count
        self.evidence_record_count = evidence_record_count


def _load_sessions_module(monkeypatch):
    async def unused_async(*args, **kwargs):
        raise AssertionError("unexpected ScienceClaw session dependency call")

    monkeypatch.setitem(
        sys.modules,
        "backend.deepagent.engine",
        types.SimpleNamespace(get_llm_model=lambda *args, **kwargs: None),
    )
    monkeypatch.setitem(
        sys.modules,
        "backend.deepagent.runner",
        types.SimpleNamespace(arun_science_task_stream=unused_async),
    )
    monkeypatch.setitem(
        sys.modules,
        "backend.deepagent.sessions",
        types.SimpleNamespace(
            ScienceSessionNotFoundError=type("ScienceSessionNotFoundError", (Exception,), {}),
            async_create_science_session=unused_async,
            async_delete_science_session=unused_async,
            async_get_science_session=unused_async,
            async_list_science_sessions=unused_async,
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "backend.user.dependencies",
        types.SimpleNamespace(
            get_current_user=lambda: None,
            require_user=lambda: None,
            User=object,
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "backend.models",
        types.SimpleNamespace(get_model_config=lambda *args, **kwargs: None),
    )
    monkeypatch.setitem(
        sys.modules,
        "backend.mongodb.db",
        types.SimpleNamespace(db=types.SimpleNamespace(get_collection=lambda name: None)),
    )
    sys.modules.pop("backend.route.sessions", None)
    return importlib.import_module("backend.route.sessions")


@pytest.mark.asyncio
async def test_research_web_evidence_ingest_persists_source_and_trace(monkeypatch):
    sessions = _load_sessions_module(monkeypatch)
    session = FakeSession()
    persisted = {}
    published = []

    async def fake_get_session(session_id):
        assert session_id == "session-1"
        return session

    async def fake_persist_web_evidence_source(database_url, **kwargs):
        persisted["database_url"] = database_url
        persisted.update(kwargs)
        return FakeStorageSummary(
            paper_id=kwargs["source_id"],
            chunk_count=len(kwargs["chunks"]),
            evidence_record_count=len(kwargs["chunks"]),
        )

    monkeypatch.setattr(sessions, "async_get_science_session", fake_get_session)
    monkeypatch.setattr(sessions, "persist_web_evidence_source_to_database", fake_persist_web_evidence_source)
    monkeypatch.setattr(sessions, "_publish_session_event", lambda *args: published.append(args))

    response = await sessions.ingest_web_evidence_for_session(
        "session-1",
        sessions.WebEvidenceIngestRequest(
            url="https://example.com/research",
            title="External Research Note",
            retrieved_at="2026-06-21T00:00:00Z",
            chunks=[
                sessions.WebEvidenceChunkRequest(
                    section="Findings",
                    content="Only source-identified web evidence can be cited.",
                    quote="source-identified web evidence",
                )
            ],
        ),
        types.SimpleNamespace(id="user-1"),
    )

    assert response.data["source_type"] == "web"
    assert response.data["source_id"].startswith("web-")
    assert response.data["url"] == "https://example.com/research"
    assert response.data["title"] == "External Research Note"
    assert response.data["chunk_count"] == 1
    assert response.data["evidence_record_count"] == 1
    assert response.data["source_quality"] == {
        "status": "citation_grade",
        "source_type": "web",
        "identity_fields": ["url", "title", "retrieved_at"],
        "missing_fields": [],
    }

    assert persisted["database_url"] == sessions.settings.research_database_url
    assert persisted["session_id"] == "session-1"
    assert persisted["user_id"] == "user-1"
    assert persisted["source_id"] == response.data["source_id"]
    assert persisted["url"] == "https://example.com/research"
    assert persisted["title"] == "External Research Note"
    assert persisted["retrieved_at"] == "2026-06-21T00:00:00Z"
    assert persisted["chunks"] == [
        {
            "chunk_id": f"{response.data['source_id']}:chunk-1",
            "section": "Findings",
            "content": "Only source-identified web evidence can be cited.",
            "quote": "source-identified web evidence",
        }
    ]

    assert session.status == sessions.SessionStatus.COMPLETED
    completed_step = session.events[-1]["data"]
    assert completed_step["status"] == "completed"
    assert completed_step["id"].startswith("research-web-evidence-")
    assert completed_step["description"] == "Web citation evidence indexed"
    assert completed_step["metadata"] == {
        "source_type": "web",
        "source_id": response.data["source_id"],
        "url": "https://example.com/research",
        "title": "External Research Note",
        "chunk_count": 1,
        "evidence_record_count": 1,
        "source_quality": response.data["source_quality"],
    }
    assert published[-1] == ("session-1", "user-1", session.events[-1])


@pytest.mark.asyncio
async def test_research_web_evidence_ingest_failure_persists_failed_trace(monkeypatch):
    sessions = _load_sessions_module(monkeypatch)
    session = FakeSession()

    async def fake_get_session(session_id):
        assert session_id == "session-1"
        return session

    async def fail_persist_web_evidence_source(*args, **kwargs):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(sessions, "async_get_science_session", fake_get_session)
    monkeypatch.setattr(sessions, "persist_web_evidence_source_to_database", fail_persist_web_evidence_source)
    monkeypatch.setattr(sessions, "_publish_session_event", lambda *args, **kwargs: None)

    with pytest.raises(sessions.HTTPException) as excinfo:
        await sessions.ingest_web_evidence_for_session(
            "session-1",
            sessions.WebEvidenceIngestRequest(
                url="https://example.com/research",
                title="External Research Note",
                chunks=[
                    sessions.WebEvidenceChunkRequest(
                        section="Findings",
                        content="Only source-identified web evidence can be cited.",
                    )
                ],
            ),
            types.SimpleNamespace(id="user-1"),
        )

    assert excinfo.value.status_code == 500
    failed_steps = [
        event["data"]
        for event in session.events
        if event.get("event") == "step" and event.get("data", {}).get("status") == "failed"
    ]
    assert len(failed_steps) == 1
    assert failed_steps[0]["id"].startswith("research-web-evidence-")
    assert failed_steps[0]["description"] == "Web citation evidence indexing failed"
    assert failed_steps[0]["metadata"]["source_type"] == "web"
    assert failed_steps[0]["metadata"]["url"] == "https://example.com/research"
    assert failed_steps[0]["metadata"]["title"] == "External Research Note"
    assert failed_steps[0]["metadata"]["source_quality"] == {
        "status": "citation_grade",
        "source_type": "web",
        "identity_fields": ["url", "title", "retrieved_at"],
        "missing_fields": [],
    }
    assert "database unavailable" in failed_steps[0]["metadata"]["error"]
    assert session.save_count == 1


@pytest.mark.asyncio
async def test_research_database_evidence_ingest_persists_source_and_trace(monkeypatch):
    sessions = _load_sessions_module(monkeypatch)
    session = FakeSession()
    persisted = {}
    published = []

    async def fake_get_session(session_id):
        assert session_id == "session-1"
        return session

    async def fake_persist_database_evidence_source(database_url, **kwargs):
        persisted["database_url"] = database_url
        persisted.update(kwargs)
        return FakeStorageSummary(
            paper_id=kwargs["source_id"],
            chunk_count=len(kwargs["chunks"]),
            evidence_record_count=len(kwargs["chunks"]),
        )

    monkeypatch.setattr(sessions, "async_get_science_session", fake_get_session)
    monkeypatch.setattr(sessions, "persist_database_evidence_source_to_database", fake_persist_database_evidence_source)
    monkeypatch.setattr(sessions, "_publish_session_event", lambda *args: published.append(args))

    response = await sessions.ingest_database_evidence_for_session(
        "session-1",
        sessions.DatabaseEvidenceIngestRequest(
            database_name="OpenAlex",
            query="topic:evidence-boundaries",
            title="OpenAlex Evidence Boundary Results",
            retrieved_at="2026-06-21T00:00:00Z",
            chunks=[
                sessions.DatabaseEvidenceChunkRequest(
                    section="Result row",
                    content="Only source-identified database evidence can be cited.",
                    quote="source-identified database evidence",
                )
            ],
        ),
        types.SimpleNamespace(id="user-1"),
    )

    assert response.data["source_type"] == "database"
    assert response.data["source_id"].startswith("database-")
    assert response.data["database_name"] == "OpenAlex"
    assert response.data["query"] == "topic:evidence-boundaries"
    assert response.data["title"] == "OpenAlex Evidence Boundary Results"
    assert response.data["chunk_count"] == 1
    assert response.data["evidence_record_count"] == 1
    assert response.data["source_quality"] == {
        "status": "citation_grade",
        "source_type": "database",
        "identity_fields": ["database_name", "query", "title", "retrieved_at"],
        "missing_fields": [],
    }

    assert persisted["database_url"] == sessions.settings.research_database_url
    assert persisted["session_id"] == "session-1"
    assert persisted["user_id"] == "user-1"
    assert persisted["source_id"] == response.data["source_id"]
    assert persisted["database_name"] == "OpenAlex"
    assert persisted["query"] == "topic:evidence-boundaries"
    assert persisted["title"] == "OpenAlex Evidence Boundary Results"
    assert persisted["retrieved_at"] == "2026-06-21T00:00:00Z"
    assert persisted["chunks"] == [
        {
            "chunk_id": f"{response.data['source_id']}:chunk-1",
            "section": "Result row",
            "content": "Only source-identified database evidence can be cited.",
            "quote": "source-identified database evidence",
        }
    ]

    assert session.status == sessions.SessionStatus.COMPLETED
    completed_step = session.events[-1]["data"]
    assert completed_step["status"] == "completed"
    assert completed_step["id"].startswith("research-database-evidence-")
    assert completed_step["description"] == "Database citation evidence indexed"
    assert completed_step["metadata"] == {
        "source_type": "database",
        "source_id": response.data["source_id"],
        "database_name": "OpenAlex",
        "query": "topic:evidence-boundaries",
        "title": "OpenAlex Evidence Boundary Results",
        "chunk_count": 1,
        "evidence_record_count": 1,
        "source_quality": response.data["source_quality"],
    }
    assert published[-1] == ("session-1", "user-1", session.events[-1])


@pytest.mark.asyncio
async def test_research_database_evidence_ingest_failure_persists_failed_trace(monkeypatch):
    sessions = _load_sessions_module(monkeypatch)
    session = FakeSession()

    async def fake_get_session(session_id):
        assert session_id == "session-1"
        return session

    async def fail_persist_database_evidence_source(*args, **kwargs):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(sessions, "async_get_science_session", fake_get_session)
    monkeypatch.setattr(sessions, "persist_database_evidence_source_to_database", fail_persist_database_evidence_source)
    monkeypatch.setattr(sessions, "_publish_session_event", lambda *args, **kwargs: None)

    with pytest.raises(sessions.HTTPException) as excinfo:
        await sessions.ingest_database_evidence_for_session(
            "session-1",
            sessions.DatabaseEvidenceIngestRequest(
                database_name="OpenAlex",
                query="topic:evidence-boundaries",
                title="OpenAlex Evidence Boundary Results",
                chunks=[
                    sessions.DatabaseEvidenceChunkRequest(
                        section="Result row",
                        content="Only source-identified database evidence can be cited.",
                    )
                ],
            ),
            types.SimpleNamespace(id="user-1"),
        )

    assert excinfo.value.status_code == 500
    failed_steps = [
        event["data"]
        for event in session.events
        if event.get("event") == "step" and event.get("data", {}).get("status") == "failed"
    ]
    assert len(failed_steps) == 1
    assert failed_steps[0]["id"].startswith("research-database-evidence-")
    assert failed_steps[0]["description"] == "Database citation evidence indexing failed"
    assert failed_steps[0]["metadata"]["source_type"] == "database"
    assert failed_steps[0]["metadata"]["database_name"] == "OpenAlex"
    assert failed_steps[0]["metadata"]["title"] == "OpenAlex Evidence Boundary Results"
    assert failed_steps[0]["metadata"]["source_quality"] == {
        "status": "citation_grade",
        "source_type": "database",
        "identity_fields": ["database_name", "query", "title", "retrieved_at"],
        "missing_fields": [],
    }
    assert "database unavailable" in failed_steps[0]["metadata"]["error"]
    assert session.save_count == 1


@pytest.mark.asyncio
async def test_research_answer_failure_persists_failed_trace_step(monkeypatch):
    sessions = _load_sessions_module(monkeypatch)
    session = FakeSession()

    async def fake_get_session(session_id):
        assert session_id == "session-1"
        return session

    async def fail_answer(*args, **kwargs):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(sessions, "async_get_science_session", fake_get_session)
    monkeypatch.setattr(sessions, "answer_research_question", fail_answer)
    monkeypatch.setattr(sessions, "_publish_session_event", lambda *args, **kwargs: None)

    with pytest.raises(sessions.HTTPException) as excinfo:
        await sessions.answer_research_question_for_session(
            "session-1",
            sessions.ResearchAnswerRequest(question="What did the paper find?"),
            types.SimpleNamespace(id="user-1"),
        )

    assert excinfo.value.status_code == 500
    failed_steps = [
        event["data"]
        for event in session.events
        if event.get("event") == "step" and event.get("data", {}).get("status") == "failed"
    ]
    assert len(failed_steps) == 1
    assert failed_steps[0]["id"].startswith("research-answer-")
    assert failed_steps[0]["description"] == "Citation evidence retrieval failed"
    assert failed_steps[0]["metadata"]["question"] == "What did the paper find?"
    assert "database unavailable" in failed_steps[0]["metadata"]["error"]
    assert session.save_count == 1


@pytest.mark.asyncio
async def test_research_answer_persists_audit_result(monkeypatch):
    sessions = _load_sessions_module(monkeypatch)
    session = FakeSession()
    persisted_audit = {}

    async def fake_get_session(session_id):
        assert session_id == "session-1"
        return session

    async def fake_answer(*args, **kwargs):
        return ResearchAnswer(
            content="Based on uploaded paper evidence:\n1. Citation evidence is bounded. [paper-1:Method:2]",
            citations=[
                ResearchCitation(
                    evidence_id=31,
                    chunk_id="chunk-31",
                    paper_id="paper-1",
                    title="Evidence Boundaries",
                    section="Method",
                    page_start=2,
                    page_end=2,
                    quote="Citation evidence is bounded.",
                    citation_label="[paper-1:Method:2]",
                )
            ],
        )

    async def fake_persist_audit(database_url, *, audit_id, session_id, subject_type, subject_id, audit):
        persisted_audit["database_url"] = database_url
        persisted_audit["audit_id"] = audit_id
        persisted_audit["session_id"] = session_id
        persisted_audit["subject_type"] = subject_type
        persisted_audit["subject_id"] = subject_id
        persisted_audit["status"] = audit.status

    monkeypatch.setattr(sessions, "async_get_science_session", fake_get_session)
    monkeypatch.setattr(sessions, "answer_research_question", fake_answer)
    monkeypatch.setattr(sessions, "persist_audit_result_to_database", fake_persist_audit)
    monkeypatch.setattr(sessions, "_publish_session_event", lambda *args, **kwargs: None)

    response = await sessions.answer_research_question_for_session(
        "session-1",
        sessions.ResearchAnswerRequest(question="What does the paper say about evidence?"),
        types.SimpleNamespace(id="user-1"),
    )

    answer_id = response.data["answer_id"]
    assert answer_id.startswith("research-answer-")
    assert persisted_audit == {
        "database_url": sessions.settings.research_database_url,
        "audit_id": f"{answer_id}:audit",
        "session_id": "session-1",
        "subject_type": "answer",
        "subject_id": answer_id,
        "status": "approved",
    }
    assert session.events[-1]["data"]["metadata"]["research_assistant"]["answer_id"] == answer_id


@pytest.mark.asyncio
async def test_research_answer_trace_and_message_keep_memory_context_separate(monkeypatch):
    sessions = _load_sessions_module(monkeypatch)
    session = FakeSession()

    async def fake_get_session(session_id):
        assert session_id == "session-1"
        return session

    async def fake_answer(*args, **kwargs):
        return ResearchAnswer(
            content="Based on uploaded paper evidence:\n1. Citation evidence is bounded. [paper-1:Method:2]",
            citations=[
                ResearchCitation(
                    evidence_id=31,
                    chunk_id="chunk-31",
                    paper_id="paper-1",
                    title="Evidence Boundaries",
                    section="Method",
                    page_start=2,
                    page_end=2,
                    quote="Citation evidence is bounded.",
                    citation_label="[paper-1:Method:2]",
                )
            ],
            context_memory=[
                {
                    "memory_id": "mem-1",
                    "layer": "l2",
                    "title": "Evidence boundary rule",
                    "content": "Memory must stay context-only.",
                    "source_type": "memory",
                    "context_only": True,
                    "source_subject_type": "answer",
                    "source_subject_id": "answer-1",
                    "recall_reason": "Stored l2 research memory for this session.",
                }
            ],
        )

    async def fake_persist_audit(*args, **kwargs):
        return None

    monkeypatch.setattr(sessions, "async_get_science_session", fake_get_session)
    monkeypatch.setattr(sessions, "answer_research_question", fake_answer)
    monkeypatch.setattr(sessions, "persist_audit_result_to_database", fake_persist_audit)
    monkeypatch.setattr(sessions, "_publish_session_event", lambda *args, **kwargs: None)

    response = await sessions.answer_research_question_for_session(
        "session-1",
        sessions.ResearchAnswerRequest(question="What does the paper say about evidence?"),
        types.SimpleNamespace(id="user-1"),
    )

    assert response.data["citation_count"] == 1
    assert response.data["context_memory_count"] == 1
    assert response.data["context_memory"][0]["source_type"] == "memory"
    assert response.data["context_memory"][0]["context_only"] is True

    completed_steps = [
        event["data"]
        for event in session.events
        if event.get("event") == "step" and event.get("data", {}).get("status") == "completed"
    ]
    assert completed_steps[-1]["metadata"]["citation_count"] == 1
    assert completed_steps[-1]["metadata"]["context_memory_count"] == 1
    assistant_research = session.events[-1]["data"]["metadata"]["research_assistant"]
    assert assistant_research["citations"][0]["source_type"] == "paper"
    assert assistant_research["context_memory"][0]["source_type"] == "memory"


@pytest.mark.asyncio
async def test_research_answer_passes_user_id_for_cross_session_memory_recall(monkeypatch):
    sessions = _load_sessions_module(monkeypatch)
    session = FakeSession()
    answer_kwargs = {}

    async def fake_get_session(session_id):
        assert session_id == "session-1"
        return session

    async def fake_answer(*args, **kwargs):
        answer_kwargs.update(kwargs)
        return ResearchAnswer(
            content="No citation evidence was found for this question.",
            citations=[],
        )

    async def fake_persist_audit(*args, **kwargs):
        return None

    monkeypatch.setattr(sessions, "async_get_science_session", fake_get_session)
    monkeypatch.setattr(sessions, "answer_research_question", fake_answer)
    monkeypatch.setattr(sessions, "persist_audit_result_to_database", fake_persist_audit)
    monkeypatch.setattr(sessions, "_publish_session_event", lambda *args, **kwargs: None)

    await sessions.answer_research_question_for_session(
        "session-1",
        sessions.ResearchAnswerRequest(question="What should I remember?"),
        types.SimpleNamespace(id="user-1"),
    )

    assert answer_kwargs["session_id"] == "session-1"
    assert answer_kwargs["user_id"] == "user-1"


@pytest.mark.asyncio
async def test_get_research_audit_result_for_session_returns_persisted_audit(monkeypatch):
    sessions = _load_sessions_module(monkeypatch)
    session = FakeSession()

    async def fake_get_session(session_id):
        assert session_id == "session-1"
        return session

    audit_result = types.SimpleNamespace(
        to_dict=lambda: {
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
            "claims": [{"claim_text": "Claim", "status": "approved", "evidence_ids": [31], "notes": []}],
        }
    )

    async def fake_get_audit(database_url, *, session_id, subject_type, subject_id):
        assert database_url == sessions.settings.research_database_url
        assert session_id == "session-1"
        assert subject_type == "answer"
        assert subject_id == "answer-1"
        return audit_result

    monkeypatch.setattr(sessions, "async_get_science_session", fake_get_session)
    monkeypatch.setattr(sessions, "get_audit_result_from_database", fake_get_audit)

    response = await sessions.get_research_audit_result_for_session(
        "session-1",
        "answer",
        "answer-1",
        types.SimpleNamespace(id="user-1"),
    )

    assert response.data["audit_id"] == "answer-1:audit"
    assert response.data["claims"][0]["evidence_ids"] == [31]


@pytest.mark.asyncio
async def test_get_research_audit_result_for_session_returns_404_when_missing(monkeypatch):
    sessions = _load_sessions_module(monkeypatch)
    session = FakeSession()

    async def fake_get_session(session_id):
        return session

    async def fake_get_audit(*args, **kwargs):
        return None

    monkeypatch.setattr(sessions, "async_get_science_session", fake_get_session)
    monkeypatch.setattr(sessions, "get_audit_result_from_database", fake_get_audit)

    with pytest.raises(sessions.HTTPException) as excinfo:
        await sessions.get_research_audit_result_for_session(
            "session-1",
            "report",
            "missing-report",
            types.SimpleNamespace(id="user-1"),
        )

    assert excinfo.value.status_code == 404


@pytest.mark.asyncio
async def test_promote_research_memory_requires_approved_audit_claim(monkeypatch):
    sessions = _load_sessions_module(monkeypatch)
    session = FakeSession()
    persisted_memory = {}

    async def fake_get_session(session_id):
        assert session_id == "session-1"
        return session

    audit_result = types.SimpleNamespace(
        claims=[
            {
                "claim_text": "Citation evidence is bounded.",
                "status": "approved",
                "evidence_ids": [17],
                "notes": [],
            },
            {
                "claim_text": "Memory can be cited.",
                "status": "invalid_source",
                "evidence_ids": [],
                "notes": ["memory is context-only"],
            },
        ]
    )

    async def fake_get_audit(database_url, *, session_id, subject_type, subject_id):
        assert database_url == sessions.settings.research_database_url
        assert session_id == "session-1"
        assert subject_type == "answer"
        assert subject_id == "answer-1"
        return audit_result

    async def fake_persist_memory(database_url, **kwargs):
        persisted_memory.update({"database_url": database_url, **kwargs})

    async def fake_list_memory(*args, **kwargs):
        return []

    monkeypatch.setattr(sessions, "async_get_science_session", fake_get_session)
    monkeypatch.setattr(sessions, "get_audit_result_from_database", fake_get_audit)
    monkeypatch.setattr(sessions, "list_memory_entries_from_database", fake_list_memory)
    monkeypatch.setattr(sessions, "persist_memory_entry_to_database", fake_persist_memory)

    response = await sessions.promote_research_memory_for_session(
        "session-1",
        sessions.ResearchMemoryPromotionRequest(
            subject_type="answer",
            subject_id="answer-1",
            claim_text="Citation evidence is bounded.",
        ),
        types.SimpleNamespace(id="user-1"),
    )

    assert response.data["source_type"] == "memory"
    assert response.data["context_only"] is True
    assert response.data["layer"] == "l2"
    assert response.data["content"] == "Citation evidence is bounded."
    assert persisted_memory["database_url"] == sessions.settings.research_database_url
    assert persisted_memory["session_id"] == "session-1"
    assert persisted_memory["user_id"] == "user-1"
    assert persisted_memory["layer"] == "L2"
    assert persisted_memory["content"] == "Citation evidence is bounded."
    assert persisted_memory["source_subject_type"] == "answer"
    assert persisted_memory["source_subject_id"] == "answer-1"
    assert response.data["created"] is True
    assert response.data["duplicate"] is False


@pytest.mark.asyncio
async def test_promote_research_memory_returns_existing_memory_without_duplicate_persist(monkeypatch):
    sessions = _load_sessions_module(monkeypatch)
    session = FakeSession()

    async def fake_get_session(session_id):
        return session

    audit_result = types.SimpleNamespace(
        claims=[
            {
                "claim_text": "Citation evidence is bounded.",
                "status": "approved",
                "evidence_ids": [17],
                "notes": [],
            }
        ]
    )

    existing_memory = types.SimpleNamespace(
        memory_id="mem-existing",
        layer="l2",
        title="Citation evidence is bounded.",
        content="Citation evidence is bounded.",
        source_subject_type="answer",
        source_subject_id="answer-1",
        to_context_dict=lambda: {
            "memory_id": "mem-existing",
            "layer": "l2",
            "title": "Citation evidence is bounded.",
            "content": "Citation evidence is bounded.",
            "source_type": "memory",
            "context_only": True,
            "source_subject_type": "answer",
            "source_subject_id": "answer-1",
        },
    )

    async def fake_get_audit(*args, **kwargs):
        return audit_result

    async def fake_list_memory(database_url, *, session_id, user_id, layer, limit):
        assert database_url == sessions.settings.research_database_url
        assert session_id == "session-1"
        assert user_id == "user-1"
        assert layer == "L2"
        assert limit == 100
        return [existing_memory]

    async def fail_persist_memory(*args, **kwargs):
        raise AssertionError("duplicate promotion must return existing memory instead of persisting")

    monkeypatch.setattr(sessions, "async_get_science_session", fake_get_session)
    monkeypatch.setattr(sessions, "get_audit_result_from_database", fake_get_audit)
    monkeypatch.setattr(sessions, "list_memory_entries_from_database", fake_list_memory)
    monkeypatch.setattr(sessions, "persist_memory_entry_to_database", fail_persist_memory)

    response = await sessions.promote_research_memory_for_session(
        "session-1",
        sessions.ResearchMemoryPromotionRequest(
            subject_type="answer",
            subject_id="answer-1",
            claim_text="Citation evidence is bounded.",
        ),
        types.SimpleNamespace(id="user-1"),
    )

    assert response.data["memory_id"] == "mem-existing"
    assert response.data["created"] is False
    assert response.data["duplicate"] is True
    assert response.data["source_type"] == "memory"
    assert response.data["context_only"] is True


@pytest.mark.asyncio
async def test_promote_research_memory_reuses_existing_l2_memory_across_user_sessions(monkeypatch):
    sessions = _load_sessions_module(monkeypatch)
    session = FakeSession()

    async def fake_get_session(session_id):
        assert session_id == "session-2"
        return session

    audit_result = types.SimpleNamespace(
        claims=[
            {
                "claim_text": "Citation evidence is bounded.",
                "status": "approved",
                "evidence_ids": [17],
                "notes": [],
            }
        ]
    )

    existing_memory = types.SimpleNamespace(
        memory_id="mem-existing",
        session_id="session-1",
        layer="l2",
        title="Citation evidence is bounded.",
        content="Citation evidence is bounded.",
        source_subject_type="answer",
        source_subject_id="answer-1",
        to_context_dict=lambda: {
            "memory_id": "mem-existing",
            "layer": "l2",
            "title": "Citation evidence is bounded.",
            "content": "Citation evidence is bounded.",
            "source_type": "memory",
            "context_only": True,
            "source_subject_type": "answer",
            "source_subject_id": "answer-1",
        },
    )

    async def fake_get_audit(*args, **kwargs):
        return audit_result

    async def fake_list_memory(database_url, *, session_id, user_id, layer, limit):
        assert database_url == sessions.settings.research_database_url
        assert session_id == "session-2"
        assert user_id == "user-1"
        assert layer == "L2"
        assert limit == 100
        return [existing_memory]

    async def fail_persist_memory(*args, **kwargs):
        raise AssertionError("cross-session duplicate promotion must reuse existing user memory")

    monkeypatch.setattr(sessions, "async_get_science_session", fake_get_session)
    monkeypatch.setattr(sessions, "get_audit_result_from_database", fake_get_audit)
    monkeypatch.setattr(sessions, "list_memory_entries_from_database", fake_list_memory)
    monkeypatch.setattr(sessions, "persist_memory_entry_to_database", fail_persist_memory)

    response = await sessions.promote_research_memory_for_session(
        "session-2",
        sessions.ResearchMemoryPromotionRequest(
            subject_type="answer",
            subject_id="answer-1",
            claim_text="Citation evidence is bounded.",
        ),
        types.SimpleNamespace(id="user-1"),
    )

    assert response.data["memory_id"] == "mem-existing"
    assert response.data["session_id"] == "session-1"
    assert response.data["created"] is False
    assert response.data["duplicate"] is True
    assert response.data["source_type"] == "memory"
    assert response.data["context_only"] is True


@pytest.mark.asyncio
async def test_promote_research_memory_rejects_unapproved_claim(monkeypatch):
    sessions = _load_sessions_module(monkeypatch)
    session = FakeSession()

    async def fake_get_session(session_id):
        return session

    audit_result = types.SimpleNamespace(
        claims=[
            {
                "claim_text": "Memory can be cited.",
                "status": "invalid_source",
                "evidence_ids": [],
                "notes": ["memory is context-only"],
            }
        ]
    )

    async def fake_get_audit(*args, **kwargs):
        return audit_result

    async def fail_persist_memory(*args, **kwargs):
        raise AssertionError("unapproved claims must not be persisted as memory")

    monkeypatch.setattr(sessions, "async_get_science_session", fake_get_session)
    monkeypatch.setattr(sessions, "get_audit_result_from_database", fake_get_audit)
    monkeypatch.setattr(sessions, "persist_memory_entry_to_database", fail_persist_memory)

    with pytest.raises(sessions.HTTPException) as excinfo:
        await sessions.promote_research_memory_for_session(
            "session-1",
            sessions.ResearchMemoryPromotionRequest(
                subject_type="answer",
                subject_id="answer-1",
                claim_text="Memory can be cited.",
            ),
            types.SimpleNamespace(id="user-1"),
        )

    assert excinfo.value.status_code == 400


@pytest.mark.asyncio
async def test_delete_research_memory_for_session_deletes_context_only_memory(monkeypatch):
    sessions = _load_sessions_module(monkeypatch)
    session = FakeSession()
    deleted_args = {}

    async def fake_get_session(session_id):
        assert session_id == "session-1"
        return session

    async def fake_delete_memory(database_url, *, session_id, memory_id):
        deleted_args.update(
            {
                "database_url": database_url,
                "session_id": session_id,
                "memory_id": memory_id,
            }
        )
        return True

    monkeypatch.setattr(sessions, "async_get_science_session", fake_get_session)
    monkeypatch.setattr(sessions, "delete_memory_entry_from_database", fake_delete_memory)

    response = await sessions.delete_research_memory_for_session(
        "session-1",
        "mem-1",
        types.SimpleNamespace(id="user-1"),
    )

    assert response.data == {
        "memory_id": "mem-1",
        "session_id": "session-1",
        "deleted": True,
        "source_type": "memory",
        "context_only": True,
    }
    assert deleted_args == {
        "database_url": sessions.settings.research_database_url,
        "session_id": "session-1",
        "memory_id": "mem-1",
    }


@pytest.mark.asyncio
async def test_delete_research_memory_for_session_returns_404_when_missing(monkeypatch):
    sessions = _load_sessions_module(monkeypatch)
    session = FakeSession()

    async def fake_get_session(session_id):
        return session

    async def fake_delete_memory(*args, **kwargs):
        return False

    monkeypatch.setattr(sessions, "async_get_science_session", fake_get_session)
    monkeypatch.setattr(sessions, "delete_memory_entry_from_database", fake_delete_memory)

    with pytest.raises(sessions.HTTPException) as excinfo:
        await sessions.delete_research_memory_for_session(
            "session-1",
            "missing-memory",
            types.SimpleNamespace(id="user-1"),
        )

    assert excinfo.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_research_memory_for_session_rejects_other_user(monkeypatch):
    sessions = _load_sessions_module(monkeypatch)
    session = FakeSession(user_id="other-user")

    async def fake_get_session(session_id):
        return session

    async def fail_delete_memory(*args, **kwargs):
        raise AssertionError("memory deletion must not run for another user's session")

    monkeypatch.setattr(sessions, "async_get_science_session", fake_get_session)
    monkeypatch.setattr(sessions, "delete_memory_entry_from_database", fail_delete_memory)

    with pytest.raises(sessions.HTTPException) as excinfo:
        await sessions.delete_research_memory_for_session(
            "session-1",
            "mem-1",
            types.SimpleNamespace(id="user-1"),
        )

    assert excinfo.value.status_code == 403


@pytest.mark.asyncio
async def test_get_research_evidence_record_for_session_returns_persisted_evidence(monkeypatch):
    sessions = _load_sessions_module(monkeypatch)
    session = FakeSession()

    async def fake_get_session(session_id):
        assert session_id == "session-1"
        return session

    evidence = types.SimpleNamespace(
        to_dict=lambda: {
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
    )

    async def fake_get_evidence(database_url, *, session_id, evidence_id):
        assert database_url == sessions.settings.research_database_url
        assert session_id == "session-1"
        assert evidence_id == 17
        return evidence

    monkeypatch.setattr(sessions, "async_get_science_session", fake_get_session)
    monkeypatch.setattr(sessions, "get_evidence_record_from_database", fake_get_evidence)

    response = await sessions.get_research_evidence_record_for_session(
        "session-1",
        17,
        types.SimpleNamespace(id="user-1"),
    )

    assert response.data["evidence_id"] == 17
    assert response.data["evidence_type"] == "paper"
    assert response.data["source_identity"]["file_path"] == "paper.pdf"


@pytest.mark.asyncio
async def test_get_research_evidence_record_for_session_returns_404_when_missing(monkeypatch):
    sessions = _load_sessions_module(monkeypatch)
    session = FakeSession()

    async def fake_get_session(session_id):
        return session

    async def fake_get_evidence(*args, **kwargs):
        return None

    monkeypatch.setattr(sessions, "async_get_science_session", fake_get_session)
    monkeypatch.setattr(sessions, "get_evidence_record_from_database", fake_get_evidence)

    with pytest.raises(sessions.HTTPException) as excinfo:
        await sessions.get_research_evidence_record_for_session(
            "session-1",
            999,
            types.SimpleNamespace(id="user-1"),
        )

    assert excinfo.value.status_code == 404


@pytest.mark.asyncio
async def test_research_report_completion_message_uses_generic_citation_evidence(monkeypatch, tmp_path):
    sessions = _load_sessions_module(monkeypatch)
    session = FakeSession(vm_root_dir=tmp_path)

    async def fake_get_session(session_id):
        assert session_id == "session-1"
        return session

    async def fake_report(*args, **kwargs):
        return types.SimpleNamespace(
            report_id="report-1",
            title="Evidence Boundary Note",
            question="Summarize the evidence",
            markdown_path=str(tmp_path / "research_reports" / "report-1.md"),
            evidence_map_path=str(tmp_path / "research_reports" / "report-1.evidence.json"),
            citation_count=2,
            to_dict=lambda: {
                "report_id": "report-1",
                "title": "Evidence Boundary Note",
                "question": "Summarize the evidence",
                "markdown_path": str(tmp_path / "research_reports" / "report-1.md"),
                "evidence_map_path": str(tmp_path / "research_reports" / "report-1.evidence.json"),
                "citation_count": 2,
            },
        )

    monkeypatch.setattr(sessions, "async_get_science_session", fake_get_session)
    monkeypatch.setattr(sessions, "generate_markdown_research_report", fake_report)
    monkeypatch.setattr(sessions, "_publish_session_event", lambda *args, **kwargs: None)

    response = await sessions.generate_research_report_for_session(
        "session-1",
        sessions.ResearchReportRequest(question="Summarize the evidence"),
        types.SimpleNamespace(id="user-1"),
    )

    assistant_messages = [
        event["data"]
        for event in session.events
        if event.get("event") == "message" and event.get("data", {}).get("role") == "assistant"
    ]
    assert assistant_messages[-1]["content"] == (
        "Generated Markdown research artifact `Evidence Boundary Note` with "
        "2 citation evidence records."
    )
    assert "paper citations" not in assistant_messages[-1]["content"]
    assert response.data["citation_count"] == 2


@pytest.mark.asyncio
async def test_research_report_failure_persists_failed_trace_step(monkeypatch, tmp_path):
    sessions = _load_sessions_module(monkeypatch)
    session = FakeSession(vm_root_dir=tmp_path)

    async def fake_get_session(session_id):
        assert session_id == "session-1"
        return session

    async def fail_report(*args, **kwargs):
        raise RuntimeError("report writer unavailable")

    monkeypatch.setattr(sessions, "async_get_science_session", fake_get_session)
    monkeypatch.setattr(sessions, "generate_markdown_research_report", fail_report)
    monkeypatch.setattr(sessions, "_publish_session_event", lambda *args, **kwargs: None)

    with pytest.raises(sessions.HTTPException) as excinfo:
        await sessions.generate_research_report_for_session(
            "session-1",
            sessions.ResearchReportRequest(question="Summarize the evidence"),
            types.SimpleNamespace(id="user-1"),
        )

    assert excinfo.value.status_code == 500
    failed_steps = [
        event["data"]
        for event in session.events
        if event.get("event") == "step" and event.get("data", {}).get("status") == "failed"
    ]
    assert len(failed_steps) == 1
    assert failed_steps[0]["id"].startswith("research-report-")
    assert failed_steps[0]["description"] == "Markdown research artifact generation failed"
    assert failed_steps[0]["metadata"]["question"] == "Summarize the evidence"
    assert "report writer unavailable" in failed_steps[0]["metadata"]["error"]
    assert session.save_count == 1


@pytest.mark.asyncio
async def test_save_tool_from_session_requires_passed_sandbox_validation(monkeypatch, tmp_path):
    sessions = _load_sessions_module(monkeypatch)
    workspace = tmp_path / "workspace"
    tools_dir = tmp_path / "Tools"
    staging = workspace / "session-1" / "tools_staging"
    staging.mkdir(parents=True)
    tools_dir.mkdir()
    (staging / "paper_lookup.py").write_text(
        '@tool\n'
        'def paper_lookup(query: str) -> str:\n'
        '    """Look up paper metadata."""\n'
        '    return query\n',
        encoding="utf-8",
    )
    session = FakeSession(vm_root_dir=workspace / "session-1")

    async def fake_get_session(session_id):
        assert session_id == "session-1"
        return session

    monkeypatch.setattr(sessions, "_WORKSPACE_DIR", str(workspace))
    monkeypatch.setattr(sessions, "_TOOLS_DIR", str(tools_dir))
    monkeypatch.setattr(sessions, "async_get_science_session", fake_get_session)

    with pytest.raises(sessions.HTTPException) as excinfo:
        await sessions.save_tool_from_session(
            "session-1",
            sessions.SaveToolRequest(
                tool_name="paper_lookup",
                user_confirmed=True,
                tool_pack="literature",
            ),
            types.SimpleNamespace(id="user-1"),
        )

    assert excinfo.value.status_code == 400
    assert "sandbox validation" in excinfo.value.detail
    assert not (tools_dir / "paper_lookup.py").exists()


@pytest.mark.asyncio
async def test_save_tool_from_session_persists_only_validated_tool(monkeypatch, tmp_path):
    sessions = _load_sessions_module(monkeypatch)
    workspace = tmp_path / "workspace"
    tools_dir = tmp_path / "Tools"
    staging = workspace / "session-1" / "tools_staging"
    staging.mkdir(parents=True)
    tools_dir.mkdir()
    tool_source = (
        '@tool\n'
        'def paper_lookup(query: str) -> str:\n'
        '    """Look up paper metadata."""\n'
        '    return query\n'
    )
    (staging / "paper_lookup.py").write_text(tool_source, encoding="utf-8")
    (staging / "paper_lookup.validation.json").write_text(
        json.dumps(
            {
                "tool_name": "paper_lookup",
                "status": "passed",
                "checks": ["python_syntax", "tool_function", "example_call", "input_schema", "return_schema"],
                "validated_at": "2026-06-21T00:00:00Z",
                "execution_environment": {
                    "type": "local_restricted",
                    "imports_allowed": False,
                },
                "source_sha256": hashlib.sha256(tool_source.encode("utf-8")).hexdigest(),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                    },
                    "required": ["query"],
                },
                "return_schema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "doi": {"type": "string"},
                    },
                    "required": ["title"],
                },
                "result_contract": {
                    "kind": "object",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "doi": {"type": "string"},
                        },
                        "required": ["title"],
                    },
                    "example_preview": {
                        "title": "evidence boundaries",
                        "doi": "10.1234/example",
                    },
                    "truncated": False,
                },
            }
        ),
        encoding="utf-8",
    )
    session = FakeSession(vm_root_dir=workspace / "session-1")

    async def fake_get_session(session_id):
        assert session_id == "session-1"
        return session

    monkeypatch.setattr(sessions, "_WORKSPACE_DIR", str(workspace))
    monkeypatch.setattr(sessions, "_TOOLS_DIR", str(tools_dir))
    monkeypatch.setattr(sessions, "async_get_science_session", fake_get_session)

    response = await sessions.save_tool_from_session(
        "session-1",
        sessions.SaveToolRequest(
            tool_name="paper_lookup",
            user_confirmed=True,
            tool_pack="literature",
        ),
        types.SimpleNamespace(id="user-1"),
    )

    assert (tools_dir / "paper_lookup.py").read_text(encoding="utf-8") == tool_source
    assert response.data["tool_name"] == "paper_lookup"
    assert response.data["tool_pack"] == {
        "id": "literature",
        "label": "Literature management",
        "research_workflow": "literature_management",
    }
    assert response.data["saved"] is True
    assert response.data["validation"] == {
        "status": "passed",
        "checks": ["python_syntax", "tool_function", "example_call", "input_schema", "return_schema"],
        "validated_at": "2026-06-21T00:00:00Z",
        "execution_environment": {
            "type": "local_restricted",
            "imports_allowed": False,
        },
        "source_sha256": hashlib.sha256(tool_source.encode("utf-8")).hexdigest(),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
            },
            "required": ["query"],
        },
        "return_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "doi": {"type": "string"},
            },
            "required": ["title"],
        },
        "result_contract": {
            "kind": "object",
            "schema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "doi": {"type": "string"},
                },
                "required": ["title"],
            },
            "example_preview": {
                "title": "evidence boundaries",
                "doi": "10.1234/example",
            },
            "truncated": False,
        },
    }


@pytest.mark.asyncio
async def test_save_tool_from_session_requires_explicit_user_confirmation(monkeypatch, tmp_path):
    sessions = _load_sessions_module(monkeypatch)
    workspace = tmp_path / "workspace"
    tools_dir = tmp_path / "Tools"
    staging = workspace / "session-1" / "tools_staging"
    staging.mkdir(parents=True)
    tools_dir.mkdir()
    tool_source = (
        '@tool\n'
        'def paper_lookup(query: str) -> str:\n'
        '    """Look up paper metadata."""\n'
        '    return query\n'
    )
    (staging / "paper_lookup.py").write_text(tool_source, encoding="utf-8")
    (staging / "paper_lookup.validation.json").write_text(
        json.dumps(
            {
                "tool_name": "paper_lookup",
                "status": "passed",
                "checks": ["python_syntax", "tool_function", "example_call", "input_schema", "return_schema"],
                "validated_at": "2026-06-21T00:00:00Z",
                "execution_environment": {
                    "type": "local_restricted",
                    "imports_allowed": False,
                },
                "source_sha256": hashlib.sha256(tool_source.encode("utf-8")).hexdigest(),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                    },
                    "required": ["query"],
                },
                "return_schema": {"type": "string"},
            }
        ),
        encoding="utf-8",
    )
    session = FakeSession(vm_root_dir=workspace / "session-1")

    async def fake_get_session(session_id):
        assert session_id == "session-1"
        return session

    monkeypatch.setattr(sessions, "_WORKSPACE_DIR", str(workspace))
    monkeypatch.setattr(sessions, "_TOOLS_DIR", str(tools_dir))
    monkeypatch.setattr(sessions, "async_get_science_session", fake_get_session)

    with pytest.raises(sessions.HTTPException) as excinfo:
        await sessions.save_tool_from_session(
            "session-1",
            sessions.SaveToolRequest(tool_name="paper_lookup", tool_pack="literature"),
            types.SimpleNamespace(id="user-1"),
        )

    assert excinfo.value.status_code == 400
    assert "user confirmation" in excinfo.value.detail
    assert not (tools_dir / "paper_lookup.py").exists()


@pytest.mark.asyncio
async def test_save_tool_from_session_requires_research_tool_pack(monkeypatch, tmp_path):
    sessions = _load_sessions_module(monkeypatch)
    workspace = tmp_path / "workspace"
    tools_dir = tmp_path / "Tools"
    staging = workspace / "session-1" / "tools_staging"
    staging.mkdir(parents=True)
    tools_dir.mkdir()
    tool_source = (
        '@tool\n'
        'def paper_lookup(query: str) -> str:\n'
        '    """Look up paper metadata."""\n'
        '    return query\n'
    )
    (staging / "paper_lookup.py").write_text(tool_source, encoding="utf-8")
    (staging / "paper_lookup.validation.json").write_text(
        json.dumps(
            {
                "tool_name": "paper_lookup",
                "status": "passed",
                "checks": ["python_syntax", "tool_function", "example_call", "input_schema", "return_schema"],
                "validated_at": "2026-06-21T00:00:00Z",
                "execution_environment": {
                    "type": "local_restricted",
                    "imports_allowed": False,
                },
                "source_sha256": hashlib.sha256(tool_source.encode("utf-8")).hexdigest(),
                "input_schema": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
                "return_schema": {"type": "string"},
                "result_contract": {
                    "kind": "text",
                    "schema": {"type": "string"},
                    "example_preview": "evidence boundaries",
                    "truncated": False,
                },
            }
        ),
        encoding="utf-8",
    )
    session = FakeSession(vm_root_dir=workspace / "session-1")

    async def fake_get_session(session_id):
        assert session_id == "session-1"
        return session

    monkeypatch.setattr(sessions, "_WORKSPACE_DIR", str(workspace))
    monkeypatch.setattr(sessions, "_TOOLS_DIR", str(tools_dir))
    monkeypatch.setattr(sessions, "async_get_science_session", fake_get_session)

    with pytest.raises(sessions.HTTPException) as missing_pack:
        await sessions.save_tool_from_session(
            "session-1",
            sessions.SaveToolRequest(
                tool_name="paper_lookup",
                user_confirmed=True,
            ),
            types.SimpleNamespace(id="user-1"),
        )

    with pytest.raises(sessions.HTTPException) as invalid_pack:
        await sessions.save_tool_from_session(
            "session-1",
            sessions.SaveToolRequest(
                tool_name="paper_lookup",
                user_confirmed=True,
                tool_pack="general",
            ),
            types.SimpleNamespace(id="user-1"),
        )

    assert missing_pack.value.status_code == 400
    assert "research tool pack" in missing_pack.value.detail
    assert invalid_pack.value.status_code == 400
    assert "research tool pack" in invalid_pack.value.detail
    assert not (tools_dir / "paper_lookup.py").exists()


@pytest.mark.asyncio
async def test_save_tool_from_session_rejects_stale_validation_source(monkeypatch, tmp_path):
    sessions = _load_sessions_module(monkeypatch)
    workspace = tmp_path / "workspace"
    tools_dir = tmp_path / "Tools"
    staging = workspace / "session-1" / "tools_staging"
    staging.mkdir(parents=True)
    tools_dir.mkdir()
    original_source = (
        '@tool\n'
        'def paper_lookup(query: str) -> dict:\n'
        '    """Look up paper metadata."""\n'
        '    return {"title": query}\n'
    )
    changed_source = (
        '@tool\n'
        'def paper_lookup(query: str) -> dict:\n'
        '    """Look up paper metadata."""\n'
        '    return {"title": query, "changed": True}\n'
    )
    (staging / "paper_lookup.py").write_text(changed_source, encoding="utf-8")
    (staging / "paper_lookup.validation.json").write_text(
        json.dumps(
            {
                "tool_name": "paper_lookup",
                "status": "passed",
                "checks": ["python_syntax", "tool_function", "example_call", "return_schema"],
                "validated_at": "2026-06-21T00:00:00Z",
                "execution_environment": {
                    "type": "local_restricted",
                    "imports_allowed": False,
                },
                "source_sha256": hashlib.sha256(original_source.encode("utf-8")).hexdigest(),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                    },
                    "required": ["query"],
                },
                "return_schema": {
                    "type": "object",
                    "properties": {"title": {"type": "string"}},
                    "required": ["title"],
                },
                "result_contract": {
                    "kind": "object",
                    "schema": {
                        "type": "object",
                        "properties": {"title": {"type": "string"}},
                        "required": ["title"],
                    },
                    "example_preview": {"title": "evidence boundaries"},
                    "truncated": False,
                },
            }
        ),
        encoding="utf-8",
    )
    session = FakeSession(vm_root_dir=workspace / "session-1")

    async def fake_get_session(session_id):
        assert session_id == "session-1"
        return session

    monkeypatch.setattr(sessions, "_WORKSPACE_DIR", str(workspace))
    monkeypatch.setattr(sessions, "_TOOLS_DIR", str(tools_dir))
    monkeypatch.setattr(sessions, "async_get_science_session", fake_get_session)

    with pytest.raises(sessions.HTTPException) as excinfo:
        await sessions.save_tool_from_session(
            "session-1",
            sessions.SaveToolRequest(
                tool_name="paper_lookup",
                user_confirmed=True,
                tool_pack="literature",
            ),
            types.SimpleNamespace(id="user-1"),
        )

    assert excinfo.value.status_code == 400
    assert "current tool source" in excinfo.value.detail
    assert not (tools_dir / "paper_lookup.py").exists()


@pytest.mark.asyncio
async def test_save_tool_from_session_requires_return_schema_validation(monkeypatch, tmp_path):
    sessions = _load_sessions_module(monkeypatch)
    workspace = tmp_path / "workspace"
    tools_dir = tmp_path / "Tools"
    staging = workspace / "session-1" / "tools_staging"
    staging.mkdir(parents=True)
    tools_dir.mkdir()
    (staging / "paper_lookup.py").write_text(
        '@tool\n'
        'def paper_lookup(query: str) -> str:\n'
        '    """Look up paper metadata."""\n'
        '    return query\n',
        encoding="utf-8",
    )
    (staging / "paper_lookup.validation.json").write_text(
        json.dumps(
            {
                "tool_name": "paper_lookup",
                "status": "passed",
                "checks": ["sandbox_import", "example_call"],
                "validated_at": "2026-06-21T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )
    session = FakeSession(vm_root_dir=workspace / "session-1")

    async def fake_get_session(session_id):
        assert session_id == "session-1"
        return session

    monkeypatch.setattr(sessions, "_WORKSPACE_DIR", str(workspace))
    monkeypatch.setattr(sessions, "_TOOLS_DIR", str(tools_dir))
    monkeypatch.setattr(sessions, "async_get_science_session", fake_get_session)

    with pytest.raises(sessions.HTTPException) as excinfo:
        await sessions.save_tool_from_session(
            "session-1",
            sessions.SaveToolRequest(
                tool_name="paper_lookup",
                user_confirmed=True,
                tool_pack="literature",
            ),
            types.SimpleNamespace(id="user-1"),
        )

    assert excinfo.value.status_code == 400
    assert "return schema" in excinfo.value.detail
    assert not (tools_dir / "paper_lookup.py").exists()


@pytest.mark.asyncio
async def test_save_tool_from_session_requires_input_schema_validation(monkeypatch, tmp_path):
    sessions = _load_sessions_module(monkeypatch)
    workspace = tmp_path / "workspace"
    tools_dir = tmp_path / "Tools"
    staging = workspace / "session-1" / "tools_staging"
    staging.mkdir(parents=True)
    tools_dir.mkdir()
    tool_source = (
        '@tool\n'
        'def paper_lookup(query: str) -> str:\n'
        '    """Look up paper metadata."""\n'
        '    return query\n'
    )
    (staging / "paper_lookup.py").write_text(tool_source, encoding="utf-8")
    (staging / "paper_lookup.validation.json").write_text(
        json.dumps(
            {
                "tool_name": "paper_lookup",
                "status": "passed",
                "checks": ["python_syntax", "tool_function", "example_call", "return_schema"],
                "validated_at": "2026-06-21T00:00:00Z",
                "execution_environment": {
                    "type": "local_restricted",
                    "imports_allowed": False,
                },
                "source_sha256": hashlib.sha256(tool_source.encode("utf-8")).hexdigest(),
                "return_schema": {"type": "string"},
            }
        ),
        encoding="utf-8",
    )
    session = FakeSession(vm_root_dir=workspace / "session-1")

    async def fake_get_session(session_id):
        assert session_id == "session-1"
        return session

    monkeypatch.setattr(sessions, "_WORKSPACE_DIR", str(workspace))
    monkeypatch.setattr(sessions, "_TOOLS_DIR", str(tools_dir))
    monkeypatch.setattr(sessions, "async_get_science_session", fake_get_session)

    with pytest.raises(sessions.HTTPException) as excinfo:
        await sessions.save_tool_from_session(
            "session-1",
            sessions.SaveToolRequest(
                tool_name="paper_lookup",
                user_confirmed=True,
                tool_pack="literature",
            ),
            types.SimpleNamespace(id="user-1"),
        )

    assert excinfo.value.status_code == 400
    assert "input schema" in excinfo.value.detail
    assert not (tools_dir / "paper_lookup.py").exists()


@pytest.mark.asyncio
async def test_validate_tool_from_session_generates_validation_sidecar(monkeypatch, tmp_path):
    sessions = _load_sessions_module(monkeypatch)
    workspace = tmp_path / "workspace"
    staging = workspace / "session-1" / "tools_staging"
    staging.mkdir(parents=True)
    (staging / "paper_lookup.py").write_text(
        '@tool\n'
        'def paper_lookup(query: str) -> dict:\n'
        '    """Look up paper metadata."""\n'
        '    return {"title": query, "doi": "10.1234/example"}\n',
        encoding="utf-8",
    )
    session = FakeSession(vm_root_dir=workspace / "session-1")

    async def fake_get_session(session_id):
        assert session_id == "session-1"
        return session

    monkeypatch.setattr(sessions, "_WORKSPACE_DIR", str(workspace))
    monkeypatch.setattr(sessions, "async_get_science_session", fake_get_session)

    response = await sessions.validate_tool_from_session(
        "session-1",
        sessions.ValidateToolRequest(
            tool_name="paper_lookup",
            example_args={"query": "evidence boundaries"},
        ),
        types.SimpleNamespace(id="user-1"),
    )

    assert response.data["tool_name"] == "paper_lookup"
    assert response.data["status"] == "passed"
    assert response.data["return_schema"] == {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "doi": {"type": "string"},
        },
        "required": ["title", "doi"],
    }
    assert response.data["result_contract"] == {
        "kind": "object",
        "schema": response.data["return_schema"],
        "example_preview": {
            "title": "evidence boundaries",
            "doi": "10.1234/example",
        },
        "truncated": False,
    }
    assert response.data["execution_environment"] == {
        "type": "local_restricted",
        "imports_allowed": False,
    }
    sidecar = json.loads((staging / "paper_lookup.validation.json").read_text(encoding="utf-8"))
    assert sidecar == response.data


@pytest.mark.asyncio
async def test_validate_tool_from_session_uses_sandbox_container_when_available(monkeypatch, tmp_path):
    sessions = _load_sessions_module(monkeypatch)
    workspace = tmp_path / "workspace"
    staging = workspace / "session-1" / "tools_staging"
    staging.mkdir(parents=True)
    (staging / "paper_lookup.py").write_text(
        '@tool\n'
        'def paper_lookup(query: str) -> dict:\n'
        '    """Look up paper metadata."""\n'
        '    return {"title": query}\n',
        encoding="utf-8",
    )
    session = FakeSession(vm_root_dir=workspace / "session-1")
    executed = []

    async def fake_get_session(session_id):
        assert session_id == "session-1"
        return session

    class FakeSandboxBackend:
        def __init__(self, session_id, user_id):
            assert session_id == "session-1"
            assert user_id == "user-1"
            self.workspace = "/workspace/session-1"

        def execute(self, command, *, timeout=None):
            executed.append((command, timeout))
            return types.SimpleNamespace(
                exit_code=0,
                output=json.dumps({"status": "passed", "result": {"title": "evidence boundaries"}}),
                truncated=False,
            )

    monkeypatch.setattr(sessions, "_WORKSPACE_DIR", str(workspace))
    monkeypatch.setattr(sessions, "async_get_science_session", fake_get_session)
    monkeypatch.setattr(sessions, "FullSandboxBackend", FakeSandboxBackend)
    monkeypatch.setenv("SANDBOX_TOOL_VALIDATION", "1")

    response = await sessions.validate_tool_from_session(
        "session-1",
        sessions.ValidateToolRequest(
            tool_name="paper_lookup",
            example_args={"query": "evidence boundaries"},
        ),
        types.SimpleNamespace(id="user-1"),
    )

    assert executed
    assert response.data["status"] == "passed"
    assert response.data["checks"] == [
        "python_syntax",
        "tool_function",
        "sandbox_example_call",
        "input_schema",
        "return_schema",
    ]
    assert response.data["execution_environment"] == {
        "type": "sandbox_container",
        "backend": "full_sandbox",
        "sandbox_workspace": "/workspace/session-1",
        "imports_allowed": False,
    }
    assert response.data["example_output"] == {"title": "evidence boundaries"}
    step = session.events[0]["data"]
    assert step["metadata"]["execution_environment"] == response.data["execution_environment"]


@pytest.mark.asyncio
async def test_validate_tool_from_session_persists_completed_trace_step(monkeypatch, tmp_path):
    sessions = _load_sessions_module(monkeypatch)
    workspace = tmp_path / "workspace"
    staging = workspace / "session-1" / "tools_staging"
    staging.mkdir(parents=True)
    (staging / "paper_lookup.py").write_text(
        '@tool\n'
        'def paper_lookup(query: str) -> dict:\n'
        '    """Look up paper metadata."""\n'
        '    return {"title": query}\n',
        encoding="utf-8",
    )
    session = FakeSession(vm_root_dir=workspace / "session-1")
    published = []

    async def fake_get_session(session_id):
        assert session_id == "session-1"
        return session

    monkeypatch.setattr(sessions, "_WORKSPACE_DIR", str(workspace))
    monkeypatch.setattr(sessions, "async_get_science_session", fake_get_session)
    monkeypatch.setattr(sessions, "_publish_session_event", lambda *args: published.append(args))

    response = await sessions.validate_tool_from_session(
        "session-1",
        sessions.ValidateToolRequest(
            tool_name="paper_lookup",
            example_args={"query": "evidence boundaries"},
        ),
        types.SimpleNamespace(id="user-1"),
    )

    assert response.data["status"] == "passed"
    assert session.save_count == 1
    assert len(session.events) == 1
    step = session.events[0]["data"]
    assert step["status"] == "completed"
    assert step["description"] == "Custom tool validation passed: paper_lookup"
    assert step["metadata"] == {
        "tool_name": "paper_lookup",
        "validation_status": "passed",
        "checks": ["python_syntax", "tool_function", "example_call", "input_schema", "return_schema"],
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
            },
            "required": ["query"],
        },
        "return_schema": {
            "type": "object",
            "properties": {"title": {"type": "string"}},
            "required": ["title"],
        },
        "result_contract": {
            "kind": "object",
            "schema": {
                "type": "object",
                "properties": {"title": {"type": "string"}},
                "required": ["title"],
            },
            "example_preview": {"title": "evidence boundaries"},
            "truncated": False,
        },
        "execution_environment": {
            "type": "local_restricted",
            "imports_allowed": False,
        },
    }
    assert published[0][0] == "session-1"
    assert published[0][1] == "user-1"
    assert published[0][2] == session.events[0]


@pytest.mark.asyncio
async def test_validate_tool_from_session_persists_failed_trace_step(monkeypatch, tmp_path):
    sessions = _load_sessions_module(monkeypatch)
    workspace = tmp_path / "workspace"
    staging = workspace / "session-1" / "tools_staging"
    staging.mkdir(parents=True)
    (staging / "paper_lookup.py").write_text(
        'def paper_lookup(query: str) -> dict:\n'
        '    return {"title": query}\n',
        encoding="utf-8",
    )
    session = FakeSession(vm_root_dir=workspace / "session-1")

    async def fake_get_session(session_id):
        assert session_id == "session-1"
        return session

    monkeypatch.setattr(sessions, "_WORKSPACE_DIR", str(workspace))
    monkeypatch.setattr(sessions, "async_get_science_session", fake_get_session)
    monkeypatch.setattr(sessions, "_publish_session_event", lambda *args: None)

    response = await sessions.validate_tool_from_session(
        "session-1",
        sessions.ValidateToolRequest(
            tool_name="paper_lookup",
            example_args={"query": "evidence boundaries"},
        ),
        types.SimpleNamespace(id="user-1"),
    )

    assert response.data["status"] == "failed"
    assert session.save_count == 1
    assert len(session.events) == 1
    step = session.events[0]["data"]
    assert step["status"] == "failed"
    assert step["description"] == "Custom tool validation failed: paper_lookup"
    assert step["metadata"]["tool_name"] == "paper_lookup"
    assert step["metadata"]["validation_status"] == "failed"
    assert step["metadata"]["checks"] == ["python_syntax"]
    assert "No @tool-decorated function" in step["metadata"]["error"]


@pytest.mark.asyncio
async def test_research_upload_marks_session_completed_after_indexing(monkeypatch, tmp_path):
    sessions = _load_sessions_module(monkeypatch)
    session = FakeSession(vm_root_dir=tmp_path)

    async def fake_get_session(session_id):
        assert session_id == "session-1"
        return session

    async def fake_index_ingestion_result(*args, **kwargs):
        return types.SimpleNamespace(
            evidence_record_count=1,
            embedding_count=1,
            embedding_model="local-hashing-v1",
        )

    paper = types.SimpleNamespace(
        paper_id="paper-1",
        title="Paper 1",
        authors=[],
        parser="grobid-tei",
    )
    ingestion = types.SimpleNamespace(
        paper=paper,
        chunks=[types.SimpleNamespace(chunk_id="chunk-1")],
        artifact=types.SimpleNamespace(
            manifest_path="/workspace/research_data/paper-1/canonical_paper.json",
            evidence_preview_path="/workspace/research_data/paper-1/evidence_preview.md",
        ),
    )

    monkeypatch.setattr(sessions, "_WORKSPACE_DIR", str(tmp_path))
    monkeypatch.setattr(sessions, "async_get_science_session", fake_get_session)
    monkeypatch.setattr(sessions, "is_research_document", lambda path: True)
    monkeypatch.setattr(sessions, "ingest_uploaded_paper", lambda **kwargs: ingestion)
    monkeypatch.setattr(sessions, "index_ingestion_result", fake_index_ingestion_result)
    monkeypatch.setattr(sessions, "_publish_session_event", lambda *args, **kwargs: None)

    response = await sessions.upload_session_file(
        "session-1",
        FakeUpload(),
        types.SimpleNamespace(id="user-1"),
    )

    assert response.data["metadata"]["research_assistant"]["status"] == "indexed"
    assert session.status == sessions.SessionStatus.COMPLETED
    assert session.events[-1]["data"]["description"] == "Paper evidence indexed: paper.pdf"
