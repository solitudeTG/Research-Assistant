from types import SimpleNamespace

import hashlib
import importlib
import json
import sys
import types

import pytest
import Tools
from backend.deepagent import agent
from backend.deepagent.sse_middleware import SSEMonitoringMiddleware
from backend.research_assistant.subagents import SubagentDefinition


def _tool(name: str, pack_id: str | None = None):
    metadata = {}
    if pack_id:
        metadata["tool_pack"] = {"id": pack_id, "label": pack_id.title()}
    return SimpleNamespace(name=name, metadata=metadata)


def test_collect_tools_does_not_expose_external_tools_without_active_pack(monkeypatch):
    monkeypatch.setattr(agent, "_STATIC_TOOLS", [])
    monkeypatch.setattr(
        agent,
        "reload_external_tools",
        lambda: [_tool("paper_lookup", "literature"), _tool("audit_claim", "evidence")],
    )

    tools = agent._collect_tools(blocked_tools=set())

    assert [tool.name for tool in tools] == []


def test_collect_tools_exposes_only_active_research_tool_pack(monkeypatch):
    monkeypatch.setattr(agent, "_STATIC_TOOLS", [])
    monkeypatch.setattr(
        agent,
        "reload_external_tools",
        lambda: [_tool("paper_lookup", "literature"), _tool("audit_claim", "evidence")],
    )

    tools = agent._collect_tools(blocked_tools=set(), active_tool_packs={"literature"})

    assert [tool.name for tool in tools] == ["paper_lookup"]


def test_supervisor_prompt_guides_autonomous_research_subagent_delegation():
    prompt = agent.get_system_prompt("/workspace")

    assert "## Research Subagent Delegation" in prompt
    assert "## Required Research Delegation" in prompt
    assert "## Research Delegation Trigger Matrix" in prompt
    assert "simple factual Q&A or casual chat" in prompt
    assert "Stay single-agent" in prompt
    assert "Simple factual Q&A or casual chat: stay single-agent" in prompt
    assert "Two-or-more-material synthesis: call Reader Worker first" in prompt
    assert "Boundary/audit/trust check: call Auditor after drafting" in prompt
    assert "Both synthesis and audit: Reader first, draft, then Auditor" in prompt
    assert "must delegate at least one scoped read" in prompt
    assert "must delegate an independent audit" in prompt
    assert "web_search`, `web_crawl`, reading files yourself, or writing todos do not satisfy" in prompt
    assert "Before finalizing a matching task" in prompt
    assert "When both reader and auditor criteria match" in prompt
    assert "Reader first, then draft, then Auditor" in prompt
    assert "Do not call Auditor before Reader for two-or-more-material synthesis" in prompt
    assert "Do not replace required delegation with repeated write_todos" in prompt
    assert "paper_reader_worker" in prompt
    assert "research_auditor" in prompt
    assert "Choose autonomously" in prompt
    assert "Do not ask the user to choose an Agent" in prompt
    assert "context_only or process_trace" in prompt
    assert "citation evidence" in prompt


def test_external_tool_proxy_carries_research_tool_pack_metadata(monkeypatch, tmp_path):
    tools_dir = tmp_path / "Tools"
    tools_dir.mkdir()
    (tools_dir / "paper_lookup.py").write_text(
        '@tool\n'
        'def paper_lookup(query: str) -> str:\n'
        '    """Look up paper metadata."""\n'
        '    return query\n',
        encoding="utf-8",
    )
    (tools_dir / "paper_lookup.meta.json").write_text(
        '{"tool_pack": {"id": "literature", "label": "Literature", "research_workflow": "文献管理"}}',
        encoding="utf-8",
    )

    monkeypatch.setattr(Tools, "_package_dir", str(tools_dir))

    proxies = Tools._scan_and_create_proxies()

    assert len(proxies) == 1
    assert proxies[0].metadata["tool_pack"]["id"] == "literature"


def test_external_tool_runtime_result_carries_contract_metadata(monkeypatch, tmp_path):
    tools_dir = tmp_path / "Tools"
    tools_dir.mkdir()
    (tools_dir / "paper_lookup.py").write_text(
        '@tool\n'
        'def paper_lookup(query: str) -> dict:\n'
        '    """Look up paper metadata."""\n'
        '    return {"title": query}\n',
        encoding="utf-8",
    )
    (tools_dir / "paper_lookup.meta.json").write_text(
        """
{
  "tool_name": "paper_lookup",
  "tool_pack": {"id": "literature", "label": "Literature"},
  "validation": {
    "result_contract": {
      "kind": "object",
      "schema": {
        "type": "object",
        "properties": {"title": {"type": "string"}},
        "required": ["title"]
      },
      "example_preview": {"title": "evidence boundaries"},
      "truncated": false
    }
  }
}
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setattr(Tools, "_package_dir", str(tools_dir))
    monkeypatch.setattr(
        Tools,
        "_execute_in_sandbox",
        lambda command: (
            "sandbox trace\n"
            f"{Tools._START_MARKER}\n"
            '{"title": "evidence boundaries"}\n'
            f"{Tools._END_MARKER}\n"
        ),
    )

    proxy = Tools._scan_and_create_proxies()[0]
    result = proxy.func(query="evidence boundaries")

    assert result["result"] == {"title": "evidence boundaries"}
    assert result["result_contract"]["kind"] == "object"
    assert result["result_contract"]["schema"]["properties"]["title"]["type"] == "string"
    assert result["tool_pack"]["id"] == "literature"


def test_tool_complete_trace_carries_runtime_result_contract_metadata():
    middleware = SSEMonitoringMiddleware(agent_name="DeepAgent")
    result_contract = {
        "kind": "object",
        "schema": {
            "type": "object",
            "properties": {"title": {"type": "string"}},
            "required": ["title"],
        },
        "example_preview": {"title": "evidence boundaries"},
        "truncated": False,
    }
    tool_pack = {"id": "literature", "label": "Literature"}

    middleware._after_tool(
        {
            "result": {"title": "evidence boundaries"},
            "result_contract": result_contract,
            "tool_pack": tool_pack,
        },
        "paper_lookup",
        {"query": "evidence boundaries"},
        "call-1",
        0,
        {"category": "custom"},
    )

    events = middleware.drain_events()
    complete_event = next(event for event in events if event["event"] == "middleware_tool_complete")

    assert complete_event["data"]["result_contract"] == result_contract
    assert complete_event["data"]["tool_pack"] == tool_pack


def test_tool_complete_trace_carries_auditable_runtime_result_summary():
    middleware = SSEMonitoringMiddleware(agent_name="DeepAgent")
    result_contract = {
        "kind": "object",
        "schema": {
            "type": "object",
            "properties": {"title": {"type": "string"}},
            "required": ["title"],
        },
        "example_preview": {"title": "evidence boundaries"},
        "truncated": False,
    }
    tool_pack = {"id": "literature", "label": "Literature"}

    middleware._after_tool(
        {
            "result": {"title": "evidence boundaries"},
            "result_contract": result_contract,
            "tool_pack": tool_pack,
        },
        "paper_lookup",
        {"query": "evidence boundaries"},
        "call-1",
        0,
        {"category": "custom"},
    )

    events = middleware.drain_events()
    complete_event = next(event for event in events if event["event"] == "middleware_tool_complete")
    expected_hash = hashlib.sha256(
        json.dumps({"title": "evidence boundaries"}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    assert complete_event["data"]["runtime_result_summary"] == {
        "kind": "object",
        "preview": {"title": "evidence boundaries"},
        "result_sha256": expected_hash,
        "truncated": False,
        "result_contract": result_contract,
        "tool_pack": tool_pack,
        "context_boundary": "process_trace",
        "citation_evidence": False,
    }


def test_task_tool_trace_carries_real_subagent_lifecycle_metadata():
    middleware = SSEMonitoringMiddleware(agent_name="DeepAgent")
    task_args = {
        "subagent_type": "paper_reader_worker",
        "description": "Read three selected papers",
    }

    _, _, _, start_time, tool_meta = middleware._before_tool(
        {"name": "task", "args": task_args, "id": "call-reader-1"}
    )
    start_event = middleware.drain_events()[0]

    assert start_event["data"]["subagent_lifecycle"] == {
        "workflow_id": "call-reader-1",
        "task_id": "call-reader-1",
        "parent_agent": "DeepAgent",
        "agent_name": "paper_reader_worker",
        "agent_role": "reader",
        "agent_type": "custom",
        "source": "registry",
        "phase": "started",
        "status": "running",
        "description": "Read three selected papers",
        "delegation_decision": {
            "decision_source": "supervisor_task_tool",
            "decision": "delegate",
            "trigger": "two_or_more_material_synthesis",
            "reason": "Reader Worker handles scoped reading before Supervisor synthesis.",
        },
        "output_boundary": "context_only",
        "citation_evidence": False,
    }

    middleware._after_tool("notes", "task", task_args, "call-reader-1", start_time, tool_meta)
    complete_event = middleware.drain_events()[0]

    assert complete_event["data"]["subagent_lifecycle"]["phase"] == "completed"
    assert complete_event["data"]["subagent_lifecycle"]["status"] == "completed"
    assert complete_event["data"]["subagent_lifecycle"]["agent_role"] == "reader"
    assert complete_event["data"]["subagent_lifecycle"]["parent_agent"] == "DeepAgent"


def test_task_tool_trace_labels_deepagents_builtin_subagent_metadata():
    middleware = SSEMonitoringMiddleware(agent_name="DeepAgent")
    task_args = {
        "subagent_type": "general-purpose",
        "description": "Handle a generic runtime task",
    }

    middleware._before_tool({"name": "task", "args": task_args, "id": "call-general-1"})
    start_event = middleware.drain_events()[0]

    assert start_event["data"]["subagent_lifecycle"] == {
        "workflow_id": "call-general-1",
        "task_id": "call-general-1",
        "parent_agent": "DeepAgent",
        "agent_name": "general-purpose",
        "agent_role": "general",
        "agent_type": "system_builtin",
        "source": "deepagents_builtin",
        "phase": "started",
        "status": "running",
        "description": "Handle a generic runtime task",
        "delegation_decision": {
            "decision_source": "supervisor_task_tool",
            "decision": "delegate",
            "trigger": "general_runtime_task",
            "reason": "DeepAgents runtime delegated a general-purpose task.",
        },
        "output_boundary": "process_trace",
        "citation_evidence": False,
    }


@pytest.mark.asyncio
async def test_runner_persists_real_subagent_lifecycle_runs(monkeypatch):
    async def unused_get_task_settings(*args, **kwargs):
        return SimpleNamespace()

    monkeypatch.setitem(
        sys.modules,
        "backend.deepagent.sessions",
        types.SimpleNamespace(ScienceSession=object),
    )
    monkeypatch.setitem(
        sys.modules,
        "backend.task_settings",
        types.SimpleNamespace(get_task_settings=unused_get_task_settings, TaskSettings=object),
    )
    sys.modules.pop("backend.deepagent.runner", None)
    runner = importlib.import_module("backend.deepagent.runner")
    calls = []

    async def fake_persist(database_url, **kwargs):
        calls.append((database_url, kwargs))

    monkeypatch.setattr(runner, "persist_subagent_run_to_database", fake_persist)

    await runner._persist_subagent_lifecycle_run(
        {
            "workflow_id": "workflow-1",
            "task_id": "task-1",
            "agent_name": "paper_reader_worker",
            "agent_role": "reader",
            "status": "completed",
            "output_boundary": "context_only",
            "citation_evidence": False,
            "evidence_refs": [{"evidence_id": 9, "source_type": "paper"}],
        },
        input_boundary={"description": "Read selected paper"},
        outputs={"result_summary": "notes"},
    )

    assert len(calls) == 1
    _, kwargs = calls[0]
    assert kwargs["task_id"] == "task-1"
    assert kwargs["parent_workflow_id"] == "workflow-1"
    assert kwargs["agent_name"] == "paper_reader_worker"
    assert kwargs["agent_role"] == "reader"
    assert kwargs["status"] == "completed"
    assert kwargs["input_boundary"] == {"description": "Read selected paper"}
    assert kwargs["output_boundary"] == "context_only"
    assert kwargs["evidence_refs"] == [{"evidence_id": 9, "source_type": "paper"}]
    assert kwargs["outputs"] == {"result_summary": "notes"}


def test_supervisor_guard_lifecycle_uses_explicit_decision_source(monkeypatch):
    async def unused_get_task_settings(*args, **kwargs):
        return SimpleNamespace()

    monkeypatch.setitem(
        sys.modules,
        "backend.deepagent.sessions",
        types.SimpleNamespace(ScienceSession=object),
    )
    monkeypatch.setitem(
        sys.modules,
        "backend.task_settings",
        types.SimpleNamespace(get_task_settings=unused_get_task_settings, TaskSettings=object),
    )
    sys.modules.pop("backend.deepagent.runner", None)
    runner = importlib.import_module("backend.deepagent.runner")

    lifecycle = runner._subagent_guard_lifecycle(
        agent_name="research_auditor",
        task_id="guard-audit-1",
        phase="started",
        status="running",
        description="Audit draft",
        decision={
            "trigger": "boundary_audit_or_trust_check",
            "reason": "audit required",
        },
    )

    assert lifecycle["agent_name"] == "research_auditor"
    assert lifecycle["delegation_decision"]["decision_source"] == "supervisor_delegation_guard"
    assert lifecycle["delegation_decision"]["trigger"] == "boundary_audit_or_trust_check"


@pytest.mark.asyncio
async def test_runner_builds_reader_scope_from_session_project_evidence(monkeypatch):
    from backend.deepagent import runner

    calls = []

    async def fake_get_project(database_url, *, session_id, user_id):
        calls.append(("project", database_url, session_id, user_id))
        return type("Project", (), {"project_id": "project-1"})()

    async def fake_list_scope(database_url, *, session_id, project_id, limit, per_paper_limit):
        calls.append(("scope", database_url, session_id, project_id, limit, per_paper_limit))
        return [
            {
                "evidence_id": 17,
                "chunk_id": "chunk-a",
                "paper_id": "paper-a",
                "title": "Paper A",
                "section": "Methods",
                "quote": "Paper A uses retrieval.",
                "source_type": "paper",
            },
            {
                "evidence_id": 18,
                "chunk_id": "chunk-b",
                "paper_id": "paper-b",
                "title": "Paper B",
                "section": "Results",
                "quote": "Paper B uses reranking.",
                "source_type": "paper",
            },
        ]

    monkeypatch.setattr(runner, "get_session_research_project_from_database", fake_get_project)
    monkeypatch.setattr(runner, "list_reader_scope_evidence_from_database", fake_list_scope)

    session = type("Session", (), {"session_id": "session-1", "user_id": "user-1"})()

    package = await runner._reader_material_package_for_session(
        session=session,
        query="请综合项目中的两篇论文并审计证据边界",
    )

    assert calls[0][0] == "project"
    assert calls[1] == (
        "scope",
        runner.settings.research_database_url,
        "session-1",
        "project-1",
        12,
        3,
    )
    assert package["reading_scope"] == {
        "scope_type": "session_or_project_evidence",
        "session_id": "session-1",
        "project_id": "project-1",
        "record_count": 2,
        "paper_count": 2,
    }
    assert package["records"][0]["paper_id"] == "paper-a"


def test_runner_task_calling_lifecycle_fallback_labels_deepagents_task(monkeypatch):
    async def unused_get_task_settings(*args, **kwargs):
        return SimpleNamespace()

    monkeypatch.setitem(
        sys.modules,
        "backend.deepagent.sessions",
        types.SimpleNamespace(ScienceSession=object),
    )
    monkeypatch.setitem(
        sys.modules,
        "backend.task_settings",
        types.SimpleNamespace(get_task_settings=unused_get_task_settings, TaskSettings=object),
    )
    sys.modules.pop("backend.deepagent.runner", None)
    runner = importlib.import_module("backend.deepagent.runner")

    lifecycle = runner._task_tool_lifecycle_from_args(
        tool_args={
            "subagent_type": "research_auditor",
            "description": "Audit draft",
        },
        tool_call_id="call-auditor-1",
        phase="started",
        status="running",
    )

    assert lifecycle["task_id"] == "call-auditor-1"
    assert lifecycle["agent_name"] == "research_auditor"
    assert lifecycle["phase"] == "started"
    assert lifecycle["delegation_decision"]["decision_source"] == "supervisor_task_tool"


@pytest.mark.asyncio
async def test_deep_agent_registers_governed_research_subagents(monkeypatch, tmp_path):
    captured = {}

    class FakeSandbox:
        def __init__(self, *, session_id: str, base_dir: str, **kwargs):
            self.workspace = str(tmp_path / session_id)
            (tmp_path / session_id).mkdir(parents=True, exist_ok=True)

        async def get_context(self):
            return {"success": False}

    def fake_create_deep_agent(**kwargs):
        captured["kwargs"] = kwargs
        return "compiled-agent"

    monkeypatch.setattr(agent, "FullSandboxBackend", FakeSandbox)
    monkeypatch.setattr(agent, "get_llm_model", lambda *args, **kwargs: SimpleNamespace(profile={"max_input_tokens": 4096}))
    monkeypatch.setattr(agent, "_collect_tools", lambda **kwargs: [])
    monkeypatch.setattr(agent, "_build_backend", lambda *args, **kwargs: "backend")
    monkeypatch.setattr(agent, "create_deep_agent", fake_create_deep_agent)
    monkeypatch.setattr(agent, "_WORKSPACE_DIR", str(tmp_path))
    monkeypatch.setattr(agent, "_BUILTIN_SKILLS_DIR", str(tmp_path / "missing-builtin"))
    monkeypatch.setattr(agent, "_EXTERNAL_SKILLS_DIR", str(tmp_path / "missing-external"))
    monkeypatch.setattr(agent._dir_watcher, "has_changed", lambda path: False)
    monkeypatch.setitem(
        sys.modules,
        "backend.task_settings",
        types.SimpleNamespace(TaskSettings=lambda: None),
    )

    result, _, context_window, _ = await agent.deep_agent(
        session_id="session-1",
        task_settings=SimpleNamespace(
            max_tokens=2048,
            sandbox_exec_timeout=30,
            max_output_chars=8000,
        ),
    )

    assert result == "compiled-agent"
    assert context_window == 4096
    subagents = captured["kwargs"]["subagents"]
    subagent_names = {subagent["name"] for subagent in subagents}
    assert subagent_names == {"research_auditor", "paper_reader_worker"}
    assert captured["kwargs"]["subagents"][0]["tools"]
    assert all(subagent["name"] != "general-purpose" for subagent in subagents)


@pytest.mark.asyncio
async def test_deep_agent_uses_enabled_registry_subagent_definitions(monkeypatch, tmp_path):
    captured = {}

    class FakeSandbox:
        def __init__(self, *, session_id: str, base_dir: str, **kwargs):
            self.workspace = str(tmp_path / session_id)
            (tmp_path / session_id).mkdir(parents=True, exist_ok=True)

        async def get_context(self):
            return {"success": False}

    async def fake_list_subagents(database_url, *, enabled_only):
        assert enabled_only is True
        return [
            SubagentDefinition(
                name="research_auditor",
                display_name="Auditor Agent",
                description="Edited auditor description from registry.",
                system_prompt="You are the edited Research Auditor Agent.",
                skill_refs=["research-evidence-audit"],
                allowed_tools=["audit_evidence_claims"],
                input_boundaries={"requires": ["answer_content", "citations"]},
                output_boundary="process_trace",
                can_answer_user=False,
                can_write_artifacts=False,
                enabled=True,
            )
        ]

    monkeypatch.setattr(agent, "FullSandboxBackend", FakeSandbox)
    monkeypatch.setattr(agent, "get_llm_model", lambda *args, **kwargs: SimpleNamespace(profile={"max_input_tokens": 4096}))
    monkeypatch.setattr(agent, "_collect_tools", lambda **kwargs: [])
    monkeypatch.setattr(agent, "_build_backend", lambda *args, **kwargs: "backend")
    def fake_create_deep_agent(**kwargs):
        captured["kwargs"] = kwargs
        return "compiled-agent"

    monkeypatch.setattr(agent, "create_deep_agent", fake_create_deep_agent)
    monkeypatch.setattr(agent, "ensure_subagent_definitions_in_database", lambda database_url: None)
    monkeypatch.setattr(agent, "list_subagent_definitions_from_database", fake_list_subagents)
    monkeypatch.setattr(agent, "_WORKSPACE_DIR", str(tmp_path))
    monkeypatch.setattr(agent, "_BUILTIN_SKILLS_DIR", str(tmp_path / "missing-builtin"))
    monkeypatch.setattr(agent, "_EXTERNAL_SKILLS_DIR", str(tmp_path / "missing-external"))
    monkeypatch.setattr(agent._dir_watcher, "has_changed", lambda path: False)
    monkeypatch.setitem(
        sys.modules,
        "backend.task_settings",
        types.SimpleNamespace(TaskSettings=lambda: None),
    )

    await agent.deep_agent(
        session_id="session-1",
        task_settings=SimpleNamespace(
            max_tokens=2048,
            sandbox_exec_timeout=30,
            max_output_chars=8000,
        ),
    )

    subagents = captured["kwargs"]["subagents"]
    assert [subagent["name"] for subagent in subagents] == ["research_auditor"]
    assert subagents[0]["description"] == "Edited auditor description from registry."


@pytest.mark.asyncio
async def test_deep_agent_exposes_bound_external_tool_to_registry_subagent(monkeypatch, tmp_path):
    captured = {}
    paper_lookup = SimpleNamespace(
        name="paper_lookup",
        description="Look up paper metadata.",
        metadata={"tool_pack": {"id": "literature", "label": "Literature"}},
    )

    class FakeSandbox:
        def __init__(self, *, session_id: str, base_dir: str, **kwargs):
            self.workspace = str(tmp_path / session_id)
            (tmp_path / session_id).mkdir(parents=True, exist_ok=True)

        async def get_context(self):
            return {"success": False}

    async def fake_list_subagents(database_url, *, enabled_only):
        assert enabled_only is True
        return [
            SubagentDefinition(
                name="methods_mapper",
                display_name="Methods Mapper",
                description="Map methods with a bound literature lookup tool.",
                system_prompt="Use only bound tools.",
                skill_refs=[],
                allowed_tools=["paper_lookup"],
                input_boundaries={"requires": ["question"]},
                output_boundary="process_trace",
                can_answer_user=False,
                can_write_artifacts=False,
                enabled=True,
                validation_status="passed",
            )
        ]

    def fake_create_deep_agent(**kwargs):
        captured["kwargs"] = kwargs
        return "compiled-agent"

    monkeypatch.setattr(agent, "FullSandboxBackend", FakeSandbox)
    monkeypatch.setattr(agent, "get_llm_model", lambda *args, **kwargs: SimpleNamespace(profile={"max_input_tokens": 4096}))
    monkeypatch.setattr(agent, "_collect_tools", lambda **kwargs: [])
    monkeypatch.setattr(agent, "_build_backend", lambda *args, **kwargs: "backend")
    monkeypatch.setattr(agent, "create_deep_agent", fake_create_deep_agent)
    monkeypatch.setattr(agent, "ensure_subagent_definitions_in_database", lambda database_url: None)
    monkeypatch.setattr(agent, "list_subagent_definitions_from_database", fake_list_subagents)
    monkeypatch.setattr(agent, "reload_external_tools", lambda force=False: [paper_lookup])
    monkeypatch.setattr(agent, "_WORKSPACE_DIR", str(tmp_path))
    monkeypatch.setattr(agent, "_BUILTIN_SKILLS_DIR", str(tmp_path / "missing-builtin"))
    monkeypatch.setattr(agent, "_EXTERNAL_SKILLS_DIR", str(tmp_path / "missing-external"))
    monkeypatch.setattr(agent._dir_watcher, "has_changed", lambda path: False)
    monkeypatch.setitem(
        sys.modules,
        "backend.task_settings",
        types.SimpleNamespace(TaskSettings=lambda: None),
    )

    await agent.deep_agent(
        session_id="session-1",
        task_settings=SimpleNamespace(
            max_tokens=2048,
            sandbox_exec_timeout=30,
            max_output_chars=8000,
        ),
        active_tool_packs=set(),
    )

    subagents = captured["kwargs"]["subagents"]
    assert [subagent["name"] for subagent in subagents] == ["methods_mapper"]
    assert subagents[0]["tools"] == [paper_lookup]


def test_chat_active_tool_packs_accept_only_research_packs(monkeypatch):
    async def unused_async(*args, **kwargs):
        raise AssertionError("unexpected ScienceClaw session dependency call")

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
        types.SimpleNamespace(get_current_user=lambda: None, require_user=lambda: None, User=object),
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
    sessions = importlib.import_module("backend.route.sessions")

    assert sessions._normalize_active_tool_packs(["literature", "evidence"]) == {
        "literature",
        "evidence",
    }

    try:
        sessions._normalize_active_tool_packs(["general"])
    except sessions.HTTPException as exc:
        assert exc.status_code == 400
        assert "research tool pack" in exc.detail
    else:
        raise AssertionError("invalid active tool pack should be rejected")
