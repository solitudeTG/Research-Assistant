"""
agent.py 鈥?缁勮 DeepAgent锛氱郴缁熸彁绀鸿瘝 + 妯″瀷 + 宸ュ叿锛堝唴缃?+ 澶栭儴鎵╁睍锛? Skills + 鐩戞帶涓棿浠躲€?

鏋舵瀯锛?
  - HybridSandboxBackend 浣滀负榛樿鍚庣锛?
    - 鏂囦欢鎿嶄綔锛坮ead_file/write_file/edit_file/ls/glob/grep锛夆啋 鏈湴 /home/scienceclaw/
    - 鍛戒护鎵ц锛坋xecute锛夆啋 杩滅▼ sandbox 瀹瑰櫒
    - 閫氳繃 Docker 鍏变韩鍗峰悓姝ユ枃浠?
  - CompositeBackend 璺敱锛?
    - /builtin-skills/ 鈫?FilesystemBackend锛堝唴缃?skills锛屽彧璇伙紝濮嬬粓鍔犺浇锛?
    - /skills/         鈫?FilteredFilesystemBackend锛堝缃?skills锛屽彲灞忚斀/鍒犻櫎锛?
  - deepagents 鍐呯疆宸ュ叿灞傜粺涓€绠＄悊鎵€鏈夊伐鍏凤紙涓嶅啀浣跨敤 MCP sandbox 宸ュ叿锛?

Skills 鏋舵瀯锛?
  - 鍐呯疆 skills锛?app/builtin_skills/锛夛細find-skills 绛夋牳蹇冭兘鍔涳紝
    COPY 杩?Docker 闀滃儚锛屼笉渚濊禆瀹夸富鏈烘寕杞斤紙閬垮厤 macOS 澶у皬鍐欎笉鏁忔劅鏂囦欢绯荤粺鐨勫啿绐侊級
  - 澶栫疆 skills锛?app/Skills/锛夛細鐢ㄦ埛閫氳繃 find-skills 涓嬭浇鎴栬嚜琛屽畨瑁呯殑 skills锛?
    鏀寔灞忚斀鍜屽垹闄ょ鐞?

鐩戞帶涓棿浠讹細
  - SSEMonitoringMiddleware 閫氳繃 wrap_tool_call 鎷︽埅宸ュ叿鎵ц鍓嶅悗
  - 浜嬩欢瀛樺偍鍦?middleware.sse_events锛岀敱 runner.py 杞娑堣垂
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from loguru import logger
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend
from backend.deepagent.engine import get_llm_model
from backend.deepagent.tools import web_search, web_crawl, propose_skill_save, propose_tool_save, eval_skill, grade_eval
from backend.deepagent.tooluniverse_tools import (
    tooluniverse_search,
    tooluniverse_info,
    tooluniverse_run,
)
from backend.deepagent.full_sandbox_backend import FullSandboxBackend
from backend.deepagent.filtered_backend import FilteredFilesystemBackend
from backend.deepagent.sse_middleware import SSEMonitoringMiddleware
from backend.deepagent.offload_middleware import ToolResultOffloadMiddleware
from backend.deepagent.diagnostic import DIAGNOSTIC_ENABLED, DiagnosticLogger
from backend.deepagent.dir_watcher import watcher as _dir_watcher
from backend.research_assistant.subagents import (
    audit_evidence_claims as research_audit_evidence_claims,
    build_deepagents_subagent_configs,
    default_subagent_definitions,
    read_research_evidence,
)
from backend.config import settings

# 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
# 澶栭儴鎵╁睍宸ュ叿锛圱ools 鐩綍鑷姩鎵弿锛屾敮鎸佺儹鍔犺浇锛?
# 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
try:
    from Tools import reload_external_tools
    _initial = reload_external_tools(force=True)
    logger.info(f"[Agent] 宸插姞杞?{len(_initial)} 涓閮ㄦ墿灞曞伐鍏? "
                f"{[t.name for t in _initial]}")
    # Register proxy tools in SSE protocol so tool_meta carries sandbox: true
    from backend.deepagent.sse_protocol import get_protocol_manager as _get_proto
    _proto = _get_proto()
    for _t in _initial:
        _proto.register_sandbox_tool(_t.name, _t.description[:80])
    logger.info(f"[Agent] 宸叉敞鍐?{len(_initial)} 涓矙绠变唬鐞嗗伐鍏峰埌 SSE 鍗忚")
except ImportError:
    reload_external_tools = None  # type: ignore[assignment]
    logger.warning("[Agent] 鏈壘鍒?Tools 鍖咃紝璺宠繃澶栭儴鎵╁睍宸ュ叿鍔犺浇")

# 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
# 璺緞閰嶇疆
# 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

_BUILTIN_SKILLS_DIR = os.environ.get("BUILTIN_SKILLS_DIR", "/app/builtin_skills")
_EXTERNAL_SKILLS_DIR = os.environ.get("EXTERNAL_SKILLS_DIR", "/app/Skills")
_BUILTIN_SKILLS_ROUTE = "/builtin-skills/"
_EXTERNAL_SKILLS_ROUTE = "/skills/"
_WORKSPACE_DIR = os.environ.get("WORKSPACE_DIR", "/home/scienceclaw")

# 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
# Backend 鏋勫缓
# 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€


def _build_backend(session_id: str, sandbox: FullSandboxBackend, blocked_skills: Set[str] | None = None):
    """
    鏋勫缓 CompositeBackend 宸ュ巶鍑芥暟锛堜細璇濈骇闅旂锛夛細
      - 榛樿: 浼犲叆鐨?FullSandboxBackend 瀹炰緥
      - /builtin-skills/ 璺敱: FilesystemBackend锛堝唴缃?skills锛屽缁堝姞杞斤級
      - /skills/          璺敱: FilteredFilesystemBackend锛堝缃?skills锛岃繃婊ゅ睆钄介」锛?
    """
    routes = {}

    if os.path.isdir(_BUILTIN_SKILLS_DIR):
        logger.info(f"[Skills] 鍐呯疆 skills: {_BUILTIN_SKILLS_DIR} 鈫?{_BUILTIN_SKILLS_ROUTE}")
        routes[_BUILTIN_SKILLS_ROUTE] = FilesystemBackend(
            root_dir=_BUILTIN_SKILLS_DIR,
            virtual_mode=True,
        )

    if os.path.isdir(_EXTERNAL_SKILLS_DIR):
        logger.info(f"[Skills] 澶栫疆 skills: {_EXTERNAL_SKILLS_DIR} 鈫?{_EXTERNAL_SKILLS_ROUTE}"
                     f" (blocked: {blocked_skills or set()})")
        routes[_EXTERNAL_SKILLS_ROUTE] = FilteredFilesystemBackend(
            root_dir=_EXTERNAL_SKILLS_DIR,
            virtual_mode=True,
            blocked_skills=blocked_skills or set(),
        )

    if routes:
        # 杩斿洖宸ュ巶鍑芥暟浠ョ‘淇濊矾鐢辩敓鏁?
        return lambda rt: CompositeBackend(default=sandbox, routes=routes)
    else:
        return sandbox


# 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
# 绯荤粺鎻愮ず璇?
# 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

_SYSTEM_PROMPT_TEMPLATE = """You are ScienceClaw, a proactive personal AI assistant designed to help users solve problems, conduct research, and complete tasks efficiently.

Current date and time: {current_datetime}.

## Language
Always respond in {language_instruction}.

## Core Principles
- Adapt to the conversation. Chat naturally for casual topics, but take concrete actions when the user asks for tasks or problem-solving.
- Prefer execution over explanation. If a task can be solved through code or tools, implement and execute the solution instead of only describing it.
- **Real-time information**: For any question involving current or up-to-date information, you MUST use `web_search` 鈥?NEVER answer from training data alone.
- **Write files, not chat**: When the user asks to write, create, or generate code/scripts/files, ALWAYS use `write_file` to create real files 鈥?never just paste code in chat.
- **Write 鈫?Execute 鈫?Fix loop**: After writing ANY executable script, you MUST immediately run it via `execute` to verify correctness. If it fails, fix and re-run.
- **Skill-first approach**: ALWAYS check available skills (`/builtin-skills/` and `/skills/`) before starting any task. If a skill matches, `read_file` its SKILL.md and follow the workflow. Do NOT reinvent what a skill already provides.
- **Research tasks**: When the user's request involves research, reports, reviews, surveys, literature analysis, discoveries, or any deep investigation topic, ALWAYS check and consider `/skills/deep-research/SKILL.md` first.
- **SKILL.md files are instruction documents** 鈥?use `read_file` to read them, NEVER `execute` them as scripts.
- Solve problems proactively. Only ask questions when the intent or requirements are truly unclear.

## Research Subagent Delegation
- Stay single-agent for simple factual Q&A or casual chat, especially when no evidence audit, multi-paper reading, or report-grade synthesis is needed.
- Choose autonomously whether a research task benefits from subagents. Do not ask the user to choose an Agent, and do not mention hidden routing mechanics unless it helps explain progress.
- Use `paper_reader_worker` when the task requires scoped reading across multiple papers/materials, parallel evidence extraction, or a focused re-read for a follow-up question.
- Use `research_auditor` after drafting evidence-grounded claims, report sections, or high-trust conclusions that need citation/evidence consistency checks.
- Treat all subagent outputs as context_only or process_trace. They can guide your synthesis, but they are not citation evidence; only paper, web, or database evidence may be cited to the user.

## Workspace
Your workspace directory is {workspace_dir}/.
- All files should be created under this directory using absolute paths.
- The workspace is shared between the file system and the execution sandbox.

## Sandbox Boundary
The sandbox is an isolated execution environment. Scripts running in the sandbox CANNOT import or call your tools directly (`from functions import ...` will FAIL with `ModuleNotFoundError`).

**Data flow**: Use YOUR tools (web_search, web_crawl, tooluniverse_run, etc.) to gather data 鈫?save results to workspace files via `write_file` 鈫?write sandbox scripts that READ those files. NEVER call your tools from within sandbox scripts.

**Large tool results** are automatically saved to `research_data/` files (raw format). To use them in sandbox scripts: `read_file` the data 鈫?write a clean JSON file via a Python script with `json.dump()` 鈫?sandbox scripts read that clean file.

## Task Completion Strategy

### Step 1: Understand & Plan
- Identify ALL deliverables, requirements, and output format.
- For any task involving 2+ steps, call `write_todos` BEFORE starting.
- Check Memory: **AGENTS.md** and **CONTEXT.md**.
- **Check Available Skills (MANDATORY)** 鈥?review the skills catalog. If ANY skill matches the task, `read_file` that SKILL.md and follow its workflow. Do NOT skip this step.

### Step 2: Execute
- If a skill matched 鈫?follow the skill's workflow completely.
- Otherwise, use tools directly. Priority: existing skills > built-in tools > ToolUniverse > web_search.
- **Before `propose_tool_save`**: read `/builtin-skills/tool-creator/SKILL.md` first.
- **Before `propose_skill_save`**: read `/builtin-skills/skill-creator/SKILL.md` first.
- Build incrementally 鈥?one component per tool call. Test via `execute` after writing.

### Step 3: Verify & Deliver
- Re-read the user's original request. Check all deliverables are produced.
- If a script fails, fix the specific error 鈥?do NOT rewrite from scratch. If it fails 2+ times, simplify.

### Step 4: Reflect & Capture
After completing a non-trivial task:
- **Reusable workflow** 鈫?Suggest saving as a **skill** via skill-creator.
- **Reusable function** 鈫?Suggest saving as a **tool** via tool-creator.
- **User preference learned** 鈫?Update **AGENTS.md** via `edit_file`.
- **Project context learned** 鈫?Update **CONTEXT.md** via `edit_file`.
"""


_EVAL_SYSTEM_PROMPT_TEMPLATE = """You are ScienceClaw, a proactive personal AI assistant designed to help users solve problems, conduct research, and complete tasks efficiently.

Current date and time: {current_datetime}

## Core Principles
- Prefer execution over explanation. If a task can be solved through code or tools, implement and execute the solution instead of only describing it.
- Always respond in the same language the user uses.
- When the user asks to write, create, or generate code/scripts/files, ALWAYS use write_file to create real files.
- Use sandbox execution whenever it can produce verifiable results.

## Workspace
Your workspace directory is {workspace_dir}/.
- All files should be created under this directory using absolute paths.
- The workspace is shared between the file system and the execution sandbox.
"""


_LANGUAGE_MAP = {
    "zh": (
        "Chinese (Simplified)",
        "You must respond in Simplified Chinese. Generated reports, document titles, and body text must also use Simplified Chinese.",
    ),
    "en": ("English", "You must respond in English. All generated reports, document titles and body text must also be in English."),
}


def get_system_prompt(workspace_dir: str, sandbox_env: str | None = None, language: str | None = None) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S %A")
    lang_code = (language or "").strip().lower()
    if lang_code in _LANGUAGE_MAP:
        lang_name, lang_detail = _LANGUAGE_MAP[lang_code]
        language_instruction = (
            f"- The user has set their preferred language to **{lang_name}** (code: `{lang_code}`).\n"
            f"- {lang_detail}\n"
            f"- This applies to ALL outputs: conversation replies, report content, section titles, chart labels, and file names."
        )
    else:
        language_instruction = "- Always respond in the same language the user uses."

    prompt = _SYSTEM_PROMPT_TEMPLATE.format(
        current_datetime=now,
        workspace_dir=workspace_dir,
        language_instruction=language_instruction,
    )
    if sandbox_env:
        prompt += f"\n\n## Sandbox Environment Information\n{sandbox_env}"
    return prompt


def _get_eval_system_prompt(workspace_dir: str, sandbox_env: str | None = None) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S %A")
    prompt = _EVAL_SYSTEM_PROMPT_TEMPLATE.format(
        current_datetime=now,
        workspace_dir=workspace_dir,
    )
    if sandbox_env:
        prompt += f"\n\n## Sandbox Environment Information\n{sandbox_env}"
    return prompt


# 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
# 宸ュ叿鍒楄〃锛堝唴缃?+ 澶栭儴鎵╁睍锛屼笉鍐嶅寘鍚?MCP sandbox 宸ュ叿锛?
# 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

_STATIC_TOOLS = [
    web_search, web_crawl, propose_skill_save, propose_tool_save,
    eval_skill, grade_eval,
    tooluniverse_search, tooluniverse_info, tooluniverse_run,
]

_RESEARCH_SUBAGENT_TOOLS = {
    "audit_evidence_claims": research_audit_evidence_claims,
    "read_research_evidence": read_research_evidence,
}


def _tool_pack_id(tool: Any) -> str | None:
    metadata = getattr(tool, "metadata", None)
    if not isinstance(metadata, dict):
        return None
    tool_pack = metadata.get("tool_pack")
    if not isinstance(tool_pack, dict):
        return None
    pack_id = tool_pack.get("id")
    if not isinstance(pack_id, str) or not pack_id.strip():
        return None
    return pack_id.strip()


def _collect_tools(
    blocked_tools: Set[str] | None = None,
    active_tool_packs: Set[str] | None = None,
) -> List:
    """鍚堝苟鍐呯疆宸ュ叿涓庡閮ㄦ墿灞曞伐鍏凤紝鍘婚噸骞惰繃婊ゅ睆钄介」銆?
    閫氳繃 DirWatcher 妫€娴?Tools/ 鐩綍鍙樻洿锛屼粎鍦ㄥ彉鏇存椂鎵嶉噸鏂?import 妯″潡銆?    """
    blocked = blocked_tools or set()
    active_packs = {pack.strip() for pack in (active_tool_packs or set()) if pack.strip()}
    seen_names: set[str] = set()
    all_tools: List = []

    ext_tools: list = []
    if reload_external_tools is not None:
        try:
            ext_tools = reload_external_tools()
        except Exception:
            logger.warning("[Agent] failed to reload external tools", exc_info=True)

    for t in _STATIC_TOOLS:
        if t.name in blocked:
            logger.info(f"[Agent] 宸ュ叿宸插睆钄斤紝璺宠繃: {t.name}")
            continue
        if t.name not in seen_names:
            all_tools.append(t)
            seen_names.add(t.name)
        else:
            logger.warning(f"[Agent] 宸ュ叿鍚嶇О閲嶅锛岃烦杩? {t.name}")

    for t in ext_tools:
        if t.name in blocked:
            logger.info(f"[Agent] 宸ュ叿宸插睆钄斤紝璺宠繃: {t.name}")
            continue
        pack_id = _tool_pack_id(t)
        if pack_id not in active_packs:
            logger.info(f"[Agent] 澶栭儴宸ュ叿鏈縺娲伙紝璺宠繃: {t.name} (tool_pack={pack_id or 'missing'})")
            continue
        if t.name not in seen_names:
            all_tools.append(t)
            seen_names.add(t.name)
        else:
            logger.warning(f"[Agent] 宸ュ叿鍚嶇О閲嶅锛岃烦杩? {t.name}")
    logger.info(f"[Agent] 鑷畾涔夊伐鍏峰垪琛?{len(all_tools)}): {[t.name for t in all_tools]}")
    return all_tools


# 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
# 灞忚斀鏌ヨ锛圡ongoDB锛?
# 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

async def get_blocked_skills(user_id: str) -> Set[str]:
    """Read blocked skills for the user from MongoDB."""
    try:
        from backend.mongodb.db import db
        col = db.get_collection("blocked_skills")
        cursor = col.find({"user_id": user_id}, {"skill_name": 1})
        blocked = set()
        async for doc in cursor:
            name = doc.get("skill_name")
            if name:
                blocked.add(name)
        return blocked
    except Exception as exc:
        logger.warning(f"[Skills] 鏌ヨ灞忚斀鍒楄〃澶辫触: {exc}")
        return set()


async def get_blocked_tools(user_id: str) -> Set[str]:
    """Read blocked tools for the user from MongoDB."""
    try:
        from backend.mongodb.db import db
        col = db.get_collection("blocked_tools")
        cursor = col.find({"user_id": user_id}, {"tool_name": 1})
        blocked = set()
        async for doc in cursor:
            name = doc.get("tool_name")
            if name:
                blocked.add(name)
        return blocked
    except Exception as exc:
        logger.warning(f"[Tools] 鏌ヨ灞忚斀鍒楄〃澶辫触: {exc}")
        return set()


# 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
# 鍒涘缓 Agent
# 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

async def deep_agent(
    session_id: str,
    model_config: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
    task_settings: Optional["TaskSettings"] = None,
    diagnostic_enabled: bool = False,
    language: Optional[str] = None,
    active_tool_packs: Optional[Set[str]] = None,
) -> Tuple[Any, SSEMonitoringMiddleware, int, Optional[DiagnosticLogger]]:
    """
    鍒涘缓涓€涓畬鏁寸殑 DeepAgent 瀹炰緥锛堜細璇濈骇闅旂锛夛紝骞舵敞鍏?SSE 鐩戞帶涓棿浠躲€?

    Returns:
        (agent, sse_middleware, context_window, diagnostic_logger)

    Skills 鏋舵瀯锛?
      - 鍐呯疆 skills锛?app/builtin_skills/锛夛細COPY 杩涢暅鍍忥紝濮嬬粓鍔犺浇
      - 澶栫疆 skills锛?app/Skills/锛夛細鐢ㄦ埛鑷鐞嗭紝鏀寔灞忚斀杩囨护
    """
    from backend.task_settings import TaskSettings as _TS
    ts: _TS = task_settings or _TS()
    model = get_llm_model(model_config, max_tokens_override=ts.max_tokens)
    context_window = getattr(model, "profile", {}).get("max_input_tokens", 131_072)

    blocked_skills = set()
    blocked_tools = set()
    if user_id:
        blocked_skills = await get_blocked_skills(user_id)
        blocked_tools = await get_blocked_tools(user_id)

    # 鈹€鈹€ 妫€娴?Tools/Skills 鐩綍鍙樻洿骞舵寜闇€閲嶆柊鍔犺浇 鈹€鈹€
    _dir_watcher.has_changed(_EXTERNAL_SKILLS_DIR)

    tools = _collect_tools(blocked_tools=blocked_tools, active_tool_packs=active_tool_packs)

    sse_middleware = SSEMonitoringMiddleware(
        agent_name="DeepAgent",
        parent_agent=None,
        verbose=False,
    )

    # 1. 瀹炰緥鍖?FullSandboxBackend 骞惰幏鍙栫幆澧冧笂涓嬫枃
    sandbox = FullSandboxBackend(
        session_id=session_id,
        user_id=user_id or "default_user",
        base_dir=_WORKSPACE_DIR,
        execute_timeout=ts.sandbox_exec_timeout,
        max_output_chars=ts.max_output_chars,
    )
    
    sandbox_info = None
    actual_workspace = sandbox.workspace  # /home/scienceclaw/{session_id}锛堜笌鍚庣鍏变韩鍗凤級
    
    ctx = await sandbox.get_context()
    if ctx.get("success"):
        sandbox_info = ctx.get("data")

    # 2. 鏋勫缓澶嶅悎鍚庣锛堝彲鑳藉寘鍚?Skills 璺敱锛?
    backend = _build_backend(session_id, sandbox, blocked_skills=blocked_skills)

    # 宸ュ叿缁撴灉鑷姩钀界洏涓棿浠讹細澶у瀷宸ュ叿缁撴灉鍐欏叆鏂囦欢锛孉gent 鎸夐渶 read_file 璇诲彇
    offload_middleware = ToolResultOffloadMiddleware(
        workspace_dir=actual_workspace,
        backend=sandbox,
    )

    # 鈹€鈹€ 璇婃柇妯″紡锛氳褰?LLM 姣忔鐪嬪埌鐨勫畬鏁翠笂涓嬫枃 鈹€鈹€
    diag: Optional[DiagnosticLogger] = None
    if diagnostic_enabled:
        diag = DiagnosticLogger(actual_workspace, session_id)
        offload_middleware._diagnostic = diag

    # 涓棿浠舵墽琛岄『搴忥細offload锛堜慨鏀圭粨鏋滐級鈫?SSE锛堢洃鎺ц褰曪級
    # create_deep_agent 杩樹細鑷姩娉ㄥ叆 SummarizationMiddleware锛堝熀浜?model profile锛?
    agent_kwargs: Dict[str, Any] = {
        "model": model,
        "tools": tools,
        "middleware": [offload_middleware, sse_middleware],
    }

    # 4. 娉ㄥ叆绯荤粺鎻愮ず璇?
    system_prompt = get_system_prompt(actual_workspace, sandbox_info, language=language)
    agent_kwargs["system_prompt"] = system_prompt

    if diag:
        diag.save_system_prompt(system_prompt)

    agent_kwargs["backend"] = backend

    skills_sources: List[str] = []
    if os.path.isdir(_BUILTIN_SKILLS_DIR):
        skills_sources.append(_BUILTIN_SKILLS_ROUTE)
    if os.path.isdir(_EXTERNAL_SKILLS_DIR):
        skills_sources.append(_EXTERNAL_SKILLS_ROUTE)

    if skills_sources:
        agent_kwargs["skills"] = skills_sources
        logger.info(f"[Agent] skills enabled: sources={skills_sources}, blocked={blocked_skills}")

    # 4. 鍚敤璺ㄤ細璇濊蹇嗭紙涓ゅ眰闅旂锛?
    #    - 鍏ㄥ眬 AGENTS.md锛氱敤鎴峰亸濂?+ 閫氱敤妯″紡锛堣法鎵€鏈変細璇濓紝浣撻噺灏忥級
    #    - 浼氳瘽绾?CONTEXT.md锛氬綋鍓嶉」鐩?浠诲姟涓婁笅鏂囷紙浼氳瘽鍒犻櫎鏃惰嚜鍔ㄦ竻鐞嗭級
    _mem_user = user_id or "default_user"
    _mem_dir = os.path.join(_WORKSPACE_DIR, "_memory", _mem_user)
    os.makedirs(_mem_dir, exist_ok=True)
    os.chmod(_mem_dir, 0o777)
    _global_mem = os.path.join(_mem_dir, "AGENTS.md")
    if not os.path.isfile(_global_mem):
        with open(_global_mem, "w") as f:
            f.write("# Global Memory (persists across all sessions)\n\n"
                    "## User Preferences\n\n"
                    "## General Patterns\n\n"
                    "## Notes\n")
        logger.info(f"[Memory] 鍒濆鍖栧叏灞€ Memory: {_global_mem}")

    _session_mem = os.path.join(actual_workspace, "CONTEXT.md")
    if not os.path.isfile(_session_mem):
        with open(_session_mem, "w") as f:
            f.write("# Session Context (this session only)\n\n"
                    "## Project Context\n\n"
                    "## Task Notes\n")
        logger.info(f"[Memory] 鍒濆鍖栦細璇?Context: {_session_mem}")

    _MAX_MEMORY_CHARS = 4000
    _mem_files_to_use = []
    for _mf in [_global_mem, _session_mem]:
        try:
            _mf_size = os.path.getsize(_mf)
            if _mf_size > _MAX_MEMORY_CHARS:
                with open(_mf, "r", encoding="utf-8") as f:
                    _full = f.read()
                _truncated = _full[:_MAX_MEMORY_CHARS].rsplit("\n", 1)[0]
                _tmp_path = _mf + ".truncated"
                with open(_tmp_path, "w", encoding="utf-8") as f:
                    f.write(_truncated + "\n\n(Memory truncated 鈥?keep entries concise to stay under limit)\n")
                _mem_files_to_use.append(_tmp_path)
                logger.warning(
                    f"[Memory] {os.path.basename(_mf)} too large ({_mf_size:,} chars), "
                    f"truncated to {_MAX_MEMORY_CHARS:,} for injection"
                )
            else:
                _mem_files_to_use.append(_mf)
        except Exception:
            _mem_files_to_use.append(_mf)

    agent_kwargs["memory"] = _mem_files_to_use
    logger.info(f"[Memory] 宸插惎鐢ㄨ蹇? {[os.path.basename(f) for f in _mem_files_to_use]}")

    agent_kwargs["subagents"] = build_deepagents_subagent_configs(
        definitions=default_subagent_definitions(),
        available_tools=_RESEARCH_SUBAGENT_TOOLS,
    )

    agent = create_deep_agent(**agent_kwargs)


    logger.info(
        f"[Agent] session={session_id}, workspace={actual_workspace}, "
        f"middleware={sse_middleware.agent_name}, context_window={context_window:,}"
        f"{', diagnostic=ON' if diag else ''}"
    )
    return agent, sse_middleware, context_window, diag


# 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
# Eval 妯″紡 Agent锛堢簿绠€鐗堬紝鐢ㄤ簬 skill 娴嬭瘯锛?
# 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

async def deep_agent_eval(
    session_id: str,
    model_config: Optional[Dict[str, Any]] = None,
    skill_sources: Optional[List[str]] = None,
) -> Tuple[Any, SSEMonitoringMiddleware]:
    """
    鍒涘缓鐢ㄤ簬 eval 娴嬭瘯鐨勭簿绠€ Agent 鈥?涓嶅惈鍏冨伐鍏凤紝鍙姞杞界洰鏍?skill銆?

    涓?deep_agent() 鐨勫叧閿樊寮傦細
      - 绮剧畝 system prompt锛堟棤 skill-creator/tool-creator 鎸囦护锛?
      - 涓嶅寘鍚?propose_skill_save / propose_tool_save 绛夊厓宸ュ叿
      - 涓嶅姞杞藉閮ㄦ墿灞曞伐鍏凤紙Tools/锛?
      - 鍙寚瀹氬彧鍔犺浇鐗瑰畾 skill sources
    """
    from backend.task_settings import TaskSettings as _TS
    ts = _TS()
    model = get_llm_model(model_config, max_tokens_override=ts.max_tokens)

    eval_tools = [web_search, web_crawl]

    middleware = SSEMonitoringMiddleware(
        agent_name="EvalAgent",
        parent_agent=None,
        verbose=False,
    )

    sandbox = FullSandboxBackend(
        session_id=session_id,
        user_id="eval_runner",
        base_dir=_WORKSPACE_DIR,
        execute_timeout=ts.sandbox_exec_timeout,
        max_output_chars=ts.max_output_chars,
    )

    actual_workspace = sandbox.workspace
    sandbox_info = None
    ctx = await sandbox.get_context()
    if ctx.get("success"):
        sandbox_info = ctx.get("data")

    system_prompt = _get_eval_system_prompt(actual_workspace, sandbox_info)

    agent_kwargs: Dict[str, Any] = {
        "model": model,
        "tools": eval_tools,
        "middleware": [middleware],
        "system_prompt": system_prompt,
    }

    # 鏋勫缓鍚庣锛堝惈 skill 璺敱锛?
    routes = {}
    resolved_sources: List[str] = []

    if skill_sources:
        for src in skill_sources:
            if src == _BUILTIN_SKILLS_ROUTE and os.path.isdir(_BUILTIN_SKILLS_DIR):
                routes[_BUILTIN_SKILLS_ROUTE] = FilesystemBackend(
                    root_dir=_BUILTIN_SKILLS_DIR, virtual_mode=True,
                )
                resolved_sources.append(_BUILTIN_SKILLS_ROUTE)
            elif src == _EXTERNAL_SKILLS_ROUTE and os.path.isdir(_EXTERNAL_SKILLS_DIR):
                routes[_EXTERNAL_SKILLS_ROUTE] = FilteredFilesystemBackend(
                    root_dir=_EXTERNAL_SKILLS_DIR, virtual_mode=True,
                    blocked_skills=set(),
                )
                resolved_sources.append(_EXTERNAL_SKILLS_ROUTE)
    else:
        if os.path.isdir(_EXTERNAL_SKILLS_DIR):
            routes[_EXTERNAL_SKILLS_ROUTE] = FilteredFilesystemBackend(
                root_dir=_EXTERNAL_SKILLS_DIR, virtual_mode=True,
                blocked_skills=set(),
            )
            resolved_sources.append(_EXTERNAL_SKILLS_ROUTE)

    if routes:
        agent_kwargs["backend"] = lambda rt: CompositeBackend(default=sandbox, routes=routes)
    else:
        agent_kwargs["backend"] = sandbox

    if resolved_sources:
        agent_kwargs["skills"] = resolved_sources

    agent = create_deep_agent(**agent_kwargs)
    logger.info(f"[EvalAgent] session={session_id}, workspace={actual_workspace}, skills={resolved_sources}")
    return agent, middleware
