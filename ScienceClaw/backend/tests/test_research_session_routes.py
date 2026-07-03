import importlib
import hashlib
import json
import sys
import types
from pathlib import Path

import pytest

from backend.research_assistant.admission import skipped_admission_result
from backend.research_assistant.answering import ResearchAnswer, ResearchCitation
from backend.research_assistant.task_router import ResearchTaskRoute


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


class FakeProject:
    def __init__(self, *, project_id="project-1", name="LEO Beamforming"):
        self.project_id = project_id
        self.name = name

    def to_dict(self):
        return {
            "project_id": self.project_id,
            "user_id": "user-1",
            "name": self.name,
            "description": "Narrow beam papers",
            "paper_count": 0,
            "chunk_count": 0,
            "evidence_record_count": 0,
            "created_at": None,
            "updated_at": None,
        }


class FakeProjectPaper:
    def to_dict(self):
        return {
            "paper_id": "paper-1",
            "project_id": "project-1",
            "session_id": "session-1",
            "user_id": "user-1",
            "title": "Space-Time Beamforming",
            "authors": ["Ada Lovelace"],
            "abstract": "Narrow beams for LEO.",
            "source_path": "/tmp/paper.pdf",
            "parser": "grobid-tei",
            "source_identity": {"file_path": "/tmp/paper.pdf"},
            "chunk_count": 4,
            "evidence_record_count": 4,
            "status": "indexed",
            "citation_ready": True,
            "created_at": None,
            "updated_at": None,
        }


class FakeSubagentDefinition:
    def __init__(self, *, name="research_auditor"):
        self.name = name
        self.agent_type = "custom"
        self.source = "registry"
        self.editable = True
        self.display_name = "Auditor Agent"
        self.description = "Audit claims."
        self.system_prompt = "You are the Research Auditor Agent."
        self.skill_refs = ["research-evidence-audit"]
        self.allowed_tools = ["audit_evidence_claims"]
        self.input_boundaries = {}
        self.output_boundary = "process_trace"
        self.can_answer_user = False
        self.can_write_artifacts = False
        self.enabled = True
        self.version = 1
        self.validation_status = "valid"
        self.citation_evidence = False
        self.metadata = {}

    def to_dict(self):
        return {
            "name": self.name,
            "display_name": self.display_name,
            "agent_type": self.agent_type,
            "source": self.source,
            "editable": self.editable,
            "description": self.description,
            "system_prompt": self.system_prompt,
            "skill_refs": self.skill_refs,
            "allowed_tools": self.allowed_tools,
            "input_boundaries": self.input_boundaries,
            "output_boundary": self.output_boundary,
            "can_answer_user": self.can_answer_user,
            "can_write_artifacts": self.can_write_artifacts,
            "enabled": self.enabled,
            "version": self.version,
            "validation_status": self.validation_status,
            "citation_evidence": self.citation_evidence,
            "metadata": self.metadata,
        }


def test_research_answer_and_report_routes_use_citation_evidence_wording():
    sessions_source = (
        Path(__file__).resolve().parents[1]
        / "route"
        / "sessions.py"
    ).read_text(encoding="utf-8")

    assert "Research question grounded in citation evidence" in sessions_source
    assert "Research question or note topic grounded in citation evidence" in sessions_source
    assert "Answer a question using citation evidence from the research store." in sessions_source
    assert 'description="Checking whether citation evidence is needed"' in sessions_source
    assert '"Citation evidence retrieval skipped"' in sessions_source
    assert "Generate a Markdown research artifact using citation evidence and context memory." in sessions_source
    assert 'description="Generating Markdown research artifact from citation evidence"' in sessions_source
    assert '"mode": "citation_evidence"' in sessions_source

    assert "Research question grounded in uploaded papers" not in sessions_source
    assert "Research question or note topic grounded in uploaded papers" not in sessions_source
    assert "using only citation evidence from uploaded papers" not in sessions_source
    assert "Retrieving citation evidence from uploaded papers" not in sessions_source
    assert "using only uploaded paper evidence" not in sessions_source
    assert "Generating Markdown research artifact from uploaded paper evidence" not in sessions_source
    assert '"mode": "paper_evidence"' not in sessions_source


def test_tool_call_mapping_preserves_subagent_lifecycle_metadata(monkeypatch):
    sessions = _load_sessions_module(monkeypatch)
    lifecycle = {
        "task_id": "call-reader-1",
        "agent_name": "paper_reader_worker",
        "agent_role": "reader",
        "phase": "started",
        "status": "running",
        "output_boundary": "context_only",
        "citation_evidence": False,
    }

    mapped = sessions._map_science_stream_to_agent_event(
        {
            "event": "tool_call",
            "data": {
                "tool_call_id": "call-reader-1",
                "function": "task",
                "args": {"subagent_type": "paper_reader_worker"},
                "subagent_lifecycle": lifecycle,
            },
        }
    )

    assert mapped["event"] == "tool"
    assert mapped["data"]["metadata"]["subagent_lifecycle"] == lifecycle


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
async def test_create_research_project_route_persists_project(monkeypatch):
    sessions = _load_sessions_module(monkeypatch)
    persisted = {}

    async def fake_create_project(database_url, **kwargs):
        persisted["database_url"] = database_url
        persisted.update(kwargs)
        return FakeProject(project_id=kwargs["project_id"], name=kwargs["name"])

    monkeypatch.setattr(sessions, "create_research_project_in_database", fake_create_project)
    monkeypatch.setattr(sessions.shortuuid, "uuid", lambda: "project-uuid")

    response = await sessions.create_research_project_for_user(
        sessions.ResearchProjectCreateRequest(
            name="LEO Beamforming",
            description="Narrow beam papers",
        ),
        types.SimpleNamespace(id="user-1"),
    )

    assert persisted == {
        "database_url": sessions.settings.research_database_url,
        "project_id": "research-project-project-uuid",
        "user_id": "user-1",
        "name": "LEO Beamforming",
        "description": "Narrow beam papers",
    }
    assert response.data["project_id"] == "research-project-project-uuid"
    assert response.data["name"] == "LEO Beamforming"


@pytest.mark.asyncio
async def test_list_research_projects_route_returns_user_projects(monkeypatch):
    sessions = _load_sessions_module(monkeypatch)
    called = {}

    async def fake_list_projects(database_url, **kwargs):
        called["database_url"] = database_url
        called.update(kwargs)
        return [FakeProject()]

    monkeypatch.setattr(sessions, "list_research_projects_from_database", fake_list_projects)

    response = await sessions.list_research_projects_for_user(
        types.SimpleNamespace(id="user-1"),
    )

    assert called == {
        "database_url": sessions.settings.research_database_url,
        "user_id": "user-1",
    }
    assert response.data["projects"][0]["project_id"] == "project-1"


@pytest.mark.asyncio
async def test_list_research_agents_route_returns_governed_registry(monkeypatch):
    sessions = _load_sessions_module(monkeypatch)
    calls = []

    async def fake_ensure_agents(database_url):
        calls.append(("ensure", database_url))

    async def fake_list_agents(database_url, *, enabled_only):
        calls.append(("list", database_url, enabled_only))
        return [FakeSubagentDefinition()]

    monkeypatch.setattr(sessions, "ensure_subagent_definitions_in_database", fake_ensure_agents)
    monkeypatch.setattr(sessions, "list_subagent_definitions_from_database", fake_list_agents)

    response = await sessions.list_research_agents_for_user(types.SimpleNamespace(id="user-1"))

    assert calls == [
        ("ensure", sessions.settings.research_database_url),
        ("list", sessions.settings.research_database_url, False),
    ]
    assert response.data["agents"][0]["name"] == "general-purpose"
    agents = {agent["name"]: agent for agent in response.data["agents"]}
    assert set(agents) == {"general-purpose", "research_auditor"}
    assert agents["general-purpose"]["agent_type"] == "system_builtin"
    assert agents["general-purpose"]["source"] == "deepagents_builtin"
    assert agents["general-purpose"]["editable"] is False
    assert agents["general-purpose"]["citation_evidence"] is False
    assert agents["research_auditor"]["agent_type"] == "custom"
    assert agents["research_auditor"]["editable"] is True
    assert agents["research_auditor"]["can_answer_user"] is False
    assert agents["research_auditor"]["citation_evidence"] is False


@pytest.mark.asyncio
async def test_list_research_agent_runs_route_returns_recent_preview(monkeypatch):
    sessions = _load_sessions_module(monkeypatch)
    calls = []

    async def fake_list_runs(database_url, *, agent_name, limit):
        calls.append((database_url, agent_name, limit))
        return [
            {
                "task_id": "task-1",
                "agent_name": agent_name,
                "status": "completed",
                "output_boundary": "context_only",
                "citation_evidence": False,
            }
        ]

    monkeypatch.setattr(sessions, "list_recent_subagent_runs_from_database", fake_list_runs)

    response = await sessions.list_research_agent_runs_for_user(
        "paper_reader_worker",
        limit=3,
        current_user=types.SimpleNamespace(id="user-1"),
    )

    assert calls == [(sessions.settings.research_database_url, "paper_reader_worker", 3)]
    assert response.data == {
        "agent_name": "paper_reader_worker",
        "runs": [
            {
                "task_id": "task-1",
                "agent_name": "paper_reader_worker",
                "status": "completed",
                "output_boundary": "context_only",
                "citation_evidence": False,
            }
        ],
    }


@pytest.mark.asyncio
async def test_validate_research_agent_route_runs_custom_validation_example(monkeypatch):
    sessions = _load_sessions_module(monkeypatch)

    async def fake_ensure_agents(database_url):
        return None

    async def fake_list_agents(database_url, *, enabled_only):
        return [FakeSubagentDefinition(name="paper_reader_worker")]

    monkeypatch.setattr(sessions, "ensure_subagent_definitions_in_database", fake_ensure_agents)
    monkeypatch.setattr(sessions, "list_subagent_definitions_from_database", fake_list_agents)

    response = await sessions.validate_research_agent_for_user(
        "paper_reader_worker",
        current_user=types.SimpleNamespace(id="user-1"),
    )

    assert response.data["agent_name"] == "paper_reader_worker"
    assert response.data["status"] == "passed"
    assert response.data["editable"] is True
    assert response.data["example_result"]["agent"] == "paper_reader_worker"
    assert response.data["example_result"]["boundary"] == "context_only"
    assert response.data["example_result"]["citation_evidence"] is False


@pytest.mark.asyncio
async def test_update_research_agent_route_allows_custom_agent_edits(monkeypatch):
    sessions = _load_sessions_module(monkeypatch)
    calls = []

    async def fake_ensure_agents(database_url):
        calls.append(("ensure", database_url))

    async def fake_list_agents(database_url, *, enabled_only):
        calls.append(("list", database_url, enabled_only))
        return [FakeSubagentDefinition(name="paper_reader_worker")]

    async def fake_update_agent(database_url, *, name, updates):
        calls.append(("update", database_url, name, updates))
        updated = FakeSubagentDefinition(name=name)
        updated.display_name = updates["display_name"]
        updated.description = updates["description"]
        updated.system_prompt = updates["system_prompt"]
        updated.enabled = updates["enabled"]
        updated.version = 2
        updated.validation_status = "draft"
        return updated

    monkeypatch.setattr(sessions, "ensure_subagent_definitions_in_database", fake_ensure_agents)
    monkeypatch.setattr(sessions, "list_subagent_definitions_from_database", fake_list_agents)
    monkeypatch.setattr(sessions, "update_subagent_definition_in_database", fake_update_agent)

    payload = sessions.ResearchAgentUpdateRequest(
        display_name="Reader Worker Tuned",
        description="Read scoped materials with sharper extraction.",
        system_prompt="You are a scoped Reader Worker. Return context-only notes.",
        skill_refs=["research-paper-reading"],
        allowed_tools=["read_research_evidence"],
        input_boundaries={"requires": ["material_package"]},
        output_boundary="context_only",
        enabled=False,
        metadata={"edited_by": "route-test"},
    )

    response = await sessions.update_research_agent_for_user(
        "paper_reader_worker",
        payload,
        current_user=types.SimpleNamespace(id="user-1"),
    )

    assert calls[0] == ("ensure", sessions.settings.research_database_url)
    assert calls[1] == ("list", sessions.settings.research_database_url, False)
    assert calls[2][0:3] == (
        "update",
        sessions.settings.research_database_url,
        "paper_reader_worker",
    )
    assert calls[2][3]["display_name"] == "Reader Worker Tuned"
    assert calls[2][3]["enabled"] is False
    assert response.data["agent"]["name"] == "paper_reader_worker"
    assert response.data["agent"]["editable"] is True
    assert response.data["agent"]["validation_status"] == "draft"


@pytest.mark.asyncio
async def test_update_research_agent_route_rejects_system_builtin(monkeypatch):
    sessions = _load_sessions_module(monkeypatch)

    async def fake_ensure_agents(database_url):
        return None

    async def fake_list_agents(database_url, *, enabled_only):
        return []

    monkeypatch.setattr(sessions, "ensure_subagent_definitions_in_database", fake_ensure_agents)
    monkeypatch.setattr(sessions, "list_subagent_definitions_from_database", fake_list_agents)

    payload = sessions.ResearchAgentUpdateRequest(description="Cannot edit built-in")

    with pytest.raises(Exception) as exc_info:
        await sessions.update_research_agent_for_user(
            "general-purpose",
            payload,
            current_user=types.SimpleNamespace(id="user-1"),
        )

    assert getattr(exc_info.value, "status_code", None) == 403


@pytest.mark.asyncio
async def test_list_research_project_papers_route_returns_project_assets(monkeypatch):
    sessions = _load_sessions_module(monkeypatch)
    called = {}

    async def fake_list_project_papers(database_url, **kwargs):
        called["database_url"] = database_url
        called.update(kwargs)
        return [FakeProjectPaper()]

    monkeypatch.setattr(sessions, "list_project_paper_assets_from_database", fake_list_project_papers)

    response = await sessions.list_research_project_papers_for_user(
        "project-1",
        types.SimpleNamespace(id="user-1"),
    )

    assert called == {
        "database_url": sessions.settings.research_database_url,
        "project_id": "project-1",
        "user_id": "user-1",
    }
    assert response.data["project_id"] == "project-1"
    assert response.data["papers"][0]["title"] == "Space-Time Beamforming"


@pytest.mark.asyncio
async def test_upload_research_project_paper_indexes_into_project(monkeypatch, tmp_path):
    sessions = _load_sessions_module(monkeypatch)
    captured = {}
    paper = types.SimpleNamespace(
        paper_id="paper-1",
        title="Space-Time Beamforming",
        authors=["Ada Lovelace"],
        parser="grobid-tei",
    )
    ingestion = types.SimpleNamespace(
        paper=paper,
        chunks=[types.SimpleNamespace(chunk_id="chunk-1")],
        artifact=types.SimpleNamespace(
            manifest_path=str(tmp_path / "canonical_paper.json"),
            evidence_preview_path=str(tmp_path / "evidence_preview.md"),
        ),
    )

    async def fake_index_ingestion_result(**kwargs):
        captured["index"] = kwargs
        return types.SimpleNamespace(
            paper_id="paper-1",
            chunk_count=1,
            evidence_record_count=1,
            embedding_count=1,
            embedding_model="local-hashing-v1",
        )

    def fake_ingest_uploaded_paper(**kwargs):
        captured["ingest"] = kwargs
        return ingestion

    monkeypatch.setattr(sessions, "_WORKSPACE_DIR", str(tmp_path))
    monkeypatch.setattr(sessions, "is_research_document", lambda path: True)
    monkeypatch.setattr(sessions, "ingest_uploaded_paper", fake_ingest_uploaded_paper)
    monkeypatch.setattr(sessions, "index_ingestion_result", fake_index_ingestion_result)

    response = await sessions.upload_research_project_paper_for_user(
        "project-1",
        FakeUpload(),
        types.SimpleNamespace(id="user-1"),
    )

    assert captured["ingest"]["session_id"] == "research-library-project-1"
    assert captured["ingest"]["user_id"] == "user-1"
    assert captured["ingest"]["workspace_dir"] == tmp_path / "research_library" / "project-1"
    assert captured["ingest"]["paper_id_namespace"] == "project:project-1"
    assert captured["index"]["project_id"] == "project-1"
    assert response.data["project_id"] == "project-1"
    assert response.data["evidence_scope"] == "project"
    assert response.data["temporary"] is False
    assert response.data["paper_id"] == "paper-1"
    assert response.data["status"] == "indexed"
    assert response.data["citation_ready"] is True


@pytest.mark.asyncio
async def test_set_session_research_project_route_persists_binding(monkeypatch):
    sessions = _load_sessions_module(monkeypatch)
    session = FakeSession()
    captured = {}

    async def fake_get_session(session_id):
        assert session_id == "session-1"
        return session

    async def fake_upsert(database_url, **kwargs):
        captured["database_url"] = database_url
        captured.update(kwargs)
        return FakeProject(project_id=kwargs["project_id"])

    monkeypatch.setattr(sessions, "async_get_science_session", fake_get_session)
    monkeypatch.setattr(sessions, "upsert_session_research_project_in_database", fake_upsert)

    response = await sessions.set_session_research_project_for_user(
        "session-1",
        sessions.SessionResearchProjectRequest(project_id="project-1"),
        types.SimpleNamespace(id="user-1"),
    )

    assert captured == {
        "database_url": sessions.settings.research_database_url,
        "session_id": "session-1",
        "project_id": "project-1",
        "user_id": "user-1",
    }
    assert response.data["project"]["project_id"] == "project-1"


@pytest.mark.asyncio
async def test_get_session_research_project_route_returns_binding(monkeypatch):
    sessions = _load_sessions_module(monkeypatch)
    session = FakeSession()

    async def fake_get_session(session_id):
        assert session_id == "session-1"
        return session

    async def fake_get_project(database_url, **kwargs):
        return FakeProject(project_id="project-1")

    monkeypatch.setattr(sessions, "async_get_science_session", fake_get_session)
    monkeypatch.setattr(sessions, "get_session_research_project_from_database", fake_get_project)

    response = await sessions.get_session_research_project_for_user(
        "session-1",
        types.SimpleNamespace(id="user-1"),
    )

    assert response.data["project"]["project_id"] == "project-1"


@pytest.mark.asyncio
async def test_runtime_result_audit_lists_persisted_process_trace_summaries(monkeypatch):
    sessions = _load_sessions_module(monkeypatch)
    session = FakeSession()
    session.events = [
        {
            "event": "tool",
            "data": {
                "event_id": "evt-call",
                "timestamp": 10,
                "tool_call_id": "tool-1",
                "name": "paper_lookup",
                "function": "paper_lookup",
                "status": "calling",
            },
        },
        {
            "event": "tool",
            "data": {
                "event_id": "evt-called",
                "timestamp": 11,
                "tool_call_id": "tool-1",
                "name": "paper_lookup",
                "function": "paper_lookup",
                "status": "called",
                "runtime_result_summary": {
                    "kind": "json",
                    "preview": {"title": "Evidence boundaries"},
                    "truncated": False,
                    "result_sha256": "abc123",
                    "context_boundary": "process_trace",
                    "citation_evidence": False,
                    "tool_pack": {
                        "id": "literature",
                        "label": "Literature",
                        "research_workflow": "Literature management",
                    },
                },
            },
        },
        {
            "event": "message",
            "data": {
                "event_id": "evt-message",
                "timestamp": 12,
                "role": "assistant",
                "content": "done",
            },
        },
    ]

    async def fake_get_session(session_id):
        assert session_id == "session-1"
        return session

    monkeypatch.setattr(sessions, "async_get_science_session", fake_get_session)

    response = await sessions.list_runtime_result_audit_for_session(
        "session-1",
        types.SimpleNamespace(id="user-1"),
    )

    assert response.data["session_id"] == "session-1"
    assert response.data["runtime_result_count"] == 1
    item = response.data["runtime_results"][0]
    assert item["event_id"] == "evt-called"
    assert item["tool_call_id"] == "tool-1"
    assert item["function"] == "paper_lookup"
    assert item["status"] == "called"
    assert item["summary"]["result_sha256"] == "abc123"
    assert item["summary"]["context_boundary"] == "process_trace"
    assert item["summary"]["citation_evidence"] is False


@pytest.mark.asyncio
async def test_runtime_result_audit_filters_and_exports_process_trace_manifest(monkeypatch):
    sessions = _load_sessions_module(monkeypatch)
    session = FakeSession()
    session.events = [
        {
            "event": "tool",
            "data": {
                "event_id": "evt-literature",
                "timestamp": 11,
                "tool_call_id": "tool-1",
                "name": "paper_lookup",
                "function": "paper_lookup",
                "status": "called",
                "runtime_result_summary": {
                    "kind": "json",
                    "preview": {"title": "Evidence boundaries"},
                    "truncated": False,
                    "result_sha256": "hash-literature",
                    "context_boundary": "process_trace",
                    "citation_evidence": False,
                    "tool_pack": {
                        "id": "literature",
                        "label": "Literature",
                        "research_workflow": "Literature management",
                    },
                },
            },
        },
        {
            "event": "tool",
            "data": {
                "event_id": "evt-audit",
                "timestamp": 12,
                "tool_call_id": "tool-2",
                "name": "audit_claims",
                "function": "audit_claims",
                "status": "called",
                "runtime_result_summary": {
                    "kind": "json",
                    "preview": {"status": "unsupported"},
                    "truncated": False,
                    "result_sha256": "hash-audit",
                    "context_boundary": "process_trace",
                    "citation_evidence": False,
                    "tool_pack": {
                        "id": "evidence-audit",
                        "label": "Evidence Audit",
                        "research_workflow": "Evidence audit",
                    },
                },
            },
        },
    ]

    async def fake_get_session(session_id):
        assert session_id == "session-1"
        return session

    monkeypatch.setattr(sessions, "async_get_science_session", fake_get_session)

    response = await sessions.list_runtime_result_audit_for_session(
        "session-1",
        types.SimpleNamespace(id="user-1"),
        tool_pack_id="literature",
        result_sha256="hash-literature",
    )

    assert response.data["runtime_result_count"] == 1
    assert response.data["runtime_results"][0]["event_id"] == "evt-literature"
    assert response.data["export_manifest"] == {
        "format": "runtime_result_audit.v1",
        "session_id": "session-1",
        "runtime_result_count": 1,
        "filters": {
            "tool_pack_id": "literature",
            "result_sha256": "hash-literature",
        },
        "context_boundary": "process_trace",
        "citation_evidence": False,
        "event_ids": ["evt-literature"],
    }


@pytest.mark.asyncio
async def test_runtime_result_audit_export_writes_process_trace_artifact(monkeypatch, tmp_path):
    sessions = _load_sessions_module(monkeypatch)
    session = FakeSession(vm_root_dir=tmp_path)
    session.events = [
        {
            "event": "tool",
            "data": {
                "event_id": "evt-literature",
                "timestamp": 11,
                "tool_call_id": "tool-1",
                "name": "paper_lookup",
                "function": "paper_lookup",
                "status": "called",
                "runtime_result_summary": {
                    "kind": "json",
                    "preview": {"title": "Evidence boundaries"},
                    "truncated": False,
                    "result_sha256": "hash-literature",
                    "context_boundary": "process_trace",
                    "citation_evidence": False,
                    "tool_pack": {"id": "literature", "label": "Literature"},
                },
            },
        }
    ]
    published = []

    async def fake_get_session(session_id):
        assert session_id == "session-1"
        return session

    monkeypatch.setattr(sessions, "async_get_science_session", fake_get_session)
    monkeypatch.setattr(sessions, "_publish_session_event", lambda *args: published.append(args))

    response = await sessions.export_runtime_result_audit_for_session(
        "session-1",
        sessions.RuntimeResultAuditExportRequest(
            tool_pack_id="literature",
            result_sha256="hash-literature",
        ),
        types.SimpleNamespace(id="user-1"),
    )

    artifact_path = Path(response.data["artifact_path"])
    assert artifact_path.is_file()
    assert artifact_path.parent == tmp_path
    assert artifact_path.name.startswith("runtime-result-audit-")
    assert artifact_path.name.endswith(".json")
    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert payload["context_boundary"] == "process_trace"
    assert payload["citation_evidence"] is False
    assert payload["export_manifest"]["filters"] == {
        "tool_pack_id": "literature",
        "result_sha256": "hash-literature",
    }
    assert payload["runtime_results"][0]["event_id"] == "evt-literature"
    assert response.data["round_files"][0]["filename"] == artifact_path.name
    assert any(
        event.get("event") == "step"
        and event.get("data", {}).get("status") == "completed"
        and event.get("data", {}).get("metadata", {}).get("context_boundary") == "process_trace"
        and event.get("data", {}).get("metadata", {}).get("citation_evidence") is False
        for event in session.events
    )
    assert session.save_count == 1
    assert published


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
async def test_research_web_evidence_ingest_warns_for_non_https_source(monkeypatch):
    sessions = _load_sessions_module(monkeypatch)
    session = FakeSession()

    async def fake_get_session(session_id):
        assert session_id == "session-1"
        return session

    async def fake_persist_web_evidence_source(database_url, **kwargs):
        return FakeStorageSummary(
            paper_id=kwargs["source_id"],
            chunk_count=len(kwargs["chunks"]),
            evidence_record_count=len(kwargs["chunks"]),
        )

    monkeypatch.setattr(sessions, "async_get_science_session", fake_get_session)
    monkeypatch.setattr(sessions, "persist_web_evidence_source_to_database", fake_persist_web_evidence_source)
    monkeypatch.setattr(sessions, "_publish_session_event", lambda *args, **kwargs: None)

    response = await sessions.ingest_web_evidence_for_session(
        "session-1",
        sessions.WebEvidenceIngestRequest(
            url="http://example.com/research",
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

    assert response.data["source_quality"]["status"] == "citation_grade"
    assert response.data["source_quality"]["quality_warnings"] == ["url_not_https"]
    completed_step = session.events[-1]["data"]
    assert completed_step["metadata"]["source_quality"]["quality_warnings"] == ["url_not_https"]


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
                    "memory_status": "conflict",
                    "conflicts_with": ["mem-2"],
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
    assert response.data["context_memory_conflict_count"] == 1
    assert response.data["context_memory"][0]["source_type"] == "memory"
    assert response.data["context_memory"][0]["context_only"] is True

    completed_steps = [
        event["data"]
        for event in session.events
        if event.get("event") == "step" and event.get("data", {}).get("status") == "completed"
    ]
    assert completed_steps[-1]["metadata"]["citation_count"] == 1
    assert completed_steps[-1]["metadata"]["context_memory_count"] == 1
    assert completed_steps[-1]["metadata"]["context_memory_conflict_count"] == 1
    assert completed_steps[-1]["metadata"]["context_boundaries"] == {
        "citation_evidence": ["paper", "web", "database"],
        "context_only_memory": ["memory"],
        "process_trace": ["tool_logs", "runtime_results", "agent_lifecycle"],
        "model_reasoning": ["model_reasoning"],
    }
    assert completed_steps[-1]["metadata"]["evidence_admission"]["decision"] == "accepted"
    assert completed_steps[-1]["metadata"]["evidence_admission"]["accepted_count"] == 1
    assert completed_steps[-1]["metadata"]["task_route"]["route"] == "evidence_qa"
    assert completed_steps[-1]["metadata"]["task_route"]["scope"] == "project_or_session"
    assistant_research = session.events[-1]["data"]["metadata"]["research_assistant"]
    assert assistant_research["citations"][0]["source_type"] == "paper"
    assert assistant_research["context_memory"][0]["source_type"] == "memory"
    assert assistant_research["context_memory_conflict_count"] == 1
    assert assistant_research["evidence_admission"]["decision"] == "accepted"
    assert assistant_research["task_route"]["route"] == "evidence_qa"


@pytest.mark.asyncio
async def test_research_answer_trace_names_skipped_admission_without_claiming_retrieval(monkeypatch):
    sessions = _load_sessions_module(monkeypatch)
    session = FakeSession()

    async def fake_get_session(session_id):
        assert session_id == "session-1"
        return session

    async def fake_answer(*args, **kwargs):
        return ResearchAnswer(
            content="This turn does not require citation evidence retrieval.",
            citations=[],
            admission=skipped_admission_result(),
        )

    async def fake_persist_audit(*args, **kwargs):
        return None

    monkeypatch.setattr(sessions, "async_get_science_session", fake_get_session)
    monkeypatch.setattr(sessions, "answer_research_question", fake_answer)
    monkeypatch.setattr(sessions, "persist_audit_result_to_database", fake_persist_audit)
    monkeypatch.setattr(sessions, "_publish_session_event", lambda *args, **kwargs: None)

    await sessions.answer_research_question_for_session(
        "session-1",
        sessions.ResearchAnswerRequest(question="谢谢"),
        types.SimpleNamespace(id="user-1"),
    )

    step_events = [event["data"] for event in session.events if event.get("event") == "step"]
    assert step_events[0]["description"] == "Checking whether citation evidence is needed"
    assert step_events[-1]["description"] == "Citation evidence retrieval skipped"
    assert step_events[-1]["metadata"]["evidence_admission"]["decision"] == "skipped"
    assert step_events[-1]["metadata"]["citation_count"] == 0


@pytest.mark.asyncio
async def test_research_answer_trace_names_whole_paper_summary_workflow(monkeypatch):
    sessions = _load_sessions_module(monkeypatch)
    session = FakeSession()

    async def fake_get_session(session_id):
        assert session_id == "session-1"
        return session

    async def fake_answer(*args, **kwargs):
        return ResearchAnswer(
            content="Whole-paper summary based on citation evidence.",
            citations=[],
            task_route=ResearchTaskRoute(
                route="whole_paper_summary",
                decision_source="rule",
                needs_retrieval=True,
                scope="current_paper",
                confidence=0.95,
                reason="whole_paper_summary_intent",
            ),
        )

    async def fake_persist_audit(*args, **kwargs):
        return None

    monkeypatch.setattr(sessions, "async_get_science_session", fake_get_session)
    monkeypatch.setattr(sessions, "answer_research_question", fake_answer)
    monkeypatch.setattr(sessions, "persist_audit_result_to_database", fake_persist_audit)
    monkeypatch.setattr(sessions, "_publish_session_event", lambda *args, **kwargs: None)

    await sessions.answer_research_question_for_session(
        "session-1",
        sessions.ResearchAnswerRequest(question="请总结这篇论文"),
        types.SimpleNamespace(id="user-1"),
    )

    step_events = [event["data"] for event in session.events if event.get("event") == "step"]
    assert step_events[-1]["description"] == "Whole-paper summary evidence prepared"
    assert step_events[-1]["metadata"]["task_route"]["route"] == "whole_paper_summary"


@pytest.mark.asyncio
async def test_research_answer_uses_requested_model_config_for_llm_synthesis(monkeypatch):
    sessions = _load_sessions_module(monkeypatch)
    session = FakeSession()
    answer_kwargs = {}
    saved_sessions = []

    async def fake_get_session(session_id):
        assert session_id == "session-1"
        return session

    async def fake_get_model_config(model_config_id):
        assert model_config_id == "model-deepseek"
        return types.SimpleNamespace(
            model_dump=lambda: {
                "id": "model-deepseek",
                "model_name": "deepseek-chat",
                "provider": "openai-compatible",
            }
        )

    async def fake_save():
        session.save_count += 1
        saved_sessions.append(session)

    session.save = fake_save

    async def fake_answer(*args, **kwargs):
        answer_kwargs.update(kwargs)
        return ResearchAnswer(
            content="Whole-paper LLM synthesis completed.",
            citations=[],
            summary_synthesis={
                "mode": "llm_section_global",
                "intermediate_boundary": "context_only",
                "citation_source": "original_evidence",
            },
            task_route=ResearchTaskRoute(
                route="whole_paper_summary",
                decision_source="rule",
                needs_retrieval=True,
                scope="current_paper",
                confidence=0.95,
                reason="whole_paper_summary_intent",
            ),
        )

    async def fake_persist_audit(*args, **kwargs):
        return None

    monkeypatch.setattr(sessions, "async_get_science_session", fake_get_session)
    monkeypatch.setattr(sessions, "get_model_config", fake_get_model_config)
    monkeypatch.setattr(sessions, "answer_research_question", fake_answer)
    monkeypatch.setattr(sessions, "persist_audit_result_to_database", fake_persist_audit)
    monkeypatch.setattr(sessions, "_publish_session_event", lambda *args, **kwargs: None)

    await sessions.answer_research_question_for_session(
        "session-1",
        sessions.ResearchAnswerRequest(
            question="Please summarize this paper.",
            model_config_id="model-deepseek",
        ),
        types.SimpleNamespace(id="user-1"),
    )

    assert answer_kwargs["model_config"] == {
        "id": "model-deepseek",
        "model_name": "deepseek-chat",
        "provider": "openai-compatible",
    }
    assert session.model_config == answer_kwargs["model_config"]
    assert saved_sessions
    assert all(saved_session is session for saved_session in saved_sessions)
    step_events = [event["data"] for event in session.events if event.get("event") == "step"]
    assert step_events[-1]["description"] == "Whole-paper LLM synthesis completed"


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
async def test_research_report_passes_user_id_for_cross_session_memory_recall(monkeypatch, tmp_path):
    sessions = _load_sessions_module(monkeypatch)
    session = FakeSession(vm_root_dir=tmp_path)
    report_kwargs = {}

    async def fake_get_session(session_id):
        assert session_id == "session-1"
        return session

    async def fake_report(**kwargs):
        report_kwargs.update(kwargs)
        report_dir = tmp_path / "research_reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        markdown_path = report_dir / "report.md"
        evidence_path = report_dir / "report.evidence.json"
        markdown_path.write_text("# Report\n", encoding="utf-8")
        evidence_path.write_text("{}", encoding="utf-8")
        return types.SimpleNamespace(
            report_id="report-1",
            title="Report",
            question=kwargs["question"],
            markdown_path=str(markdown_path),
            evidence_map_path=str(evidence_path),
            citation_count=0,
            to_dict=lambda: {
                "report_id": "report-1",
                "title": "Report",
                "question": kwargs["question"],
                "markdown_path": str(markdown_path),
                "evidence_map_path": str(evidence_path),
                "citation_count": 0,
            },
        )

    monkeypatch.setattr(sessions, "async_get_science_session", fake_get_session)
    monkeypatch.setattr(sessions, "generate_markdown_research_report", fake_report)
    monkeypatch.setattr(sessions, "_publish_session_event", lambda *args, **kwargs: None)

    await sessions.generate_research_report_for_session(
        "session-1",
        sessions.ResearchReportRequest(question="What should the report remember?"),
        types.SimpleNamespace(id="user-1"),
    )

    assert report_kwargs["session_id"] == "session-1"
    assert report_kwargs["user_id"] == "user-1"


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
    published = []

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
    monkeypatch.setattr(sessions, "_publish_session_event", lambda *args: published.append(args))

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
    assert session.save_count == 1
    memory_step = session.events[-1]["data"]
    assert memory_step["status"] == "completed"
    assert memory_step["description"] == "Context-only research memory saved"
    assert memory_step["metadata"] == {
        "memory_id": response.data["memory_id"],
        "layer": "l2",
        "source_type": "memory",
        "context_only": True,
        "citation_evidence": False,
        "promotion_reason": "approved_audit_claim",
        "subject_type": "answer",
        "subject_id": "answer-1",
        "evidence_ids": [17],
        "duplicate": False,
    }
    assert published[-1] == ("session-1", "user-1", session.events[-1])


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
    published = []

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
    monkeypatch.setattr(sessions, "_publish_session_event", lambda *args: published.append(args))

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
    assert session.save_count == 1
    memory_step = session.events[-1]["data"]
    assert memory_step["status"] == "completed"
    assert memory_step["description"] == "Context-only research memory forgotten"
    assert memory_step["metadata"] == {
        "memory_id": "mem-1",
        "source_type": "memory",
        "context_only": True,
        "citation_evidence": False,
        "deleted": True,
    }
    assert published[-1] == ("session-1", "user-1", session.events[-1])


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
        reader_summary = {
            "status": "All audited claims are approved by citation evidence.",
            "evidence_basis": "2 citation evidence records from uploaded papers only.",
            "memory_boundary": "No context-only memory was used.",
            "next_action": "Use the Evidence-Grounded Answer, then inspect Claim Checks and Citation Evidence before reuse.",
        }
        return types.SimpleNamespace(
            report_id="report-1",
            title="Evidence Boundary Note",
            question="Summarize the evidence",
            markdown_path=str(tmp_path / "research_reports" / "report-1.md"),
            evidence_map_path=str(tmp_path / "research_reports" / "report-1.evidence.json"),
            citation_count=2,
            reader_summary=reader_summary,
            to_dict=lambda: {
                "report_id": "report-1",
                "title": "Evidence Boundary Note",
                "question": "Summarize the evidence",
                "markdown_path": str(tmp_path / "research_reports" / "report-1.md"),
                "evidence_map_path": str(tmp_path / "research_reports" / "report-1.evidence.json"),
                "citation_count": 2,
                "reader_summary": reader_summary,
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
    assert assistant_messages[-1]["metadata"]["research_assistant"]["context_boundaries"] == {
        "citation_evidence": ["paper", "web", "database"],
        "context_only_memory": ["memory"],
        "process_trace": ["tool_logs", "runtime_results", "agent_lifecycle"],
        "model_reasoning": ["model_reasoning"],
    }
    assert assistant_messages[-1]["metadata"]["research_assistant"]["report"]["reader_summary"] == {
        "status": "All audited claims are approved by citation evidence.",
        "evidence_basis": "2 citation evidence records from uploaded papers only.",
        "memory_boundary": "No context-only memory was used.",
        "next_action": "Use the Evidence-Grounded Answer, then inspect Claim Checks and Citation Evidence before reuse.",
    }
    assert response.data["citation_count"] == 2
    assert response.data["reader_summary"]["evidence_basis"] == "2 citation evidence records from uploaded papers only."
    assert response.data["context_boundaries"] == {
        "citation_evidence": ["paper", "web", "database"],
        "context_only_memory": ["memory"],
        "process_trace": ["tool_logs", "runtime_results", "agent_lifecycle"],
        "model_reasoning": ["model_reasoning"],
    }
    completed_steps = [
        event["data"]
        for event in session.events
        if event.get("event") == "step" and event.get("data", {}).get("status") == "completed"
    ]
    assert completed_steps[-1]["metadata"]["context_boundaries"] == {
        "citation_evidence": ["paper", "web", "database"],
        "context_only_memory": ["memory"],
        "process_trace": ["tool_logs", "runtime_results", "agent_lifecycle"],
        "model_reasoning": ["model_reasoning"],
    }
    assert completed_steps[-1]["metadata"]["reader_summary"]["next_action"].startswith("Use the Evidence-Grounded Answer")


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
    captured = {}

    def fake_ingest_uploaded_paper(**kwargs):
        captured["ingest"] = kwargs
        return ingestion

    monkeypatch.setattr(sessions, "ingest_uploaded_paper", fake_ingest_uploaded_paper)
    monkeypatch.setattr(sessions, "index_ingestion_result", fake_index_ingestion_result)
    monkeypatch.setattr(sessions, "_publish_session_event", lambda *args, **kwargs: None)

    response = await sessions.upload_session_file(
        "session-1",
        FakeUpload(),
        types.SimpleNamespace(id="user-1"),
    )

    assert response.data["metadata"]["research_assistant"]["status"] == "indexed"
    assert response.data["metadata"]["research_assistant"]["evidence_scope"] == "session"
    assert response.data["metadata"]["research_assistant"]["temporary"] is True
    assert response.data["metadata"]["research_assistant"]["project_id"] is None
    assert captured["ingest"]["paper_id_namespace"] == "session:session-1"
    assert session.status == sessions.SessionStatus.COMPLETED
    assert session.events[-1]["data"]["description"] == "Paper evidence indexed: paper.pdf"


@pytest.mark.asyncio
async def test_promote_chat_paper_to_library_reuses_library_indexing_path(monkeypatch, tmp_path):
    sessions = _load_sessions_module(monkeypatch)
    workspace = tmp_path / "workspace"
    source_dir = workspace / "session-1"
    source_dir.mkdir(parents=True)
    source_path = source_dir / "paper.pdf"
    source_path.write_bytes(b"%PDF-1.4\nfake")
    session = FakeSession(vm_root_dir=source_dir)
    captured = {}

    async def fake_get_session(session_id):
        assert session_id == "session-1"
        return session

    def fake_ingest_uploaded_paper(**kwargs):
        captured["ingest"] = kwargs
        paper = types.SimpleNamespace(
            paper_id="paper-1",
            title="Paper 1",
            authors=["Ada Lovelace"],
            parser="pdf-text",
        )
        return types.SimpleNamespace(
            paper=paper,
            chunks=[types.SimpleNamespace(chunk_id="chunk-1")],
            artifact=types.SimpleNamespace(
                manifest_path="/library/research_data/paper-1/canonical_paper.json",
                evidence_preview_path="/library/research_data/paper-1/evidence_preview.md",
            ),
        )

    async def fake_index_ingestion_result(**kwargs):
        captured["index"] = kwargs
        return types.SimpleNamespace(
            evidence_record_count=1,
            embedding_count=1,
            embedding_model="local-hashing-v1",
        )

    monkeypatch.setattr(sessions, "_WORKSPACE_DIR", str(workspace))
    monkeypatch.setattr(sessions, "async_get_science_session", fake_get_session)
    monkeypatch.setattr(sessions, "is_research_document", lambda path: True)
    monkeypatch.setattr(sessions, "ingest_uploaded_paper", fake_ingest_uploaded_paper)
    monkeypatch.setattr(sessions, "index_ingestion_result", fake_index_ingestion_result)
    monkeypatch.setattr(sessions, "_publish_session_event", lambda *args, **kwargs: None)

    response = await sessions.promote_session_paper_to_research_library(
        "session-1",
        sessions.ResearchLibraryPromotionRequest(
            project_id="project-1",
            sandbox_path=str(source_path),
        ),
        types.SimpleNamespace(id="user-1"),
    )

    library_workspace = workspace / "research_library" / "project-1"
    assert captured["ingest"]["file_path"] == library_workspace / "paper.pdf"
    assert captured["ingest"]["session_id"] == "research-library-project-1"
    assert captured["ingest"]["workspace_dir"] == library_workspace
    assert captured["ingest"]["paper_id_namespace"] == "project:project-1"
    assert captured["index"]["project_id"] == "project-1"
    assert response.data["project_id"] == "project-1"
    assert response.data["evidence_scope"] == "project"
    assert response.data["temporary"] is False
    assert response.data["source_session_id"] == "session-1"
    assert response.data["promotion_status"] == "indexed"
    assert response.data["citation_ready"] is True
    assert session.events[-1]["data"]["status"] == "completed"
    assert session.events[-1]["data"]["metadata"]["promotion_status"] == "indexed"


@pytest.mark.asyncio
async def test_promote_chat_paper_to_library_rejects_outside_session_workspace(monkeypatch, tmp_path):
    sessions = _load_sessions_module(monkeypatch)
    workspace = tmp_path / "workspace"
    source_dir = workspace / "session-1"
    source_dir.mkdir(parents=True)
    outside_path = tmp_path / "outside.pdf"
    outside_path.write_bytes(b"%PDF-1.4\nfake")
    session = FakeSession(vm_root_dir=source_dir)

    async def fake_get_session(session_id):
        assert session_id == "session-1"
        return session

    monkeypatch.setattr(sessions, "_WORKSPACE_DIR", str(workspace))
    monkeypatch.setattr(sessions, "async_get_science_session", fake_get_session)

    with pytest.raises(sessions.HTTPException) as excinfo:
        await sessions.promote_session_paper_to_research_library(
            "session-1",
            sessions.ResearchLibraryPromotionRequest(
                project_id="project-1",
                sandbox_path=str(outside_path),
            ),
            types.SimpleNamespace(id="user-1"),
        )

    assert excinfo.value.status_code == 400
    assert "session workspace" in excinfo.value.detail
