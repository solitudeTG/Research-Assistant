import importlib
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

    monkeypatch.setattr(sessions, "async_get_science_session", fake_get_session)
    monkeypatch.setattr(sessions, "get_audit_result_from_database", fake_get_audit)
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
    assert persisted_memory["layer"] == "L2"
    assert persisted_memory["content"] == "Citation evidence is bounded."
    assert persisted_memory["source_subject_type"] == "answer"
    assert persisted_memory["source_subject_id"] == "answer-1"


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
