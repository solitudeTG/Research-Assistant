"""
Sessions 路由。

路由：
  PUT    /sessions                          → 创建会话
  GET    /sessions                          → 会话列表
  GET    /sessions/shared/{session_id}      → 获取已分享会话（无需认证）
  GET    /sessions/{session_id}             → 会话详情
  DELETE /sessions/{session_id}             → 删除会话
  POST   /sessions/{session_id}/chat                      → 聊天（SSE）
  POST   /sessions/{session_id}/stop                      → 停止会话
  POST   /sessions/{session_id}/clear_unread_message_count → 清零未读消息计数
  POST   /sessions/{session_id}/share       → 开启分享
  DELETE /sessions/{session_id}/share       → 取消分享
  GET    /sessions/{session_id}/files       → 沙盒文件列表
  GET    /sessions/{session_id}/sandbox-file → 读取沙盒文件
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import shlex
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

import shutil
from pathlib import Path as _Path

import httpx
import yaml as _yaml

import shortuuid
from fastapi import APIRouter, HTTPException, Query, Request, Depends, UploadFile, File as FastAPIFile
from fastapi.responses import FileResponse, Response
from loguru import logger
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from langchain_core.messages import HumanMessage, SystemMessage

from backend.deepagent.engine import get_llm_model
from backend.deepagent.full_sandbox_backend import FullSandboxBackend
from backend.deepagent.runner import arun_science_task_stream
from backend.deepagent.sessions import (
    ScienceSessionNotFoundError,
    async_create_science_session,
    async_delete_science_session,
    async_get_science_session,
    async_list_science_sessions,
)
from backend.research_assistant.answering import answer_research_question
from backend.research_assistant.indexing import index_ingestion_result
from backend.research_assistant.ingestion import ingest_uploaded_paper, is_research_document
from backend.research_assistant.parsers import PaperParseError
from backend.research_assistant.reports import generate_markdown_research_report
from backend.research_assistant.tool_validation import tool_source_sha256, validate_staged_tool
from backend.research_assistant.storage.database import (
    delete_memory_entry_from_database,
    get_audit_result_from_database,
    get_evidence_record_from_database,
    get_research_session_status_from_database,
    list_memory_entries_from_database,
    persist_audit_result_to_database,
    persist_database_evidence_source_to_database,
    persist_memory_entry_to_database,
    persist_web_evidence_source_to_database,
)
from backend.user.dependencies import get_current_user, require_user, User
from backend.models import get_model_config
from backend.config import settings

router = APIRouter(prefix="/sessions", tags=["sessions"])


# ═══════════════════════════════════════════════════════════════════
# Pydantic Models
# ═══════════════════════════════════════════════════════════════════

class ApiResponse(BaseModel):
    code: int = Field(default=0, description="Business status code, 0 means success")
    msg: str = Field(default="ok", description="Business message")
    data: Any = Field(default=None, description="Response data")


class CreateSessionRequest(BaseModel):
    mode: str = Field(default="deep", description="Session mode")
    model_config_id: Optional[str] = Field(default=None, description="Model config ID")


class CreateSessionData(BaseModel):
    session_id: str = Field(..., description="Session ID")
    mode: str = Field(default="deep", description="Session mode")


class SessionStatus:
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"


class ListSessionItem(BaseModel):
    session_id: str = Field(..., description="Session ID")
    title: Optional[str] = Field(default=None, description="Session title")
    latest_message: Optional[str] = Field(default=None, description="Latest message content")
    latest_message_at: Optional[int] = Field(default=None, description="Latest message timestamp")
    status: str = Field(default=SessionStatus.PENDING, description="Session status")
    unread_message_count: int = Field(default=0, description="Unread message count")
    is_shared: bool = Field(default=False, description="Whether shared")
    mode: str = Field(default="deep", description="Session mode")
    pinned: bool = Field(default=False, description="Whether pinned")
    source: Optional[str] = Field(default=None, description="Session source (e.g. wechat, lark)")


class ListSessionData(BaseModel):
    sessions: List[ListSessionItem] = Field(..., description="Session list")


class GetSessionData(BaseModel):
    session_id: str = Field(..., description="Session ID")
    title: Optional[str] = Field(default=None, description="Session title")
    status: str = Field(default=SessionStatus.PENDING, description="Session status")
    events: List[Dict[str, Any]] = Field(default_factory=list, description="Session events list")
    is_shared: bool = Field(default=False, description="Whether shared")
    mode: str = Field(default="deep", description="Session mode")
    model_config_id: Optional[str] = Field(default=None, description="Model config ID")


class ChatRequest(BaseModel):
    message: str = Field(default="", description="User message content")
    timestamp: Optional[int] = Field(default=None, description="Message timestamp")
    event_id: Optional[str] = Field(default=None, description="Event ID")
    attachments: Optional[List[str]] = Field(default=None, description="Attachment path list")
    language: Optional[str] = Field(default=None, description="User interface language (e.g. 'zh', 'en')")
    model_config_id: Optional[str] = Field(default=None, description="Model config ID to use (overrides session default)")


class ResearchAnswerRequest(BaseModel):
    question: str = Field(..., description="Research question grounded in uploaded papers")
    limit: int = Field(default=5, ge=1, le=20, description="Maximum evidence chunks to cite")


class ResearchReportRequest(BaseModel):
    question: str = Field(..., description="Research question or note topic grounded in uploaded papers")
    limit: int = Field(default=8, ge=1, le=20, description="Maximum evidence chunks to include")


class WebEvidenceChunkRequest(BaseModel):
    section: str = Field(default="Web", min_length=1, description="Section or heading for this web evidence chunk")
    content: str = Field(..., min_length=1, description="Web evidence chunk content")
    quote: Optional[str] = Field(default=None, description="Citation quote to persist; defaults to content")


class WebEvidenceIngestRequest(BaseModel):
    url: str = Field(..., min_length=1, description="Source URL")
    title: str = Field(..., min_length=1, description="Source title")
    retrieved_at: Optional[str] = Field(default=None, description="ISO timestamp when the source was retrieved")
    chunks: List[WebEvidenceChunkRequest] = Field(..., min_length=1, description="Source-identified web evidence chunks")


class DatabaseEvidenceChunkRequest(BaseModel):
    section: str = Field(default="Database", min_length=1, description="Section or result grouping for this database evidence chunk")
    content: str = Field(..., min_length=1, description="Database evidence chunk content")
    quote: Optional[str] = Field(default=None, description="Citation quote to persist; defaults to content")


class DatabaseEvidenceIngestRequest(BaseModel):
    database_name: str = Field(..., min_length=1, description="Research database name")
    query: str = Field(..., min_length=1, description="Query or lookup that produced this source")
    title: str = Field(..., min_length=1, description="Source title")
    retrieved_at: Optional[str] = Field(default=None, description="ISO timestamp when the source was retrieved")
    chunks: List[DatabaseEvidenceChunkRequest] = Field(..., min_length=1, description="Source-identified database evidence chunks")


def _source_quality(source_type: str, identity: dict[str, Any]) -> dict[str, Any]:
    identity_fields = list(identity.keys())
    missing_fields = [field for field, value in identity.items() if not str(value or "").strip()]
    return {
        "status": "citation_grade" if not missing_fields else "identity_incomplete",
        "source_type": source_type,
        "identity_fields": identity_fields,
        "missing_fields": missing_fields,
    }


class ResearchMemoryPromotionRequest(BaseModel):
    subject_type: str = Field(..., pattern="^(answer|report)$", description="Audited research subject type")
    subject_id: str = Field(..., min_length=1, description="Audited answer or report id")
    claim_text: str = Field(..., min_length=1, description="Approved audit claim to promote into L2 memory")
    title: Optional[str] = Field(default=None, description="Optional memory title")


# ═══════════════════════════════════════════════════════════════════
# 内部辅助函数
# ═══════════════════════════════════════════════════════════════════

def _now_ts() -> int:
    return int(time.time())


def _new_event_id() -> str:
    return shortuuid.uuid()


def _wrap_event(event: str, data: Dict[str, Any]) -> Dict[str, Any]:
    return {"event": event, "data": data}


def _json_dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _session_to_list_item(session) -> ListSessionItem:
    return ListSessionItem(
        session_id=session.session_id,
        title=getattr(session, "title", None),
        latest_message=getattr(session, "latest_message", None),
        latest_message_at=getattr(session, "latest_message_at", None),
        status=getattr(session, "status", SessionStatus.PENDING),
        unread_message_count=getattr(session, "unread_message_count", 0),
        is_shared=getattr(session, "is_shared", False),
        mode=getattr(session, "mode", "deep"),
        pinned=getattr(session, "pinned", False),
        source=getattr(session, "source", None),
    )


def _append_session_event(session: Any, event: Dict[str, Any]) -> None:
    events = getattr(session, "events", None)
    if not isinstance(events, list):
        events = []
        setattr(session, "events", events)
    events.append(event)
    if event.get("event") == "message":
        data = event.get("data") or {}
        content = data.get("content")
        if isinstance(content, str) and content.strip():
            setattr(session, "latest_message", content)
            setattr(session, "latest_message_at", int(data.get("timestamp") or _now_ts()))


def _research_upload_step_event(
    *,
    step_id: str,
    status: str,
    description: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    data: Dict[str, Any] = {
        "event_id": _new_event_id(),
        "timestamp": _now_ts(),
        "status": status,
        "id": step_id,
        "description": description,
    }
    if metadata:
        data["metadata"] = metadata
    return _wrap_event("step", data)


def _find_approved_audit_claim(claims: list[dict[str, Any]], claim_text: str) -> dict[str, Any] | None:
    target = claim_text.strip()
    for claim in claims:
        if claim.get("status") == "approved" and str(claim.get("claim_text", "")).strip() == target:
            return claim
    return None


def _memory_title_from_claim(claim_text: str) -> str:
    title = " ".join(claim_text.strip().split())
    if len(title) <= 80:
        return title
    return f"{title[:77]}..."


def _find_matching_memory_entry(memories: list[Any], *, subject_type: str, subject_id: str, claim_text: str) -> Any | None:
    target = " ".join(claim_text.strip().split())
    for memory in memories:
        content = " ".join(str(getattr(memory, "content", "")).strip().split())
        if (
            getattr(memory, "source_subject_type", None) == subject_type
            and getattr(memory, "source_subject_id", None) == subject_id
            and content == target
        ):
            return memory
    return None


def _publish_session_event(session_id: str, user_id: str, event: Dict[str, Any]) -> None:
    try:
        from backend.notifications import publish as _notify

        _notify("session_updated", {
            "session_id": session_id,
            "user_id": user_id,
            "session_event": event,
        })
    except Exception:
        logger.debug("Failed to publish session event", exc_info=True)


async def _append_save_publish_session_event(
    session: Any,
    *,
    session_id: str,
    user_id: str,
    event: Dict[str, Any],
) -> None:
    _append_session_event(session, event)
    await session.save()
    _publish_session_event(session_id, user_id, event)


def _count_user_messages(events: List[Dict[str, Any]]) -> int:
    """Count message events with role=user."""
    if not events:
        return 0
    return sum(
        1 for ev in events
        if ev.get("event") == "message" and (ev.get("data") or {}).get("role") == "user"
    )


async def _generate_session_title(first_message: str) -> str:
    """
    Use LLM to generate a short, descriptive chat title from the first user message.
    Returns a fallback if generation fails.
    """
    if not (first_message and first_message.strip()):
        return ""
    prompt = first_message.strip()
    if len(prompt) > 800:
        prompt = prompt[:800] + "..."
    system = (
        "You are a helper. Given the first user message of a chat conversation, "
        "reply with a very short summary to use as the chat title. "
        "Use at most 15 words. Reply in the same language as the user. "
        "Output only the title, no quotes, no explanation, no prefix."
    )
    try:
        llm = get_llm_model(config=None, max_tokens_override=60, streaming=False)
        response = await llm.ainvoke([
            SystemMessage(content=system),
            HumanMessage(content=prompt),
        ])
        title = (response.content or "").strip()
        if title and len(title) > 80:
            title = title[:80].rstrip()
        return title or ""
    except Exception as exc:
        logger.warning("session title generation failed: %s", exc)
        # Fallback: use first line or truncated message
        first_line = prompt.split("\n")[0].strip()
        return first_line[:50] if first_line else ""


# ── SSE 事件映射（runner 事件 → 前端事件）──

def _map_plan_to_steps(plan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    def _map_status(status: str) -> str:
        status = (status or "pending").strip()
        if status in {"in_progress", "running"}:
            return "running"
        if status == "completed":
            return "completed"
        if status in {"blocked", "failed"}:
            return "failed"
        return "pending"

    return [
        {
            "event_id": _new_event_id(),
            "timestamp": _now_ts(),
            "status": _map_status(str(step.get("status") or "pending")),
            "id": str(step.get("id") or ""),
            "description": str(step.get("content") or ""),
            "tools": step.get("tools") if isinstance(step.get("tools"), list) else [],
        }
        for step in plan
    ]


def _infer_tool_name(tool_function: str) -> str:
    func = (tool_function or "").strip()
    if func in {"web_search", "web_crawl", "internet_search"}:
        return "web_search"
    if func in {"sandbox_exec", "terminal_execute", "terminal_session",
                "sandbox_execute_bash", "sandbox_execute_code"}:
        return func
    if func in {"sandbox_write_file", "file_write", "sandbox_file_operations",
                "sandbox_str_replace_editor"}:
        return func
    if func in {"sandbox_read_file", "file_read"}:
        return func
    if func in {"sandbox_find_files", "file_list"}:
        return func
    if func in {"file_search"}:
        return "grep"
    if func in {"file_replace"}:
        return "edit_file"
    if func in {"terminal_kill"}:
        return "execute"
    if func in {"sandbox_get_context", "sandbox_get_packages", "sandbox_convert_to_markdown"}:
        return func
    if func.startswith("sandbox_browser_") or func == "sandbox_get_browser_info":
        return func
    if func.startswith("browser_"):
        return func
    if func.startswith("markitdown_"):
        return func
    if func in {"ls", "grep", "write", "read_file", "write_file", "edit_file"}:
        return func
    return func or "info"


def _normalize_tool_args(tool_function: str, args: Any, tool_call_id: str) -> Dict[str, Any]:
    if not isinstance(args, dict):
        return {}
    out = dict(args)
    func = (tool_function or "").strip()
    if func in {"read_file", "write_file", "edit_file", "sandbox_read_file", "sandbox_write_file",
                "file_read", "file_write", "file_replace"}:
        if "file" not in out and "file_path" in out:
            out["file"] = out.get("file_path")
    if func in {"execute", "sandbox_exec", "terminal_execute"}:
        out.setdefault("id", tool_call_id)
    return out


def _maybe_wrap_tool_content(
    tool_function: str, tool_args: Dict[str, Any], raw_content: Any, tool_call_id: str
) -> Any:
    func = (tool_function or "").strip()

    # 终端命令执行
    if func in {"execute", "sandbox_exec", "terminal_execute"}:
        if isinstance(raw_content, str):
            try:
                parsed = json.loads(raw_content)
            except (json.JSONDecodeError, TypeError):
                parsed = {"output": raw_content}
        elif isinstance(raw_content, dict):
            parsed = raw_content
        else:
            parsed = {"output": str(raw_content)}

        output = parsed.get("output", str(raw_content))
        command = tool_args.get("command", "")
        session_id = parsed.get("session_id", tool_call_id)
        return {
            "output": output,
            "session_id": session_id,
            "console": [{"ps1": "$", "command": command, "output": output}],
        }

    # 文件读取
    if func in {"read_file", "sandbox_read_file", "file_read"}:
        if isinstance(raw_content, str):
            try:
                parsed = json.loads(raw_content)
                return {"file": parsed.get("file", tool_args.get("file_path", "")), "content": parsed.get("content", "")}
            except (json.JSONDecodeError, TypeError):
                pass
        elif isinstance(raw_content, dict):
            return {"file": raw_content.get("file", tool_args.get("file_path", "")), "content": raw_content.get("content", "")}
        content = raw_content if isinstance(raw_content, str) else str(raw_content)
        return {"file": tool_args.get("file", tool_args.get("file_path", "")), "content": content}

    # 文件写入
    if func in {"write_file", "sandbox_write_file", "file_write"}:
        if isinstance(raw_content, str):
            try:
                parsed = json.loads(raw_content)
                return parsed
            except (json.JSONDecodeError, TypeError):
                pass
        return raw_content

    return raw_content


def _extract_tool_meta(data: Dict[str, Any]) -> Dict[str, Any]:
    """从 runner 事件中提取工具元数据（icon, category, description, sandbox 等）"""
    meta = data.get("tool_meta") or {}
    result: Dict[str, Any] = {
        "icon": meta.get("icon", ""),
        "category": meta.get("category", ""),
        "description": meta.get("description", ""),
    }
    if meta.get("sandbox"):
        result["sandbox"] = True
    return result


# ── 沙盒文件管理辅助函数 ──

_FILE_OP_TOOLS = {
    "sandbox_file_operations",
    "sandbox_str_replace_editor",
    "file_write",
    "sandbox_write_file",
}

_CODE_EXEC_TOOLS = {
    "sandbox_execute_bash",
    "sandbox_execute_code",
    "terminal_execute",
}

_OPEN_WRITE_RE = re.compile(
    r"""open\s*\(\s*(?P<q>['"])(?P<path>.+?)(?P=q)\s*,\s*(?P<q2>['"])(?P<mode>[wxa][+tb]*)(?P=q2)\s*\)"""
)


def _get_sandbox_rest_base() -> str:
    """Derive sandbox REST base URL from SANDBOX_MCP_URL."""
    mcp_url = os.environ.get("SANDBOX_MCP_URL", "http://sandbox:8080/mcp")
    return mcp_url.rsplit("/", 1)[0]


def _extract_sandbox_file_paths(events: List[Dict[str, Any]]) -> Set[str]:
    """Scan session events and extract file paths touched by sandbox tools."""
    paths: Set[str] = set()
    for ev in events:
        if ev.get("event") != "tool":
            continue
        data = ev.get("data") or {}
        func = (data.get("function") or "").strip()
        args = data.get("args") or {}

        if func in _FILE_OP_TOOLS:
            for key in ("path", "file_path", "file", "filename"):
                p = args.get(key)
                if isinstance(p, str) and p.strip():
                    paths.add(p.strip())
                    break

        if func in _CODE_EXEC_TOOLS:
            code = args.get("code") or args.get("command") or ""
            if isinstance(code, str):
                for m in _OPEN_WRITE_RE.finditer(code):
                    paths.add(m.group("path"))

    return paths


# ── 轮次文件快照 / diff ──

_ROUND_FILES_EXCLUDE_DIRS = {"_diagnostic", "tools_staging", "__pycache__", ".git"}
_ROUND_FILES_EXCLUDE_NAMES = {"CONTEXT.md", "planner.md", "AGENTS.md"}


def _snapshot_workspace_files(workspace_dir: _Path) -> Dict[str, float]:
    """Return {relative_path: mtime} for every file under *workspace_dir*."""
    snap: Dict[str, float] = {}
    if not workspace_dir.is_dir():
        return snap
    for fp in workspace_dir.rglob("*"):
        if not fp.is_file():
            continue
        try:
            rel = str(fp.relative_to(workspace_dir))
            snap[rel] = fp.stat().st_mtime
        except (OSError, ValueError):
            continue
    return snap


def _diff_workspace_files(
    pre: Dict[str, float],
    post: Dict[str, float],
    workspace_dir: _Path,
    session_id: str,
) -> List[Dict[str, Any]]:
    """Compare snapshots and return new/modified files, excluding system artefacts."""
    changed: List[Dict[str, Any]] = []
    for rel, mtime in post.items():
        top_dir = rel.split("/", 1)[0] if "/" in rel else ""
        if top_dir in _ROUND_FILES_EXCLUDE_DIRS:
            continue
        basename = rel.rsplit("/", 1)[-1]
        if basename in _ROUND_FILES_EXCLUDE_NAMES:
            continue
        if basename.startswith("."):
            continue

        prev_mtime = pre.get(rel)
        if prev_mtime is not None and prev_mtime >= mtime:
            continue

        fp = workspace_dir / rel
        try:
            stat = fp.stat()
            upload_date = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
            size = stat.st_size
        except OSError:
            continue

        category = "research_data" if top_dir == "research_data" else "output"
        abs_path = str(fp)
        changed.append({
            "file_id": abs_path,
            "filename": basename,
            "relative_path": rel,
            "size": size,
            "upload_date": upload_date,
            "file_url": f"/api/v1/sessions/{session_id}/sandbox-file/download?path={abs_path}",
            "category": category,
        })
    return changed


async def _sandbox_file_list(directory: str) -> List[Dict[str, Any]]:
    """Call sandbox REST API to list files in a directory."""
    base = _get_sandbox_rest_base()
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(f"{base}/v1/file/list", json={"path": directory})
        if resp.status_code != 200:
            return []
        body = resp.json()
        data = body.get("data", body)
        if isinstance(data, dict):
            return data.get("files", [])
        return data if isinstance(data, list) else []


async def _sandbox_file_read(file_path: str) -> Optional[str]:
    """Call sandbox REST API to read a file."""
    base = _get_sandbox_rest_base()
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(f"{base}/v1/file/read", json={"file": file_path})
        if resp.status_code != 200:
            return None
        body = resp.json()
        data = body.get("data", body)
        if isinstance(data, dict):
            return data.get("content", "")
        return str(data)


async def _verify_sandbox_files(paths: Set[str]) -> List[Dict[str, Any]]:
    """Verify which paths still exist in the sandbox and return FileInfo-compatible dicts."""
    dirs_to_scan: Dict[str, Set[str]] = {}
    for p in paths:
        parent = p.rsplit("/", 1)[0] if "/" in p else "/"
        dirs_to_scan.setdefault(parent, set()).add(p)

    existing_files: Dict[str, Dict[str, Any]] = {}
    for directory, expected_paths in dirs_to_scan.items():
        entries = await _sandbox_file_list(directory)
        for entry in entries:
            entry_path = entry.get("path", "")
            if entry_path in expected_paths:
                existing_files[entry_path] = entry

    results: List[Dict[str, Any]] = []
    now_iso = datetime.now(timezone.utc).isoformat()
    for p in sorted(paths):
        entry = existing_files.get(p)
        if entry is None:
            continue
        filename = entry.get("name", p.rsplit("/", 1)[-1] if "/" in p else p)
        mod_time = entry.get("modified_time", "")
        if mod_time and mod_time.isdigit():
            upload_date = datetime.fromtimestamp(int(mod_time), tz=timezone.utc).isoformat()
        else:
            upload_date = mod_time or now_iso
        results.append({
            "file_id": p,
            "filename": filename,
            "size": entry.get("size") or 0,
            "upload_date": upload_date,
            "content_type": "text/plain",
            "file_url": None,
            "metadata": {"sandbox_path": p},
        })
    return results


def _map_science_stream_to_agent_event(evt: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    将 runner 产生的事件映射为前端期望的 SSE 事件格式。

    runner 现在产生自包含的事件（已在 runner 层完成中间件数据合并），
    每个事件都带有完整的 tool_meta、duration_ms，无需额外缓存。
    """
    event_type = str(evt.get("event") or "")
    data = evt.get("data") or {}
    ts = _now_ts()

    if event_type == "thinking":
        return _wrap_event("thinking", {
            "event_id": _new_event_id(), "timestamp": ts,
            "content": data.get("content", ""),
        })

    if event_type in {"plan", "plan_update"}:
        plan = data.get("plan") or []
        if not isinstance(plan, list):
            return None
        return _wrap_event("plan", {"event_id": _new_event_id(), "timestamp": ts, "steps": _map_plan_to_steps(plan)})

    if event_type == "step_start":
        step = data.get("step") or {}
        return _wrap_event("step", {
            "event_id": _new_event_id(), "timestamp": ts,
            "status": "running",
            "id": str(step.get("id") or ""),
            "description": str(step.get("content") or ""),
        })

    if event_type == "step_end":
        return _wrap_event("step", {
            "event_id": _new_event_id(), "timestamp": ts,
            "status": "completed",
            "id": str(data.get("step_id") or ""),
            "description": "",
        })

    if event_type == "message_chunk":
        return _wrap_event("message_chunk", {
            "event_id": _new_event_id(), "timestamp": ts,
            "content": data.get("content", ""), "role": "assistant",
        })

    if event_type == "message_chunk_done":
        return _wrap_event("message_chunk_done", {
            "event_id": _new_event_id(), "timestamp": ts,
        })

    if event_type in {"planning_message", "step_message"}:
        content = data.get("content")
        if not isinstance(content, str):
            content = str(content)
        return _wrap_event("message", {
            "event_id": _new_event_id(), "timestamp": ts,
            "content": content, "role": "assistant", "attachments": [],
        })

    if event_type == "tool_call":
        tool_call_id = str(data.get("tool_call_id") or "")
        tool_function = str(data.get("function") or "")
        tool_args = _normalize_tool_args(tool_function, data.get("args") or {}, tool_call_id)
        tool_meta = _extract_tool_meta(data)
        return _wrap_event("tool", {
            "event_id": _new_event_id(), "timestamp": ts,
            "tool_call_id": tool_call_id,
            "name": _infer_tool_name(tool_function),
            "status": "calling",
            "function": tool_function,
            "args": tool_args,
            "tool_meta": tool_meta,
        })

    if event_type == "tool_result":
        tool_call_id = str(data.get("tool_call_id") or "")
        tool_function = str(data.get("function") or "")
        raw_args = data.get("args")
        # 只在有实际 args 时才 normalize，否则不发送 args（让前端保留 calling 的 args）
        tool_args = _normalize_tool_args(tool_function, raw_args or {}, tool_call_id) if raw_args else None
        content = _maybe_wrap_tool_content(tool_function, tool_args or {}, data.get("content"), tool_call_id)
        tool_meta = _extract_tool_meta(data)
        duration_ms = data.get("duration_ms")

        result = {
            "event_id": _new_event_id(), "timestamp": ts,
            "tool_call_id": tool_call_id,
            "name": _infer_tool_name(tool_function),
            "status": "called",
            "function": tool_function,
            "content": content,
            "duration_ms": duration_ms,
            "tool_meta": tool_meta,
        }
        # 只在有实际 args 时才包含，避免覆盖前端 calling 事件中保存的 args
        if tool_args:
            result["args"] = tool_args
        return _wrap_event("tool", result)

    if event_type == "statistics":
        return _wrap_event("statistics", data)

    if event_type == "error":
        message = data.get("message")
        if not isinstance(message, str):
            message = str(message)
        return _wrap_event("error", {"event_id": _new_event_id(), "timestamp": ts, "error": message})

    return None


# ═══════════════════════════════════════════════════════════════════
# 路由
# ═══════════════════════════════════════════════════════════════════

@router.put("", response_model=ApiResponse)
async def create_session(
    body: CreateSessionRequest = CreateSessionRequest(),
    current_user: User = Depends(require_user),
) -> ApiResponse:
    try:
        model_config_dict = None
        if body.model_config_id:
            mc = await get_model_config(body.model_config_id)
            if mc:
                if not mc.is_system and mc.user_id != current_user.id:
                    raise HTTPException(status_code=403, detail="Cannot use this model")
                model_config_dict = mc.model_dump()

        session = await async_create_science_session(
            mode=body.mode,
            user_id=current_user.id,
            model_config=model_config_dict,
        )
        return ApiResponse(data=CreateSessionData(session_id=session.session_id, mode=session.mode).model_dump())
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("create_session failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("", response_model=ApiResponse)
async def list_sessions(current_user: User = Depends(require_user)) -> ApiResponse:
    sessions = await async_list_science_sessions(user_id=current_user.id)
    items = [_session_to_list_item(s) for s in sessions]
    return ApiResponse(data=ListSessionData(sessions=items).model_dump())


@router.get("/shared/{session_id}", response_model=ApiResponse)
async def get_shared_session(session_id: str) -> ApiResponse:
    """获取已分享的会话（无需认证）"""
    try:
        session = await async_get_science_session(session_id)
        if not getattr(session, "is_shared", False):
            raise HTTPException(status_code=404, detail="Shared session not found")

        events = getattr(session, "events", []) or []
        return ApiResponse(data=GetSessionData(
            session_id=session.session_id,
            title=getattr(session, "title", None),
            status=getattr(session, "status", SessionStatus.PENDING),
            events=events,
            is_shared=True,
            mode=getattr(session, "mode", "deep"),
        ).model_dump())
    except ScienceSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Shared session not found") from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("get_shared_session failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ═══════════════════════════════════════════════════════════════════
# 外置 Skills 管理（必须放在 /{session_id} 路由之前，否则 "skills" 会被当作 session_id）
# ═══════════════════════════════════════════════════════════════════

from backend.mongodb.db import db as _db

_EXTERNAL_SKILLS_DIR = os.environ.get("EXTERNAL_SKILLS_DIR", "/app/Skills")
_BUILTIN_SKILLS_DIR = os.environ.get("BUILTIN_SKILLS_DIR", "/app/builtin_skills")
_WORKSPACE_DIR = os.environ.get("WORKSPACE_DIR", "/home/scienceclaw")


def _parse_skill_frontmatter(skill_dir: _Path) -> Dict[str, Any]:
    """从 SKILL.md 中解析 YAML front-matter 元数据。"""
    skill_md = skill_dir / "SKILL.md"
    result: Dict[str, Any] = {"name": skill_dir.name, "description": ""}
    if not skill_md.is_file():
        return result
    try:
        text = skill_md.read_text(encoding="utf-8", errors="replace")
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
        if match:
            fm = _yaml.safe_load(match.group(1))
            if isinstance(fm, dict):
                result["name"] = fm.get("name", skill_dir.name)
                result["description"] = fm.get("description", "")
    except Exception:
        pass
    return result


def _list_skill_dirs(base_dir: str, builtin: bool = False) -> List[Dict[str, Any]]:
    """列出指定目录中所有合法的 skill。"""
    base = _Path(base_dir)
    if not base.is_dir():
        return []
    skills = []
    for child in sorted(base.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        if not (child / "SKILL.md").is_file():
            continue
        meta = _parse_skill_frontmatter(child)
        files = [str(f.relative_to(child)) for f in child.rglob("*") if f.is_file()]
        skills.append({**meta, "files": files, "builtin": builtin})
    return skills


class SkillBlockRequest(BaseModel):
    blocked: bool = Field(default=True)


@router.get("/skills", response_model=ApiResponse)
async def list_skills(current_user: User = Depends(require_user)) -> ApiResponse:
    """列出所有 skills（内置排前面，不可屏蔽/删除）+ 外置 skills。"""
    try:
        builtin = _list_skill_dirs(_BUILTIN_SKILLS_DIR, builtin=True)
        external = _list_skill_dirs(_EXTERNAL_SKILLS_DIR, builtin=False)

        col = _db.get_collection("blocked_skills")
        blocked_docs = col.find({"user_id": current_user.id}, {"skill_name": 1})
        blocked_names: set = set()
        async for doc in blocked_docs:
            name = doc.get("skill_name")
            if name:
                blocked_names.add(name)

        for s in builtin:
            s["blocked"] = False
        for s in external:
            s["blocked"] = s["name"] in blocked_names

        return ApiResponse(data=builtin + external)
    except Exception as exc:
        logger.exception("list_skills failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.put("/skills/{skill_name}/block", response_model=ApiResponse)
async def toggle_block_skill(
    skill_name: str,
    body: SkillBlockRequest,
    current_user: User = Depends(require_user),
) -> ApiResponse:
    """屏蔽或取消屏蔽一个外置 skill。"""
    try:
        col = _db.get_collection("blocked_skills")
        filt = {"user_id": current_user.id, "skill_name": skill_name}
        if body.blocked:
            await col.update_one(filt, {"$set": filt}, upsert=True)
        else:
            await col.delete_one(filt)
        return ApiResponse(data={"skill_name": skill_name, "blocked": body.blocked})
    except Exception as exc:
        logger.exception("toggle_block_skill failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/skills/{skill_name}", response_model=ApiResponse)
async def delete_skill(
    skill_name: str,
    current_user: User = Depends(require_user),
) -> ApiResponse:
    """彻底删除一个外置 skill 目录。"""
    try:
        skill_path = _Path(_EXTERNAL_SKILLS_DIR) / skill_name
        if not skill_path.is_dir():
            raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")
        resolved = skill_path.resolve()
        base_resolved = _Path(_EXTERNAL_SKILLS_DIR).resolve()
        if not str(resolved).startswith(str(base_resolved)):
            raise HTTPException(status_code=403, detail="Invalid skill path")
        shutil.rmtree(resolved)
        col = _db.get_collection("blocked_skills")
        await col.delete_many({"skill_name": skill_name})
        return ApiResponse(data={"skill_name": skill_name, "deleted": True})
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("delete_skill failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


class SaveSkillRequest(BaseModel):
    skill_name: str = Field(..., description="Name of the skill to save")


@router.post("/{session_id}/skills/save", response_model=ApiResponse)
async def save_skill_from_session(
    session_id: str,
    body: SaveSkillRequest,
    current_user: User = Depends(require_user),
) -> ApiResponse:
    """Copy a skill from the session workspace to the permanent Skills directory."""
    try:
        session = await async_get_science_session(session_id)
        if session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        skill_name = body.skill_name.strip()
        if not skill_name or "/" in skill_name or "\\" in skill_name:
            raise HTTPException(status_code=400, detail="Invalid skill name")

        # Agent 可能将 skill 写在多种位置，按优先级检查
        candidate_paths = [
            _Path(_WORKSPACE_DIR) / session_id / ".agents" / "skills" / skill_name,
            _Path(_WORKSPACE_DIR) / session_id / "skills" / skill_name,
            _Path(_WORKSPACE_DIR) / session_id / skill_name,
        ]
        src = next(
            (p for p in candidate_paths if p.is_dir() and (p / "SKILL.md").is_file()),
            None,
        )

        dst = _Path(_EXTERNAL_SKILLS_DIR) / skill_name

        if src is None:
            # Agent 可能直接编辑了 /skills/ 目录下的已有 skill（in-place 编辑），
            # 此时 workspace 里没有副本，但 /skills/ 已经是最新版本
            if dst.is_dir() and (dst / "SKILL.md").is_file():
                logger.info(
                    f"[Skills] Skill '{skill_name}' not in workspace but already exists "
                    f"in {dst}, treating as in-place update"
                )
                return ApiResponse(data={"skill_name": skill_name, "saved": True})
            raise HTTPException(
                status_code=404,
                detail=f"Skill '{skill_name}' not found in session workspace "
                       f"(checked .agents/skills/, skills/, and {skill_name}/)",
            )

        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)

        logger.info(f"[Skills] Saved skill '{skill_name}' from session {session_id} to {dst}")
        return ApiResponse(data={"skill_name": skill_name, "saved": True})
    except ScienceSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("save_skill_from_session failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/skills/{skill_name}/files", response_model=ApiResponse)
async def list_skill_files(
    skill_name: str,
    path: str = "",
    current_user: User = Depends(require_user),
) -> ApiResponse:
    """列出某个外置 skill 内部的文件结构。"""
    try:
        skill_path = _Path(_EXTERNAL_SKILLS_DIR) / skill_name
        if not skill_path.is_dir():
            raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")
        target = skill_path / path if path else skill_path
        target_resolved = target.resolve()
        if not str(target_resolved).startswith(str(skill_path.resolve())):
            raise HTTPException(status_code=403, detail="Invalid path")
        if not target_resolved.is_dir():
            raise HTTPException(status_code=404, detail="Directory not found")
        items = []
        for child in sorted(target_resolved.iterdir()):
            if child.name.startswith("."):
                continue
            rel = str(child.relative_to(skill_path))
            items.append({
                "name": child.name,
                "path": rel,
                "type": "directory" if child.is_dir() else "file",
            })
        return ApiResponse(data=items)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("list_skill_files failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


class ReadSkillFileRequest(BaseModel):
    file: str


@router.post("/skills/{skill_name}/read", response_model=ApiResponse)
async def read_skill_file(
    skill_name: str,
    body: ReadSkillFileRequest,
    current_user: User = Depends(require_user),
) -> ApiResponse:
    """读取某个外置 skill 内的文件内容。"""
    try:
        skill_path = _Path(_EXTERNAL_SKILLS_DIR) / skill_name
        if not skill_path.is_dir():
            raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")
        file_path = (skill_path / body.file).resolve()
        if not str(file_path).startswith(str(skill_path.resolve())):
            raise HTTPException(status_code=403, detail="Invalid file path")
        if not file_path.is_file():
            raise HTTPException(status_code=404, detail="File not found")
        content = file_path.read_text(encoding="utf-8", errors="replace")
        return ApiResponse(data={"file": body.file, "content": content})
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("read_skill_file failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ═══════════════════════════════════════════════════════════════════
# 外置 Tools 管理（必须放在 /{session_id} 路由之前）
# ═══════════════════════════════════════════════════════════════════

_TOOLS_DIR = os.environ.get("TOOLS_DIR", "/app/Tools")


def _extract_tool_description(py_file: _Path) -> str:
    """从 Python 文件中提取 @tool 函数的首行 docstring。"""
    try:
        content = py_file.read_text(encoding="utf-8", errors="replace")
        match = re.search(r'@tool\s*\ndef\s+\w+\([^)]*\)[^:]*:\s*"""(.*?)"""', content, re.DOTALL)
        if match:
            return match.group(1).strip().split('\n')[0].strip()
    except Exception:
        pass
    return ""


def _read_tool_validation_payload(staging_dir: _Path, tool_name: str) -> Dict[str, Any] | None:
    validation_path = staging_dir / f"{tool_name}.validation.json"
    if not validation_path.is_file():
        return None
    try:
        payload = json.loads(validation_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get("tool_name") != tool_name:
        return None
    return payload


def _normalize_passed_tool_validation(
    payload: Dict[str, Any],
    *,
    source: str | None = None,
) -> Dict[str, Any] | None:
    if payload.get("status") != "passed":
        return None
    return_schema = payload.get("return_schema")
    if return_schema is None:
        return_schema = payload.get("result_schema")
    if not isinstance(return_schema, dict) or not return_schema:
        return None
    input_schema = payload.get("input_schema")
    if not isinstance(input_schema, dict) or not input_schema:
        return None
    result_contract = payload.get("result_contract")
    if not isinstance(result_contract, dict) or not result_contract:
        return None
    execution_environment = payload.get("execution_environment")
    if not isinstance(execution_environment, dict) or not execution_environment.get("type"):
        return None
    source_sha256 = payload.get("source_sha256")
    if not isinstance(source_sha256, str) or not source_sha256:
        return None
    if source is not None and source_sha256 != tool_source_sha256(source):
        return None
    checks = payload.get("checks")
    return {
        "status": "passed",
        "checks": checks if isinstance(checks, list) else [],
        "validated_at": str(payload.get("validated_at") or ""),
        "execution_environment": execution_environment,
        "source_sha256": source_sha256,
        "input_schema": input_schema,
        "return_schema": return_schema,
        "result_contract": result_contract,
    }


def _read_passed_tool_validation(staging_dir: _Path, tool_name: str) -> Dict[str, Any] | None:
    payload = _read_tool_validation_payload(staging_dir, tool_name)
    if payload is None:
        return None
    source_path = staging_dir / f"{tool_name}.py"
    source = source_path.read_text(encoding="utf-8", errors="replace") if source_path.is_file() else None
    return _normalize_passed_tool_validation(payload, source=source)


def _require_passed_tool_validation(staging_dir: _Path, tool_name: str) -> Dict[str, Any]:
    payload = _read_tool_validation_payload(staging_dir, tool_name)
    source_path = staging_dir / f"{tool_name}.py"
    source = source_path.read_text(encoding="utf-8", errors="replace") if source_path.is_file() else None
    validation = _normalize_passed_tool_validation(payload, source=source) if payload is not None else None
    if validation is None:
        if payload is not None and payload.get("status") == "passed":
            raise HTTPException(
                status_code=400,
                detail=_passed_tool_validation_failure_detail(payload, source=source),
            )
        raise HTTPException(
            status_code=400,
            detail="Tool must pass sandbox validation before it can be saved",
        )
    return validation


def _passed_tool_validation_failure_detail(payload: Dict[str, Any], *, source: str | None = None) -> str:
    return_schema = payload.get("return_schema") or payload.get("result_schema")
    if not isinstance(return_schema, dict) or not return_schema:
        return "Tool validation must include a non-empty return schema before it can be saved"
    input_schema = payload.get("input_schema")
    if not isinstance(input_schema, dict) or not input_schema:
        return "Tool validation must include a non-empty input schema before it can be saved"
    result_contract = payload.get("result_contract")
    if not isinstance(result_contract, dict) or not result_contract:
        return "Tool validation must include a result contract before it can be saved"
    execution_environment = payload.get("execution_environment")
    if not isinstance(execution_environment, dict) or not execution_environment.get("type"):
        return "Tool validation must include an execution environment before it can be saved"
    source_sha256 = payload.get("source_sha256")
    if not isinstance(source_sha256, str) or not source_sha256:
        return "Tool validation must include a source hash before it can be saved"
    if source is not None and source_sha256 != tool_source_sha256(source):
        return "Tool validation must match the current tool source before it can be saved"
    return "Tool must pass sandbox validation before it can be saved"


def _list_external_tools() -> List[Dict[str, Any]]:
    """列出 Tools 目录中所有外置工具（排除 __init__.py）。"""
    base = _Path(_TOOLS_DIR)
    if not base.is_dir():
        return []
    tools: List[Dict[str, Any]] = []
    for py_file in sorted(base.glob("*.py")):
        if py_file.name == "__init__.py":
            continue
        tools.append({
            "name": py_file.stem,
            "description": _extract_tool_description(py_file),
            "file": py_file.name,
        })
    return tools


class ToolBlockRequest(BaseModel):
    blocked: bool = Field(default=True)


@router.get("/tools", response_model=ApiResponse)
async def list_tools(current_user: User = Depends(require_user)) -> ApiResponse:
    """列出所有外置 tools，包含屏蔽状态。"""
    try:
        tools = _list_external_tools()
        col = _db.get_collection("blocked_tools")
        blocked_docs = col.find({"user_id": current_user.id}, {"tool_name": 1})
        blocked_names: set = set()
        async for doc in blocked_docs:
            name = doc.get("tool_name")
            if name:
                blocked_names.add(name)
        for t in tools:
            t["blocked"] = t["name"] in blocked_names
        return ApiResponse(data=tools)
    except Exception as exc:
        logger.exception("list_tools failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.put("/tools/{tool_name}/block", response_model=ApiResponse)
async def toggle_block_tool(
    tool_name: str,
    body: ToolBlockRequest,
    current_user: User = Depends(require_user),
) -> ApiResponse:
    """屏蔽或取消屏蔽一个外置 tool。"""
    try:
        col = _db.get_collection("blocked_tools")
        filt = {"user_id": current_user.id, "tool_name": tool_name}
        if body.blocked:
            await col.update_one(filt, {"$set": filt}, upsert=True)
        else:
            await col.delete_one(filt)
        return ApiResponse(data={"tool_name": tool_name, "blocked": body.blocked})
    except Exception as exc:
        logger.exception("toggle_block_tool failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/tools/{tool_name}", response_model=ApiResponse)
async def delete_tool(
    tool_name: str,
    current_user: User = Depends(require_user),
) -> ApiResponse:
    """彻底删除一个外置 tool 文件。"""
    try:
        tool_path = _Path(_TOOLS_DIR) / f"{tool_name}.py"
        if not tool_path.is_file():
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
        resolved = tool_path.resolve()
        base_resolved = _Path(_TOOLS_DIR).resolve()
        if not str(resolved).startswith(str(base_resolved)):
            raise HTTPException(status_code=403, detail="Invalid tool path")
        resolved.unlink()
        col = _db.get_collection("blocked_tools")
        await col.delete_many({"tool_name": tool_name})
        return ApiResponse(data={"tool_name": tool_name, "deleted": True})
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("delete_tool failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/tools/{tool_name}/read", response_model=ApiResponse)
async def read_tool_file(
    tool_name: str,
    current_user: User = Depends(require_user),
) -> ApiResponse:
    """读取一个外置 tool 的源码内容。"""
    try:
        tool_path = _Path(_TOOLS_DIR) / f"{tool_name}.py"
        if not tool_path.is_file():
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
        content = tool_path.read_text(encoding="utf-8", errors="replace")
        return ApiResponse(data={"file": f"{tool_name}.py", "content": content})
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("read_tool_file failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


class SaveToolRequest(BaseModel):
    tool_name: str = Field(..., description="Name of the tool to save (without .py extension)")
    replaces: str = Field("", description="If this tool replaces an existing tool with a different name, specify the old tool name here")
    user_confirmed: bool = Field(False, description="Whether the user explicitly confirmed permanent tool persistence")


class ValidateToolRequest(BaseModel):
    tool_name: str = Field(..., description="Name of the staged tool to validate (without .py extension)")
    example_args: Dict[str, Any] = Field(default_factory=dict, description="Example keyword arguments for a sandbox validation call")


def _tool_validation_runner_source(tool_name: str, example_args: Dict[str, Any]) -> str:
    return (
        "import json\n"
        "import sys\n"
        "from pathlib import Path\n\n"
        f"tool_name = {tool_name!r}\n"
        f"example_args = {json.dumps(example_args, ensure_ascii=False)!r}\n\n"
        "safe_builtins = {\n"
        "    'bool': bool, 'dict': dict, 'float': float, 'int': int, 'len': len,\n"
        "    'list': list, 'max': max, 'min': min, 'range': range, 'round': round,\n"
        "    'str': str, 'sum': sum,\n"
        "}\n"
        "namespace = {\n"
        "    '__builtins__': safe_builtins,\n"
        "    'tool': lambda fn=None, **_kwargs: fn if fn is not None else (lambda wrapped: wrapped),\n"
        "}\n"
        "try:\n"
        "    source = Path(__file__).with_name(f'{tool_name}.py').read_text(encoding='utf-8', errors='replace')\n"
        "    exec(compile(source, f'{tool_name}.py', 'exec'), namespace)\n"
        "    result = namespace[tool_name](**json.loads(example_args))\n"
        "    print(json.dumps({'status': 'passed', 'result': result}, ensure_ascii=False))\n"
        "except Exception as exc:\n"
        "    print(json.dumps({'status': 'failed', 'error': str(exc)}, ensure_ascii=False))\n"
        "    sys.exit(1)\n"
    )


def _parse_sandbox_validation_output(output: str) -> Dict[str, Any] | None:
    for line in reversed(str(output or "").splitlines()):
        text = line.strip()
        if not text:
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get("status") in {"passed", "failed"}:
            return payload
    return None


def _run_staged_tool_example_in_sandbox(
    *,
    session_id: str,
    user_id: str,
    staging_dir: _Path,
    tool_name: str,
    example_args: Dict[str, Any],
) -> tuple[Dict[str, Any], Dict[str, Any]] | None:
    if os.environ.get("SANDBOX_TOOL_VALIDATION") != "1" and not os.environ.get("SANDBOX_REST_URL"):
        return None

    runner_path = staging_dir / f".{tool_name}.validation_runner.py"
    sandbox = FullSandboxBackend(session_id, user_id)
    execution_environment = {
        "type": "sandbox_container",
        "backend": "full_sandbox",
        "sandbox_workspace": sandbox.workspace,
        "imports_allowed": False,
    }
    try:
        runner_path.write_text(
            _tool_validation_runner_source(tool_name, example_args),
            encoding="utf-8",
        )
        remote_runner = "/".join([
            str(sandbox.workspace).rstrip("/"),
            "tools_staging",
            runner_path.name,
        ])
        result = sandbox.execute(f"python {shlex.quote(remote_runner)}", timeout=30)
        parsed = _parse_sandbox_validation_output(getattr(result, "output", ""))
        if parsed is None:
            return None
        return parsed, execution_environment
    except Exception as exc:
        logger.warning(f"Sandbox tool validation unavailable for {tool_name}: {exc}")
        return None
    finally:
        try:
            runner_path.unlink(missing_ok=True)
        except OSError:
            pass


@router.post("/{session_id}/tools/validate", response_model=ApiResponse)
async def validate_tool_from_session(
    session_id: str,
    body: ValidateToolRequest,
    current_user: User = Depends(require_user),
) -> ApiResponse:
    """Run a reproducible validation check for a staged session tool."""
    try:
        session = await async_get_science_session(session_id)
        if session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        tool_name = body.tool_name.strip()
        if not tool_name or "/" in tool_name or "\\" in tool_name:
            raise HTTPException(status_code=400, detail="Invalid tool name")

        staging_dir = _Path(_WORKSPACE_DIR) / session_id / "tools_staging"
        sandbox_result = _run_staged_tool_example_in_sandbox(
            session_id=session_id,
            user_id=current_user.id,
            staging_dir=staging_dir,
            tool_name=tool_name,
            example_args=body.example_args,
        )
        if sandbox_result is not None:
            example_call_result, execution_environment = sandbox_result
            payload = validate_staged_tool(
                staging_dir,
                tool_name,
                example_args=body.example_args,
                example_call_result=example_call_result,
                example_check_name="sandbox_example_call",
                execution_environment=execution_environment,
            )
        else:
            payload = validate_staged_tool(staging_dir, tool_name, example_args=body.example_args)
        validation_status = str(payload.get("status", "failed"))
        trace_status = "completed" if validation_status == "passed" else "failed"
        metadata: Dict[str, Any] = {
            "tool_name": tool_name,
            "validation_status": validation_status,
            "checks": payload.get("checks", []),
        }
        if payload.get("execution_environment"):
            metadata["execution_environment"] = payload["execution_environment"]
        if payload.get("input_schema"):
            metadata["input_schema"] = payload["input_schema"]
        if payload.get("return_schema"):
            metadata["return_schema"] = payload["return_schema"]
        if payload.get("result_contract"):
            metadata["result_contract"] = payload["result_contract"]
        if payload.get("error"):
            metadata["error"] = payload["error"]

        await _append_save_publish_session_event(
            session,
            session_id=session_id,
            user_id=current_user.id,
            event=_research_upload_step_event(
                step_id=f"tool-validation-{tool_name}",
                status=trace_status,
                description=f"Custom tool validation {validation_status}: {tool_name}",
                metadata=metadata,
            ),
        )
        return ApiResponse(data=payload)
    except ScienceSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("validate_tool_from_session failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{session_id}/tools/save", response_model=ApiResponse)
async def save_tool_from_session(
    session_id: str,
    body: SaveToolRequest,
    current_user: User = Depends(require_user),
) -> ApiResponse:
    """Copy a tool from the session workspace to the permanent Tools directory."""
    try:
        session = await async_get_science_session(session_id)
        if session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        tool_name = body.tool_name.strip()
        if not tool_name or "/" in tool_name or "\\" in tool_name:
            raise HTTPException(status_code=400, detail="Invalid tool name")
        if body.user_confirmed is not True:
            raise HTTPException(status_code=400, detail="Tool save requires explicit user confirmation")

        staging_dir = _Path(_WORKSPACE_DIR) / session_id / "tools_staging"
        src = staging_dir / f"{tool_name}.py"
        if not src.is_file():
            raise HTTPException(
                status_code=404,
                detail=f"Tool '{tool_name}.py' not found in session workspace tools_staging/",
            )

        content = src.read_text(encoding="utf-8", errors="replace")
        if "@tool" not in content:
            raise HTTPException(
                status_code=400,
                detail="File does not contain a @tool decorated function",
            )

        validation = _require_passed_tool_validation(staging_dir, tool_name)
        dst = _Path(_TOOLS_DIR) / f"{tool_name}.py"
        shutil.copy2(src, dst)

        replaces = (body.replaces or "").strip()
        if replaces and replaces != tool_name:
            old_file = _Path(_TOOLS_DIR) / f"{replaces}.py"
            if old_file.is_file():
                old_file.unlink()
                logger.info(f"[Tools] Removed old tool '{replaces}.py' (replaced by '{tool_name}')")

        logger.info(f"[Tools] Saved tool '{tool_name}' from session {session_id} to {dst}")
        return ApiResponse(data={
            "tool_name": tool_name,
            "saved": True,
            "replaced": replaces or None,
            "validation": validation,
        })
    except ScienceSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("save_tool_from_session failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ═══════════════════════════════════════════════════════════════════
# 文件上传（保存到 session workspace，让 Agent 可以直接访问）
# ═══════════════════════════════════════════════════════════════════

@router.post("/{session_id}/upload", response_model=ApiResponse)
async def upload_session_file(
    session_id: str,
    file: UploadFile = FastAPIFile(...),
    current_user: User = Depends(require_user),
) -> ApiResponse:
    """Upload a file to session workspace (/home/scienceclaw/{session_id}/)."""
    try:
        session = await async_get_science_session(session_id)
        if session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        workspace_dir = _Path(_WORKSPACE_DIR) / session_id
        workspace_dir.mkdir(parents=True, exist_ok=True)
        workspace_dir.chmod(0o777)

        safe_filename = _Path(file.filename or "upload").name
        if not safe_filename or safe_filename in {".", ".."}:
            safe_filename = "upload"

        target_path = workspace_dir / safe_filename
        if target_path.exists():
            stem = target_path.stem
            suffix = target_path.suffix
            i = 1
            while target_path.exists():
                target_path = workspace_dir / f"{stem}_{i}{suffix}"
                i += 1

        content = await file.read()
        target_path.write_bytes(content)

        abs_path = str(target_path)
        stat = target_path.stat()
        logger.info(f"[Upload] Saved file to {abs_path} ({stat.st_size} bytes)")

        metadata: Dict[str, Any] = {"sandbox_path": abs_path, "session_id": session_id}
        if is_research_document(target_path):
            upload_step_id = f"research-upload-{_new_event_id()}"
            parse_step_id = f"research-parse-{_new_event_id()}"
            index_step_id = f"research-index-{_new_event_id()}"
            await _append_save_publish_session_event(
                session,
                session_id=session_id,
                user_id=current_user.id,
                event=_research_upload_step_event(
                    step_id=upload_step_id,
                    status="completed",
                    description=f"Research document uploaded: {target_path.name}",
                    metadata={"filename": target_path.name, "path": abs_path, "size": stat.st_size},
                ),
            )
            await _append_save_publish_session_event(
                session,
                session_id=session_id,
                user_id=current_user.id,
                event=_research_upload_step_event(
                    step_id=parse_step_id,
                    status="running",
                    description=f"Parsing research document: {target_path.name}",
                    metadata={"filename": target_path.name, "path": abs_path},
                ),
            )

            try:
                ingestion = ingest_uploaded_paper(
                    file_path=target_path,
                    session_id=session_id,
                    user_id=current_user.id,
                    workspace_dir=workspace_dir,
                )
                metadata["research_assistant"] = {
                    "status": "ingested",
                    "paper_id": ingestion.paper.paper_id,
                    "title": ingestion.paper.title,
                    "authors": ingestion.paper.authors,
                    "parser": ingestion.paper.parser,
                    "chunk_count": len(ingestion.chunks),
                    "manifest_path": ingestion.artifact.manifest_path,
                    "evidence_preview_path": ingestion.artifact.evidence_preview_path,
                }
                await _append_save_publish_session_event(
                    session,
                    session_id=session_id,
                    user_id=current_user.id,
                    event=_research_upload_step_event(
                        step_id=parse_step_id,
                        status="completed",
                        description=f"Research document parsed: {target_path.name}",
                        metadata=metadata["research_assistant"],
                    ),
                )
                await _append_save_publish_session_event(
                    session,
                    session_id=session_id,
                    user_id=current_user.id,
                    event=_research_upload_step_event(
                        step_id=index_step_id,
                        status="running",
                        description=f"Indexing paper evidence in PostgreSQL: {target_path.name}",
                        metadata={
                            "paper_id": ingestion.paper.paper_id,
                            "chunk_count": len(ingestion.chunks),
                            "embedding_model": settings.research_embedding_model,
                        },
                    ),
                )
                try:
                    indexing_summary = await index_ingestion_result(
                        database_url=settings.research_database_url,
                        result=ingestion,
                        embedding_dimensions=settings.research_embedding_dimensions,
                        embedding_model=settings.research_embedding_model,
                    )
                    metadata["research_assistant"].update(
                        {
                            "status": "indexed",
                            "stored_in": "postgresql",
                            "evidence_record_count": indexing_summary.evidence_record_count,
                            "embedding_count": indexing_summary.embedding_count,
                            "embedding_model": indexing_summary.embedding_model,
                        }
                    )
                    completed_event = _research_upload_step_event(
                        step_id=index_step_id,
                        status="completed",
                        description=f"Paper evidence indexed: {target_path.name}",
                        metadata=metadata["research_assistant"],
                    )
                except Exception as exc:
                    logger.exception("[ResearchAssistant] PostgreSQL indexing failed")
                    metadata["research_assistant"].update(
                        {
                            "status": "index_failed",
                            "stored_in": "filesystem_only",
                            "index_error": str(exc),
                        }
                    )
                    completed_event = _research_upload_step_event(
                        step_id=index_step_id,
                        status="failed",
                        description=f"Paper evidence indexing failed for {target_path.name}",
                        metadata=metadata["research_assistant"],
                    )
            except (NotImplementedError, PaperParseError) as exc:
                metadata["research_assistant"] = {
                    "status": "parser_unavailable",
                    "reason": str(exc),
                }
                completed_event = _research_upload_step_event(
                    step_id=parse_step_id,
                    status="completed",
                    description=f"Research parsing deferred for {target_path.name}: parser unavailable",
                    metadata=metadata["research_assistant"],
                )
            except Exception as exc:
                logger.exception("[ResearchAssistant] ingestion failed")
                metadata["research_assistant"] = {
                    "status": "failed",
                    "reason": str(exc),
                }
                completed_event = _research_upload_step_event(
                    step_id=parse_step_id,
                    status="failed",
                    description=f"Research document parsing failed for {target_path.name}",
                    metadata=metadata["research_assistant"],
                )

            await _append_save_publish_session_event(
                session,
                session_id=session_id,
                user_id=current_user.id,
                event=completed_event,
            )
            setattr(session, "status", SessionStatus.COMPLETED)
            await session.save()

        return ApiResponse(data={
            "file_id": abs_path,
            "filename": target_path.name,
            "size": stat.st_size,
            "upload_date": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            "content_type": file.content_type or "application/octet-stream",
            "file_url": f"/api/v1/sessions/{session_id}/sandbox-file/download?path={abs_path}",
            "metadata": metadata,
        })
    except ScienceSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("upload_session_file failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ═══════════════════════════════════════════════════════════════════
# Real-time session notifications (SSE)
# ═══════════════════════════════════════════════════════════════════

@router.post("/{session_id}/research/web-evidence", response_model=ApiResponse)
async def ingest_web_evidence_for_session(
    session_id: str,
    body: WebEvidenceIngestRequest,
    current_user: User = Depends(require_user),
) -> ApiResponse:
    """Persist source-identified web chunks as citation evidence for a research session."""
    try:
        session = await async_get_science_session(session_id)
        if session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        url = body.url.strip()
        title = body.title.strip()
        if not url:
            raise HTTPException(status_code=400, detail="url is required")
        if not title:
            raise HTTPException(status_code=400, detail="title is required")
        if not body.chunks:
            raise HTTPException(status_code=400, detail="At least one evidence chunk is required")

        retrieved_at = body.retrieved_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        source_quality = _source_quality("web", {
            "url": url,
            "title": title,
            "retrieved_at": retrieved_at,
        })
        source_id = f"web-{_new_event_id()}"
        chunks = [
            {
                "chunk_id": f"{source_id}:chunk-{index}",
                "section": chunk.section.strip() or "Web",
                "content": chunk.content.strip(),
                "quote": (chunk.quote.strip() if chunk.quote else chunk.content.strip()),
            }
            for index, chunk in enumerate(body.chunks, start=1)
        ]
        if any(not chunk["content"] for chunk in chunks):
            raise HTTPException(status_code=400, detail="Evidence chunk content is required")

        step_id = f"research-web-evidence-{_new_event_id()}"
        started_event = _research_upload_step_event(
            step_id=step_id,
            status="running",
            description="Indexing web citation evidence",
            metadata={
                "source_type": "web",
                "source_id": source_id,
                "url": url,
                "title": title,
                "chunk_count": len(chunks),
                "source_quality": source_quality,
            },
        )
        _append_session_event(session, started_event)
        _publish_session_event(session_id, current_user.id, started_event)

        try:
            summary = await persist_web_evidence_source_to_database(
                settings.research_database_url,
                session_id=session_id,
                user_id=current_user.id,
                source_id=source_id,
                url=url,
                title=title,
                retrieved_at=retrieved_at,
                chunks=chunks,
            )
        except Exception as exc:
            await _append_save_publish_session_event(
                session,
                session_id=session_id,
                user_id=current_user.id,
                event=_research_upload_step_event(
                    step_id=step_id,
                    status="failed",
                    description="Web citation evidence indexing failed",
                    metadata={
                        "source_type": "web",
                        "source_id": source_id,
                        "url": url,
                        "title": title,
                        "chunk_count": len(chunks),
                        "source_quality": source_quality,
                        "error": str(exc),
                    },
                ),
            )
            raise

        data = {
            "source_type": "web",
            "source_id": source_id,
            "url": url,
            "title": title,
            "retrieved_at": retrieved_at,
            "chunk_count": summary.chunk_count,
            "evidence_record_count": summary.evidence_record_count,
            "source_quality": source_quality,
        }
        setattr(session, "status", SessionStatus.COMPLETED)
        await _append_save_publish_session_event(
            session,
            session_id=session_id,
            user_id=current_user.id,
            event=_research_upload_step_event(
                step_id=step_id,
                status="completed",
                description="Web citation evidence indexed",
                metadata={
                    "source_type": "web",
                    "source_id": source_id,
                    "url": url,
                    "title": title,
                    "chunk_count": summary.chunk_count,
                    "evidence_record_count": summary.evidence_record_count,
                    "source_quality": source_quality,
                },
            ),
        )
        return ApiResponse(data=data)
    except ScienceSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("ingest_web_evidence_for_session failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{session_id}/research/database-evidence", response_model=ApiResponse)
async def ingest_database_evidence_for_session(
    session_id: str,
    body: DatabaseEvidenceIngestRequest,
    current_user: User = Depends(require_user),
) -> ApiResponse:
    """Persist source-identified database result chunks as citation evidence for a research session."""
    try:
        session = await async_get_science_session(session_id)
        if session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        database_name = body.database_name.strip()
        query = body.query.strip()
        title = body.title.strip()
        if not database_name:
            raise HTTPException(status_code=400, detail="database_name is required")
        if not query:
            raise HTTPException(status_code=400, detail="query is required")
        if not title:
            raise HTTPException(status_code=400, detail="title is required")
        if not body.chunks:
            raise HTTPException(status_code=400, detail="At least one evidence chunk is required")

        retrieved_at = body.retrieved_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        source_quality = _source_quality("database", {
            "database_name": database_name,
            "query": query,
            "title": title,
            "retrieved_at": retrieved_at,
        })
        source_id = f"database-{_new_event_id()}"
        chunks = [
            {
                "chunk_id": f"{source_id}:chunk-{index}",
                "section": chunk.section.strip() or "Database",
                "content": chunk.content.strip(),
                "quote": (chunk.quote.strip() if chunk.quote else chunk.content.strip()),
            }
            for index, chunk in enumerate(body.chunks, start=1)
        ]
        if any(not chunk["content"] for chunk in chunks):
            raise HTTPException(status_code=400, detail="Evidence chunk content is required")

        step_id = f"research-database-evidence-{_new_event_id()}"
        started_event = _research_upload_step_event(
            step_id=step_id,
            status="running",
            description="Indexing database citation evidence",
            metadata={
                "source_type": "database",
                "source_id": source_id,
                "database_name": database_name,
                "query": query,
                "title": title,
                "chunk_count": len(chunks),
                "source_quality": source_quality,
            },
        )
        _append_session_event(session, started_event)
        _publish_session_event(session_id, current_user.id, started_event)

        try:
            summary = await persist_database_evidence_source_to_database(
                settings.research_database_url,
                session_id=session_id,
                user_id=current_user.id,
                source_id=source_id,
                database_name=database_name,
                query=query,
                title=title,
                retrieved_at=retrieved_at,
                chunks=chunks,
            )
        except Exception as exc:
            await _append_save_publish_session_event(
                session,
                session_id=session_id,
                user_id=current_user.id,
                event=_research_upload_step_event(
                    step_id=step_id,
                    status="failed",
                    description="Database citation evidence indexing failed",
                    metadata={
                        "source_type": "database",
                        "source_id": source_id,
                        "database_name": database_name,
                        "query": query,
                        "title": title,
                        "chunk_count": len(chunks),
                        "source_quality": source_quality,
                        "error": str(exc),
                    },
                ),
            )
            raise

        data = {
            "source_type": "database",
            "source_id": source_id,
            "database_name": database_name,
            "query": query,
            "title": title,
            "retrieved_at": retrieved_at,
            "chunk_count": summary.chunk_count,
            "evidence_record_count": summary.evidence_record_count,
            "source_quality": source_quality,
        }
        setattr(session, "status", SessionStatus.COMPLETED)
        await _append_save_publish_session_event(
            session,
            session_id=session_id,
            user_id=current_user.id,
            event=_research_upload_step_event(
                step_id=step_id,
                status="completed",
                description="Database citation evidence indexed",
                metadata={
                    "source_type": "database",
                    "source_id": source_id,
                    "database_name": database_name,
                    "query": query,
                    "title": title,
                    "chunk_count": summary.chunk_count,
                    "evidence_record_count": summary.evidence_record_count,
                    "source_quality": source_quality,
                },
            ),
        )
        return ApiResponse(data=data)
    except ScienceSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("ingest_database_evidence_for_session failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{session_id}/research/answer", response_model=ApiResponse)
async def answer_research_question_for_session(
    session_id: str,
    body: ResearchAnswerRequest,
    current_user: User = Depends(require_user),
) -> ApiResponse:
    """Answer a question using only citation evidence from uploaded papers."""
    try:
        session = await async_get_science_session(session_id)
        if session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        user_event = _wrap_event("message", {
            "event_id": _new_event_id(),
            "timestamp": _now_ts(),
            "content": body.question,
            "role": "user",
            "attachments": [],
            "metadata": {"research_assistant": {"mode": "paper_evidence"}},
        })
        _append_session_event(session, user_event)
        _publish_session_event(session_id, current_user.id, user_event)

        step_id = f"research-answer-{_new_event_id()}"
        retrieval_started = _research_upload_step_event(
            step_id=step_id,
            status="running",
            description="Retrieving citation evidence from uploaded papers",
            metadata={"question": body.question, "limit": body.limit},
        )
        _append_session_event(session, retrieval_started)
        _publish_session_event(session_id, current_user.id, retrieval_started)

        try:
            answer = await answer_research_question(
                database_url=settings.research_database_url,
                session_id=session_id,
                user_id=current_user.id,
                question=body.question,
                embedding_dimensions=settings.research_embedding_dimensions,
                embedding_model=settings.research_embedding_model,
                limit=body.limit,
            )
            await persist_audit_result_to_database(
                settings.research_database_url,
                audit_id=f"{answer.answer_id}:audit",
                session_id=session_id,
                subject_type="answer",
                subject_id=answer.answer_id,
                audit=answer.audit,
            )
        except Exception as exc:
            await _append_save_publish_session_event(
                session,
                session_id=session_id,
                user_id=current_user.id,
                event=_research_upload_step_event(
                    step_id=step_id,
                    status="failed",
                    description="Citation evidence retrieval failed",
                    metadata={"question": body.question, "error": str(exc)},
                ),
            )
            raise

        retrieval_completed = _research_upload_step_event(
            step_id=step_id,
            status="completed",
            description="Citation evidence retrieval completed",
            metadata={
                "citation_count": answer.citation_count,
                "context_memory_count": answer.context_memory_count,
                "embedding_model": settings.research_embedding_model,
            },
        )
        _append_session_event(session, retrieval_completed)
        _publish_session_event(session_id, current_user.id, retrieval_completed)

        assistant_event = _wrap_event("message", {
            "event_id": _new_event_id(),
            "timestamp": _now_ts(),
            "content": answer.content,
            "role": "assistant",
            "attachments": [],
            "metadata": {"research_assistant": {**answer.to_dict(), "question": body.question}},
        })
        _append_session_event(session, assistant_event)
        _publish_session_event(session_id, current_user.id, assistant_event)
        await session.save()

        return ApiResponse(data=answer.to_dict())
    except ScienceSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("answer_research_question_for_session failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{session_id}/research/status", response_model=ApiResponse)
async def get_research_status_for_session(
    session_id: str,
    current_user: User = Depends(require_user),
) -> ApiResponse:
    """Return whether this session has indexed uploaded-paper evidence."""
    try:
        session = await async_get_science_session(session_id)
        if session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        status = await get_research_session_status_from_database(
            settings.research_database_url,
            session_id=session_id,
        )
        return ApiResponse(data=status.to_dict())
    except ScienceSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("get_research_status_for_session failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{session_id}/research/audit/{subject_type}/{subject_id}", response_model=ApiResponse)
async def get_research_audit_result_for_session(
    session_id: str,
    subject_type: str,
    subject_id: str,
    current_user: User = Depends(require_user),
) -> ApiResponse:
    """Return a persisted Evidence Audit result for a session answer or report."""
    try:
        if subject_type not in {"answer", "report"}:
            raise HTTPException(status_code=400, detail="subject_type must be 'answer' or 'report'")
        session = await async_get_science_session(session_id)
        if session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        audit_result = await get_audit_result_from_database(
            settings.research_database_url,
            session_id=session_id,
            subject_type=subject_type,
            subject_id=subject_id,
        )
        if audit_result is None:
            raise HTTPException(status_code=404, detail="Evidence audit result not found")
        return ApiResponse(data=audit_result.to_dict())
    except ScienceSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("get_research_audit_result_for_session failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{session_id}/research/memory/promote", response_model=ApiResponse)
async def promote_research_memory_for_session(
    session_id: str,
    body: ResearchMemoryPromotionRequest,
    current_user: User = Depends(require_user),
) -> ApiResponse:
    """Promote an approved audited claim into explicit context-only L2 memory."""
    try:
        session = await async_get_science_session(session_id)
        if session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        audit_result = await get_audit_result_from_database(
            settings.research_database_url,
            session_id=session_id,
            subject_type=body.subject_type,
            subject_id=body.subject_id,
        )
        if audit_result is None:
            raise HTTPException(status_code=404, detail="Evidence audit result not found")

        approved_claim = _find_approved_audit_claim(audit_result.claims, body.claim_text)
        if approved_claim is None:
            raise HTTPException(status_code=400, detail="Only approved audit claims can be promoted to memory")

        existing_memories = await list_memory_entries_from_database(
            settings.research_database_url,
            session_id=session_id,
            user_id=current_user.id,
            layer="L2",
            limit=100,
        )
        existing_memory = _find_matching_memory_entry(
            existing_memories,
            subject_type=body.subject_type,
            subject_id=body.subject_id,
            claim_text=body.claim_text,
        )
        if existing_memory is not None:
            data = existing_memory.to_context_dict()
            data.update(
                {
                    "session_id": getattr(existing_memory, "session_id", session_id),
                    "promotion_reason": "approved_audit_claim",
                    "evidence_ids": approved_claim.get("evidence_ids", []),
                    "created": False,
                    "duplicate": True,
                }
            )
            return ApiResponse(data=data)

        memory_id = f"research-memory-{_new_event_id()}"
        title = body.title or _memory_title_from_claim(body.claim_text)
        await persist_memory_entry_to_database(
            settings.research_database_url,
            memory_id=memory_id,
            session_id=session_id,
            user_id=current_user.id,
            layer="L2",
            title=title,
            content=body.claim_text,
            source_subject_type=body.subject_type,
            source_subject_id=body.subject_id,
        )
        return ApiResponse(
            data={
                "memory_id": memory_id,
                "session_id": session_id,
                "layer": "l2",
                "title": title,
                "content": body.claim_text,
                "source_type": "memory",
                "context_only": True,
                "source_subject_type": body.subject_type,
                "source_subject_id": body.subject_id,
                "promotion_reason": "approved_audit_claim",
                "evidence_ids": approved_claim.get("evidence_ids", []),
                "created": True,
                "duplicate": False,
            }
        )
    except ScienceSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("promote_research_memory_for_session failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/{session_id}/research/memory/{memory_id}", response_model=ApiResponse)
async def delete_research_memory_for_session(
    session_id: str,
    memory_id: str,
    current_user: User = Depends(require_user),
) -> ApiResponse:
    """Delete a session-scoped context-only research memory entry."""
    try:
        session = await async_get_science_session(session_id)
        if session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        deleted = await delete_memory_entry_from_database(
            settings.research_database_url,
            session_id=session_id,
            memory_id=memory_id,
        )
        if not deleted:
            raise HTTPException(status_code=404, detail="Research memory entry not found")

        return ApiResponse(
            data={
                "memory_id": memory_id,
                "session_id": session_id,
                "deleted": True,
                "source_type": "memory",
                "context_only": True,
            }
        )
    except ScienceSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("delete_research_memory_for_session failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{session_id}/research/evidence/{evidence_id}", response_model=ApiResponse)
async def get_research_evidence_record_for_session(
    session_id: str,
    evidence_id: int,
    current_user: User = Depends(require_user),
) -> ApiResponse:
    """Return inspectable citation evidence details for this session."""
    try:
        session = await async_get_science_session(session_id)
        if session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        evidence_record = await get_evidence_record_from_database(
            settings.research_database_url,
            session_id=session_id,
            evidence_id=evidence_id,
        )
        if evidence_record is None:
            raise HTTPException(status_code=404, detail="Citation evidence not found")
        return ApiResponse(data=evidence_record.to_dict())
    except ScienceSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("get_research_evidence_record_for_session failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{session_id}/research/report", response_model=ApiResponse)
async def generate_research_report_for_session(
    session_id: str,
    body: ResearchReportRequest,
    current_user: User = Depends(require_user),
) -> ApiResponse:
    """Generate a Markdown research artifact using only uploaded paper evidence."""
    try:
        session = await async_get_science_session(session_id)
        if session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        pre_file_snapshot = _snapshot_workspace_files(session.vm_root_dir)

        user_event = _wrap_event("message", {
            "event_id": _new_event_id(),
            "timestamp": _now_ts(),
            "content": f"Generate Markdown research report: {body.question}",
            "role": "user",
            "attachments": [],
            "metadata": {"research_assistant": {"mode": "markdown_report"}},
        })
        _append_session_event(session, user_event)
        _publish_session_event(session_id, current_user.id, user_event)

        step_id = f"research-report-{_new_event_id()}"
        report_started = _research_upload_step_event(
            step_id=step_id,
            status="running",
            description="Generating Markdown research artifact from uploaded paper evidence",
            metadata={"question": body.question, "limit": body.limit},
        )
        _append_session_event(session, report_started)
        _publish_session_event(session_id, current_user.id, report_started)

        try:
            report = await generate_markdown_research_report(
                database_url=settings.research_database_url,
                session_id=session_id,
                question=body.question,
                workspace_dir=session.vm_root_dir,
                embedding_dimensions=settings.research_embedding_dimensions,
                embedding_model=settings.research_embedding_model,
                limit=body.limit,
            )
        except Exception as exc:
            await _append_save_publish_session_event(
                session,
                session_id=session_id,
                user_id=current_user.id,
                event=_research_upload_step_event(
                    step_id=step_id,
                    status="failed",
                    description="Markdown research artifact generation failed",
                    metadata={"question": body.question, "error": str(exc)},
                ),
            )
            raise

        report_completed = _research_upload_step_event(
            step_id=step_id,
            status="completed",
            description="Markdown research artifact generated",
            metadata=report.to_dict(),
        )
        _append_session_event(session, report_completed)
        _publish_session_event(session_id, current_user.id, report_completed)

        post_file_snapshot = _snapshot_workspace_files(session.vm_root_dir)
        round_files = _diff_workspace_files(
            pre_file_snapshot,
            post_file_snapshot,
            session.vm_root_dir,
            session_id,
        )

        assistant_event = _wrap_event("message", {
            "event_id": _new_event_id(),
            "timestamp": _now_ts(),
            "content": (
                f"Generated Markdown research artifact `{report.title}` with "
                f"{report.citation_count} citation evidence records."
            ),
            "role": "assistant",
            "attachments": [],
            "metadata": {"research_assistant": {"report": report.to_dict()}},
        })
        _append_session_event(session, assistant_event)
        _publish_session_event(session_id, current_user.id, assistant_event)

        done_event = _wrap_event("done", {
            "event_id": _new_event_id(),
            "timestamp": _now_ts(),
            "statistics": {
                "citation_count": report.citation_count,
                "artifact_count": len(round_files),
            },
            "round_files": round_files,
        })
        _append_session_event(session, done_event)
        _publish_session_event(session_id, current_user.id, done_event)

        setattr(session, "status", SessionStatus.COMPLETED)
        await session.save()

        return ApiResponse(data={**report.to_dict(), "round_files": round_files})
    except ScienceSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("generate_research_report_for_session failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/notifications")
async def session_notifications(
    request: Request,
    current_user: User = Depends(require_user),
) -> EventSourceResponse:
    """SSE stream that pushes session_created / session_updated events."""
    from backend.notifications import subscribe, unsubscribe

    sub_id, events = await subscribe()
    user_id = current_user.id

    async def event_generator():
        try:
            async for event in events:
                if await request.is_disconnected():
                    break
                evt_data = event.get("data", {})
                if evt_data.get("user_id") and evt_data["user_id"] != user_id:
                    continue
                yield {
                    "event": event["event"],
                    "data": _json_dumps(evt_data),
                }
        except asyncio.CancelledError:
            pass
        finally:
            await unsubscribe(sub_id)

    return EventSourceResponse(event_generator())


# ═══════════════════════════════════════════════════════════════════
# Session CRUD（/{session_id} 路由必须在 /skills, /tools 之后）
# ═══════════════════════════════════════════════════════════════════

@router.get("/{session_id}", response_model=ApiResponse)
async def get_session(session_id: str, current_user: User = Depends(require_user)) -> ApiResponse:
    try:
        session = await async_get_science_session(session_id)
        if session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        events = getattr(session, "events", []) or []
        # 从 session.model_config 中提取 model_config_id
        mc = getattr(session, "model_config", None)
        mc_id = mc.get("id") if isinstance(mc, dict) else None
        return ApiResponse(data=GetSessionData(
            session_id=session.session_id,
            title=getattr(session, "title", None),
            status=getattr(session, "status", SessionStatus.PENDING),
            events=events,
            is_shared=getattr(session, "is_shared", False),
            mode=getattr(session, "mode", "deep"),
            model_config_id=mc_id,
        ).model_dump())
    except ScienceSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("get_session failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/{session_id}", response_model=ApiResponse)
async def remove_session(session_id: str, current_user: User = Depends(require_user)) -> ApiResponse:
    try:
        session = await async_get_science_session(session_id)
        if session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        await async_delete_science_session(session_id)
        return ApiResponse(data={"ok": True})
    except ScienceSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("remove_session failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── Session Update Endpoints (Pin, Archive, Title) ──

class PinRequest(BaseModel):
    pinned: bool

class TitleRequest(BaseModel):
    title: str


@router.patch("/{session_id}/pin", response_model=ApiResponse)
async def update_session_pin(
    session_id: str,
    request: PinRequest,
    current_user: User = Depends(require_user)
) -> ApiResponse:
    """Pin or unpin a session."""
    try:
        session = await async_get_science_session(session_id)
        if session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        session.pinned = request.pinned
        await session.save()
        return ApiResponse(data={"session_id": session_id, "pinned": request.pinned})
    except ScienceSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("update_session_pin failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.patch("/{session_id}/title", response_model=ApiResponse)
async def update_session_title(
    session_id: str,
    request: TitleRequest,
    current_user: User = Depends(require_user)
) -> ApiResponse:
    """Update session title."""
    try:
        session = await async_get_science_session(session_id)
        if session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        session.title = request.title
        await session.save()
        return ApiResponse(data={"session_id": session_id, "title": request.title})
    except ScienceSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("update_session_title failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{session_id}/clear_unread_message_count", response_model=ApiResponse)
async def clear_unread_message_count(session_id: str, current_user: User = Depends(require_user)) -> ApiResponse:
    try:
        session = await async_get_science_session(session_id)
        if session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        session.unread_message_count = 0
        await session.save()
        return ApiResponse(data={"ok": True})
    except ScienceSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("clear_unread_message_count failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{session_id}/stop", response_model=ApiResponse)
async def stop_session(session_id: str, current_user: User = Depends(require_user)) -> ApiResponse:
    try:
        session = await async_get_science_session(session_id)
        if session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        session.cancel()
        setattr(session, "status", SessionStatus.COMPLETED)
        await session.save()
        return ApiResponse(data={"ok": True})
    except ScienceSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("stop_session failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── Background agent execution (decoupled from SSE) ──

import asyncio as _asyncio

_agent_tasks: Dict[str, "_asyncio.Task[None]"] = {}
_agent_queues: Dict[str, "_asyncio.Queue[Optional[Dict[str, str]]]"] = {}


async def cleanup_orphaned_sessions() -> int:
    """Mark orphaned sessions as completed on startup.

    Called during lifespan startup — any RUNNING session or PENDING session
    with events must be orphaned because the process was restarted.
    Brand-new PENDING sessions (no events) are left intact.
    """
    now = _now_ts()
    result = await _db.get_collection("sessions").update_many(
        {"$or": [
            {"status": SessionStatus.RUNNING},
            {"status": SessionStatus.PENDING, "events.0": {"$exists": True}},
        ]},
        {
            "$set": {"status": SessionStatus.COMPLETED, "updated_at": now},
            "$push": {"events": {
                "event": "done",
                "data": {
                    "event_id": shortuuid.uuid(),
                    "timestamp": now,
                    "statistics": {},
                    "interrupted": True,
                },
            }},
        },
    )
    if result.modified_count:
        logger.info(
            f"[Startup] Cleaned up {result.modified_count} orphaned session(s) "
            "(running/pending → completed)"
        )
    return result.modified_count


async def graceful_shutdown_agents() -> None:
    """Cancel every running agent task and bulk-update DB status.

    Called during lifespan shutdown so that a normal restart does not
    leave orphaned sessions in the database.
    """
    tasks_to_cancel = [
        (sid, t) for sid, t in list(_agent_tasks.items()) if not t.done()
    ]
    for sid, task in tasks_to_cancel:
        task.cancel()
    for sid, task in tasks_to_cancel:
        try:
            await task
        except (_asyncio.CancelledError, Exception):
            pass

    _agent_tasks.clear()
    _agent_queues.clear()

    now = _now_ts()
    result = await _db.get_collection("sessions").update_many(
        {"status": {"$in": [SessionStatus.RUNNING, SessionStatus.PENDING]}},
        {
            "$set": {"status": SessionStatus.COMPLETED, "updated_at": now},
            "$push": {"events": {
                "event": "done",
                "data": {
                    "event_id": shortuuid.uuid(),
                    "timestamp": now,
                    "statistics": {},
                    "interrupted": True,
                },
            }},
        },
    )
    cancelled = len(tasks_to_cancel)
    orphaned = result.modified_count
    if cancelled or orphaned:
        logger.info(
            f"[Shutdown] Cancelled {cancelled} agent task(s), "
            f"cleaned up {orphaned} orphaned session(s)"
        )


def _emit_to_sse(session_id: str, event: Dict[str, str]) -> None:
    """Push an SSE event dict to the live queue (if a client is connected)."""
    q = _agent_queues.get(session_id)
    if q is not None:
        try:
            q.put_nowait(event)
        except Exception:
            pass


async def _agent_background_worker(
    session: Any,
    session_id: str,
    message: str,
    attachments: List[str],
    event_id: Optional[str] = None,
    timestamp: Optional[int] = None,
    language: Optional[str] = None,
) -> None:
    """Run agent in a background task. Results are saved to DB and pushed to SSE."""
    from backend.notifications import publish as _notify

    user_attachments = attachments or []
    _is_im = getattr(session, "source", None) in ("wechat", "lark")
    _im_user_id = getattr(session, "user_id", None)

    if message.strip():
        user_event = _wrap_event("message", {
            "event_id": event_id or _new_event_id(),
            "timestamp": timestamp or _now_ts(),
            "content": message,
            "role": "user",
            "attachments": user_attachments,
        })
        _append_session_event(session, user_event)
        await session.save()
        if _is_im and _im_user_id:
            _notify("session_updated", {
                "session_id": session_id,
                "user_id": _im_user_id,
                "session_event": user_event,
            })

    session.reset_cancel()
    setattr(session, "status", SessionStatus.RUNNING)
    await session.save()

    # Snapshot workspace before agent execution for round-level file tracking
    pre_file_snapshot = _snapshot_workspace_files(session.vm_root_dir)

    statistics: Dict[str, Any] = {}
    _chunk_buffer: list[str] = []

    def _emit(evt_name: str, data_json: str) -> None:
        _emit_to_sse(session_id, {"event": evt_name, "data": data_json})
        if _is_im and _im_user_id:
            _notify("session_updated", {
                "session_id": session_id,
                "user_id": _im_user_id,
                "session_event": {"event": evt_name, "data": json.loads(data_json)},
            })

    # Generate title after the first user message
    if message.strip() and not (getattr(session, "title", None) or "").strip():
        events = getattr(session, "events", []) or []
        if _count_user_messages(events) <= 1:
            try:
                gen_title = await _generate_session_title(message)
                if gen_title:
                    setattr(session, "title", gen_title)
                    await session.save()
                    _emit("title", _json_dumps({
                        "event_id": _new_event_id(),
                        "timestamp": _now_ts(),
                        "title": gen_title,
                    }))
            except Exception as exc:
                logger.warning("Title generation failed: %s", exc)

    try:
        async for evt in arun_science_task_stream(
            session=session, query=message or "", attachments=user_attachments,
            language=language,
        ):
            if session.is_cancelled():
                _emit("error", _json_dumps({
                    "event_id": _new_event_id(), "timestamp": _now_ts(),
                    "error": "Session stopped by user",
                }))
                return

            mapped = _map_science_stream_to_agent_event(evt)
            if mapped is None:
                continue

            if mapped.get("event") == "statistics":
                statistics = mapped.get("data", {})
                continue

            evt_name = mapped.get("event")

            if evt_name == "message_chunk":
                _chunk_buffer.append(mapped.get("data", {}).get("content", ""))
                _emit(evt_name, _json_dumps(mapped["data"]))
                continue

            if evt_name == "message_chunk_done":
                if _chunk_buffer:
                    full_content = "".join(_chunk_buffer)
                    persist_event = _wrap_event("message", {
                        "event_id": _new_event_id(), "timestamp": _now_ts(),
                        "content": full_content, "role": "assistant", "attachments": [],
                    })
                    _append_session_event(session, persist_event)
                    await session.save()
                    _chunk_buffer.clear()
                _emit(evt_name, _json_dumps(mapped["data"]))
                continue

            _append_session_event(session, mapped)
            if evt_name in ["message", "tool", "step", "plan"]:
                await session.save()
            _emit(evt_name, _json_dumps(mapped["data"]))

    except Exception as exc:
        logger.exception(f"[AgentWorker] session={session_id} failed")
        error_event = _wrap_event("error", {
            "event_id": _new_event_id(), "timestamp": _now_ts(), "error": str(exc),
        })
        _append_session_event(session, error_event)
        _emit(error_event["event"], _json_dumps(error_event["data"]))

    finally:
        if _chunk_buffer:
            full_content = "".join(_chunk_buffer)
            persist_event = _wrap_event("message", {
                "event_id": _new_event_id(), "timestamp": _now_ts(),
                "content": full_content, "role": "assistant", "attachments": [],
            })
            _append_session_event(session, persist_event)
            _chunk_buffer.clear()

        setattr(session, "status", SessionStatus.COMPLETED)

        # Auto-detect skills
        try:
            saved_skills = {
                d.name for d in _Path(_EXTERNAL_SKILLS_DIR).iterdir()
                if d.is_dir() and not d.name.startswith(".")
            } if _Path(_EXTERNAL_SKILLS_DIR).is_dir() else set()
            detected_skills: set = set()
            for sub in [".agents/skills", "skills"]:
                skills_dir = _Path(_WORKSPACE_DIR) / session_id / sub
                if not skills_dir.is_dir():
                    continue
                for child in sorted(skills_dir.iterdir()):
                    if (child.is_dir()
                            and not child.name.startswith(".")
                            and (child / "SKILL.md").is_file()
                            and child.name not in saved_skills
                            and child.name not in detected_skills):
                        detected_skills.add(child.name)
                        _emit("skill_save_prompt", _json_dumps({
                            "event_id": _new_event_id(),
                            "timestamp": _now_ts(),
                            "skill_name": child.name,
                        }))
        except Exception:
            logger.debug("skill auto-detect skipped", exc_info=True)

        # Auto-detect tools
        try:
            staging_dir = _Path(_WORKSPACE_DIR) / session_id / "tools_staging"
            if staging_dir.is_dir():
                saved_tools = {
                    f.stem for f in _Path(_TOOLS_DIR).glob("*.py")
                    if f.name != "__init__.py"
                } if _Path(_TOOLS_DIR).is_dir() else set()
                for child in sorted(staging_dir.glob("*.py")):
                    tool_name = child.stem
                    if (
                        tool_name not in saved_tools
                        and "@tool" in child.read_text(encoding="utf-8", errors="replace")
                        and _read_passed_tool_validation(staging_dir, tool_name) is not None
                    ):
                        _emit("tool_save_prompt", _json_dumps({
                            "event_id": _new_event_id(),
                            "timestamp": _now_ts(),
                            "tool_name": tool_name,
                        }))
        except Exception:
            logger.debug("tool auto-detect skipped", exc_info=True)

        # Compute files created/modified during this round
        round_files: List[Dict[str, Any]] = []
        try:
            post_file_snapshot = _snapshot_workspace_files(session.vm_root_dir)
            round_files = _diff_workspace_files(
                pre_file_snapshot, post_file_snapshot,
                session.vm_root_dir, session_id,
            )
        except Exception:
            logger.debug("round_files diff failed", exc_info=True)

        done_event = _wrap_event("done", {
            "event_id": _new_event_id(),
            "timestamp": _now_ts(),
            "statistics": statistics,
            "round_files": round_files,
        })
        _append_session_event(session, done_event)
        await session.save()
        _emit(done_event["event"], _json_dumps(done_event["data"]))

        # Signal SSE stream completion
        q = _agent_queues.get(session_id)
        if q is not None:
            try:
                q.put_nowait(None)
            except Exception:
                pass

        _agent_tasks.pop(session_id, None)
        _agent_queues.pop(session_id, None)
        logger.info(f"[AgentWorker] session={session_id} completed")


@router.post("/{session_id}/chat")
async def chat_with_session(
    session_id: str, 
    body: ChatRequest, 
    request: Request, 
    current_user: User = Depends(require_user)
) -> EventSourceResponse:

    try:
        session = await async_get_science_session(session_id)
        if session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
    except ScienceSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    # Hot-swap model config if the user switched models mid-conversation
    if body.model_config_id:
        current_mc = getattr(session, "model_config", None)
        current_mc_id = current_mc.get("id") if isinstance(current_mc, dict) else None
        if body.model_config_id != current_mc_id:
            mc = await get_model_config(body.model_config_id)
            if mc:
                if not mc.is_system and mc.user_id != current_user.id:
                    raise HTTPException(status_code=403, detail="Cannot use this model")
                session.model_config = mc.model_dump()
                await session.save()
                logger.info(f"[Chat] Model switched for session {session_id}: {current_mc_id} → {body.model_config_id}")

    existing_task = _agent_tasks.get(session_id)
    is_reconnect = existing_task is not None and not existing_task.done()

    # Orphan detection: session DB says RUNNING but no live agent task exists
    # (happens after a server restart). Don't start a phantom agent — just
    # mark completed and inform the client immediately.
    # Only RUNNING sessions can be orphaned; PENDING sessions never had an
    # agent so they are simply idle (not orphaned).
    is_orphan = (
        not is_reconnect
        and session.status == SessionStatus.RUNNING
        and not body.message
    )
    if is_orphan:
        session.status = SessionStatus.COMPLETED
        done_data = {
            "event_id": _new_event_id(),
            "timestamp": _now_ts(),
            "statistics": {},
            "interrupted": True,
        }
        _append_session_event(session, _wrap_event("done", done_data))
        await session.save()
        logger.info(f"[Chat] Orphaned session {session_id} recovered → completed")

        async def _orphan_generator():
            yield {"event": "done", "data": _json_dumps(done_data)}

        return EventSourceResponse(_orphan_generator())

    # Create a fresh SSE queue for this connection
    queue: _asyncio.Queue[Optional[Dict[str, str]]] = _asyncio.Queue()
    _agent_queues[session_id] = queue

    if not is_reconnect:
        task = _asyncio.create_task(
            _agent_background_worker(
                session, session_id,
                body.message or "", body.attachments or [],
                event_id=body.event_id, timestamp=body.timestamp,
                language=body.language,
            )
        )
        _agent_tasks[session_id] = task
    else:
        logger.info(f"[Chat] Reconnecting SSE to running agent for session {session_id}")

    # Capture the cursor so we can replay missed events on reconnection
    client_cursor = body.event_id if is_reconnect else None

    async def event_generator():
        try:
            # On reconnection: replay events the client missed (between getSession and now)
            if client_cursor:
                found_cursor = False
                for evt in list(session.events):
                    evt_data = evt.get("data", {})
                    if not found_cursor:
                        if evt_data.get("event_id") == client_cursor:
                            found_cursor = True
                        continue
                    yield {"event": evt["event"], "data": _json_dumps(evt_data)}

            # Stream live events from the background worker
            while True:
                try:
                    event = await _asyncio.wait_for(queue.get(), timeout=600)
                except _asyncio.TimeoutError:
                    break
                if event is None:
                    break
                yield event
        except _asyncio.CancelledError:
            pass
        finally:
            if _agent_queues.get(session_id) is queue:
                _agent_queues.pop(session_id, None)

    return EventSourceResponse(event_generator())


@router.post("/{session_id}/share", response_model=ApiResponse)
async def share_session(session_id: str, current_user: User = Depends(require_user)) -> ApiResponse:
    try:
        session = await async_get_science_session(session_id)
        if session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        session.is_shared = True
        await session.save()
        return ApiResponse(data={"session_id": session_id, "is_shared": True})
    except ScienceSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("share_session failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/{session_id}/share", response_model=ApiResponse)
async def unshare_session(session_id: str, current_user: User = Depends(require_user)) -> ApiResponse:
    try:
        session = await async_get_science_session(session_id)
        if session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        session.is_shared = False
        await session.save()
        return ApiResponse(data={"session_id": session_id, "is_shared": False})
    except ScienceSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("unshare_session failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ═══════════════════════════════════════════════════════════════════
# 沙盒文件管理
# ═══════════════════════════════════════════════════════════════════

def _classify_file(rel_path: str) -> str:
    """Classify a workspace file by its relative path into a UI category."""
    top_dir = rel_path.split("/", 1)[0] if "/" in rel_path else ""
    basename = rel_path.rsplit("/", 1)[-1]

    if top_dir in ("_diagnostic", "tools_staging", "__pycache__"):
        return "process"
    if basename in ("CONTEXT.md", "planner.md", "AGENTS.md") or basename.startswith("."):
        return "process"
    if top_dir in ("research_data",):
        return "process"
    if basename.endswith(".pyc"):
        return "process"
    return "result"


@router.get("/{session_id}/files", response_model=ApiResponse)
async def list_session_files(session_id: str, current_user: User = Depends(require_user)) -> ApiResponse:
    """列出 session workspace 目录（/home/scienceclaw/{session_id}/）下的所有文件。"""
    try:
        session = await async_get_science_session(session_id)
        if session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        workspace_dir = session.vm_root_dir
        if not workspace_dir.is_dir():
            return ApiResponse(data=[])

        file_list: List[Dict[str, Any]] = []
        for file_path in sorted(workspace_dir.rglob("*")):
            if not file_path.is_file():
                continue
            abs_path = str(file_path)
            try:
                rel_path = str(file_path.relative_to(workspace_dir))
            except ValueError:
                rel_path = file_path.name
            try:
                stat = file_path.stat()
                upload_date = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
                file_size = stat.st_size
            except OSError:
                upload_date = datetime.now(timezone.utc).isoformat()
                file_size = 0
            file_list.append({
                "file_id": abs_path,
                "filename": file_path.name,
                "size": file_size,
                "upload_date": upload_date,
                "content_type": "text/plain",
                "file_url": f"/api/v1/sessions/{session_id}/sandbox-file/download?path={abs_path}",
                "category": _classify_file(rel_path),
                "metadata": {"sandbox_path": abs_path, "session_id": session_id},
            })

        return ApiResponse(data=file_list)
    except ScienceSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("list_session_files failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{session_id}/sandbox-file")
async def read_sandbox_file(
    session_id: str,
    path: str,
    current_user: User = Depends(require_user),
):
    """代理读取沙盒文件内容。path 必须在 session workspace 目录下。"""
    try:
        session = await async_get_science_session(session_id)
        if session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        workspace_prefix = str(session.vm_root_dir) + "/"
        if not path.startswith(workspace_prefix):
            raise HTTPException(status_code=403, detail="File path not under session workspace")

        local_path = _Path(path)
        if local_path.is_file():
            try:
                content = local_path.read_text(encoding="utf-8", errors="replace")
                return ApiResponse(data={"file": path, "content": content})
            except Exception:
                pass

        content = await _sandbox_file_read(path)
        if content is None:
            raise HTTPException(status_code=404, detail="File not found")

        return ApiResponse(data={"file": path, "content": content})
    except ScienceSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("read_sandbox_file failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{session_id}/sandbox-file/download")
async def download_sandbox_file(
    session_id: str,
    path: str = Query(...),
    current_user: User = Depends(require_user),
):
    """直接返回沙盒文件原始内容（用于下载/预览）。优先本地文件系统，回退 sandbox API。"""
    try:
        session = await async_get_science_session(session_id)
        if session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        workspace_prefix = str(session.vm_root_dir) + "/"
        if not path.startswith(workspace_prefix):
            raise HTTPException(status_code=403, detail="File path not under session workspace")

        local_path = _Path(path)
        if local_path.is_file():
            return FileResponse(
                path=str(local_path),
                filename=local_path.name,
                media_type="application/octet-stream",
            )

        content = await _sandbox_file_read(path)
        if content is None:
            raise HTTPException(status_code=404, detail="File not found")

        filename = path.rsplit("/", 1)[-1] if "/" in path else path
        from urllib.parse import quote
        try:
            filename.encode("ascii")
            cd_header = f'attachment; filename="{filename}"'
        except UnicodeEncodeError:
            encoded = quote(filename)
            cd_header = f"attachment; filename*=UTF-8''{encoded}"
        return Response(
            content=content.encode("utf-8") if isinstance(content, str) else content,
            media_type="application/octet-stream",
            headers={"Content-Disposition": cd_header},
        )
    except ScienceSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("download_sandbox_file failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
