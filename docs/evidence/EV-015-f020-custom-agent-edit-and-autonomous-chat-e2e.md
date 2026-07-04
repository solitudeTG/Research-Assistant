---
id: EV-015
doc_kind: evidence
scope: feature
feature_refs:
  - docs/features/F020-multi-agent-subagent-registry.md
status: accepted
owner: solitudeTG
created: 2026-07-03
updated: 2026-07-03
---

# EV-015: F020 Custom Agent Edit and Autonomous Chat E2E

## Supports Claim

F020 的两个遗留缺口已经被真实 live UI 验收覆盖：

- Research Agents 页面可以编辑用户自定义 Agent，例如 `paper_reader_worker`；系统内置 `general-purpose` 仍然只读。
- 用户在 Chat 会话中提交未显式点名 subagent 的复杂科研综述任务时，Supervisor 能按任务复杂度先委派 Reader Worker，再委派 Auditor Agent。
- Reader Worker 输出保持 `context_only`，Auditor Agent 输出保持 `process_trace`，两者均为 `citation_evidence=false`。

## Verification Scope

Verified:

- Real Docker backend on `http://127.0.0.1:12001`.
- Real Vite frontend on `http://127.0.0.1:5173`.
- Real browser interaction through `/chat/research-agents` and `/chat`.
- Real authenticated backend session/event polling.
- Backend runtime using `DS_MODEL=qwen3.6-flash-2026-04-16`.

Not verified:

- Production deployment migration.
- Cross-model reliability beyond the configured qwen model.

## Checks

```powershell
docker exec research-assistant-backend-1 sh -lc "printf 'DS_MODEL='; printenv DS_MODEL"
```

Result: `DS_MODEL=qwen3.6-flash-2026-04-16`.

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python -m pytest ScienceClaw\backend\tests\test_research_subagents.py::test_auditor_tool_accepts_material_labels_without_crashing -q
```

Result: `1 passed, 1 warning`.

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python -m pytest ScienceClaw\backend\tests\test_research_tool_runtime.py::test_supervisor_prompt_guides_autonomous_research_subagent_delegation -q
```

Result: `1 passed, 1 warning`.

## Live UI Results

### Research Agents Custom Edit

Browser path: `http://127.0.0.1:5173/chat/research-agents`.

Observed:

- Registry displayed 3 agents.
- `general-purpose` showed `系统内置`, `只读`, `system_builtin`, `deepagents_builtin`, and the main edit button was disabled.
- `paper_reader_worker` showed `用户自定义`, `可编辑`, and exposed the edit panel.
- Saved `paper_reader_worker` with metadata:

```json
{
  "live_ui_e2e": true,
  "saved_from": "browser",
  "scenario": "f020_custom_agent_edit"
}
```

Backend readback:

```json
{
  "name": "paper_reader_worker",
  "validation_status": "draft",
  "live_ui_e2e": true,
  "saved_from": "browser",
  "scenario": "f020_custom_agent_edit"
}
```

### Chat Autonomous Multi-Agent E2E

Browser path: `http://127.0.0.1:5173/chat/KbKqyTdqftRwGrAZFTy7Py`.

User prompt did not explicitly ask to call Reader Worker or Auditor Agent. It asked for a complex research synthesis across materials A/B/C and an independent boundary check.

Final session state:

```json
{
  "session_id": "KbKqyTdqftRwGrAZFTy7Py",
  "status": "completed",
  "event_count": 652,
  "last_event_type": "done"
}
```

Observed real `task` calls:

```json
[
  {"subagent_type": "paper_reader_worker", "status": "calling"},
  {"subagent_type": "research_auditor", "status": "calling"}
]
```

Observed lifecycle metadata:

```json
[
  {
    "agent_name": "paper_reader_worker",
    "phase": "completed",
    "status": "completed",
    "boundary": "context_only",
    "citation_evidence": false
  },
  {
    "agent_name": "research_auditor",
    "phase": "completed",
    "status": "completed",
    "boundary": "process_trace",
    "citation_evidence": false
  }
]
```

Browser UI also showed the final answer with `citation evidence`, `context`, and `process trace` boundary language, plus tool entries for `task paper_reader_worker` and `task research_auditor`.

## Results

Pass.

- Custom Agent editing passed in the real Research Agents page.
- System built-in Agent read-only governance passed in the real Research Agents page.
- Autonomous complex Chat E2E passed with real `paper_reader_worker` and `research_auditor` task calls.
- Lifecycle boundary metadata passed: Reader is `context_only`, Auditor is `process_trace`, and both keep `citation_evidence=false`.
- Regression coverage passed for Auditor non-numeric material labels and Supervisor delegation prompt constraints.

## Regression Fixed During Verification

The first real Chat E2E against qwen called Auditor but skipped Reader. Root cause: Supervisor prompt allowed the model to treat `web_search` / direct self-reading as sufficient reading work. The prompt was hardened so `web_search`, `web_crawl`, direct self-reading, and `write_todos` do not satisfy Reader Worker delegation for two-or-more-material synthesis.

The earlier Auditor attempt also exposed a runtime bug: user-provided material labels such as `A/B/C` could be passed as `evidence_id`, while the deterministic audit payload expected an integer. `_citation_payloads` now preserves the label as `citation_label` and safely falls back to a sequence number for the internal integer id.

## Artifacts

- `ScienceClaw/backend/deepagent/agent.py`
- `ScienceClaw/backend/research_assistant/subagents.py`
- `ScienceClaw/backend/route/sessions.py`
- `ScienceClaw/backend/research_assistant/storage/repository.py`
- `ScienceClaw/backend/research_assistant/storage/database.py`
- `ScienceClaw/frontend/src/api/agent.ts`
- `ScienceClaw/frontend/src/pages/ResearchAgentsPage.vue`
- `ScienceClaw/backend/tests/test_research_subagents.py`
- `ScienceClaw/backend/tests/test_research_tool_runtime.py`

## Limitations

The qwen model followed the hardened delegation prompt in the verified run. This remains a prompt-guided Supervisor policy, not a deterministic router. If future model changes regress the behavior, the next product decision should be whether to add a lightweight runtime delegation guard or keep improving prompt-only autonomy.

## Notes

- Earlier live sessions in this verification run are intentionally treated as failed discovery evidence: one completed with Auditor only, and one exposed the `A/B/C` evidence-id parsing bug.
- The accepted live Chat E2E session is `KbKqyTdqftRwGrAZFTy7Py`.
- The accepted Research Agents edit used a temporary E2E display name/metadata on `paper_reader_worker`; validation status became `draft` as intended after editing. The local display name was restored after evidence capture to avoid leaving an E2E label in the development database.
