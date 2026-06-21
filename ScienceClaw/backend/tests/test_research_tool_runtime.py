from types import SimpleNamespace

import importlib
import sys
import types

import Tools
from backend.deepagent import agent
from backend.deepagent.sse_middleware import SSEMonitoringMiddleware


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
