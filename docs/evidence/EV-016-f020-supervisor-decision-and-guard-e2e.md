---
id: EV-016
doc_kind: evidence
status: valid
owner: solitudeTG
scope: feature
feature_refs:
  - docs/features/F020-multi-agent-subagent-registry.md
created: 2026-07-03
feature: F020
---

# EV-016: F020 Supervisor Decision And Guard Live UI E2E

## Supports Claim

F020 now exposes inspectable Supervisor multi-agent decision metadata and preserves the simple/complex routing boundary in the real live UI:

- Simple factual Q&A stays single-agent.
- Complex multi-material synthesis with evidence-boundary checking delegates Reader Worker and Auditor Agent with real lifecycle events.
- ActivityPanel shows `multi_agent_decision` separately from actual subagent lifecycle, so decision intent and execution evidence remain distinguishable.

## Verification Scope

- Frontend: `http://127.0.0.1:5173/chat` and `http://127.0.0.1:5173/chat/research-agents`
- Backend: Docker service `research-assistant-backend-1`, health endpoint `http://127.0.0.1:12001/health`
- Browser: Playwright using local Chrome executable against the live Vite UI.
- Model environment: existing Docker backend runtime using the configured `MODEL_NAME` through compose-provided `DS_MODEL`.

## Checks

1. Opened `Research Agents` page through the live browser UI after logging in with the local development account.
2. Verified the Registry page shows `边界审计智能体`, `research_auditor`, `paper_reader_worker`, `general-purpose`, `系统内置`, and `用户自定义`.
3. Submitted a simple chat task through the live composer:
   - `什么是 DNA？请用一句话回答。`
4. Queried the resulting live session events through the authenticated browser context.
5. Submitted a complex chat task through the live composer:
   - Three labeled materials A/B/C.
   - Requested a short research synthesis.
   - Requested evidence-boundary checking.
   - Did not explicitly name any subagent.
6. Queried the resulting live session events and inspected ActivityPanel text.

## Results

### Research Agents UI

- Page URL: `http://127.0.0.1:5173/chat/research-agents`
- Result: pass.
- Observed `边界审计智能体` as the Chinese display name for `research_auditor`.
- Observed Registry type split:
  - `general-purpose`: system built-in, read-only.
  - `research_auditor` and `paper_reader_worker`: user-custom/custom governance entries.

### Simple Chat E2E

- Session: `JLC8fAB3ttD6sc7eVjt6np`
- Status: `completed`
- Event count: `26`
- Tool count: `0`
- Subagent lifecycle count: `0`
- Latest `multi_agent_decision`:

```json
{
  "enabled": false,
  "decision_source": "supervisor_delegation_guard",
  "reason": "no_multi_material_or_audit_requirement_detected",
  "selected_agents": [],
  "skipped_agents": ["paper_reader_worker", "research_auditor"],
  "trigger": "single_agent_default",
  "requires_reader": false,
  "requires_auditor": false
}
```

### Complex Chat E2E

- Session: `KTkunuCnaxF2BDQpkSXNxs`
- Status: `completed`
- Event count: `270`
- ActivityPanel showed `多 Agent 决策`.
- Latest `multi_agent_decision`:

```json
{
  "enabled": true,
  "decision_source": "supervisor_delegation_guard",
  "reason": "The task has multiple materials plus an evidence-boundary or trust-check requirement.",
  "selected_agents": ["paper_reader_worker", "research_auditor"],
  "skipped_agents": [],
  "trigger": "two_or_more_material_synthesis_with_boundary_audit",
  "requires_reader": true,
  "requires_auditor": true,
  "confidence": 0.86
}
```

Observed subagent lifecycle summary:

```json
[
  {
    "agent": "paper_reader_worker",
    "phase": "started",
    "status": "running",
    "source": "supervisor_delegation_guard",
    "boundary": "context_only",
    "citation": false
  },
  {
    "agent": "paper_reader_worker",
    "phase": "completed",
    "status": "completed",
    "source": "supervisor_delegation_guard",
    "boundary": "context_only",
    "citation": false
  },
  {
    "agent": "research_auditor",
    "phase": "started",
    "status": "running",
    "source": "supervisor_delegation_guard",
    "boundary": "process_trace",
    "citation": false
  },
  {
    "agent": "research_auditor",
    "phase": "completed",
    "status": "completed",
    "source": "supervisor_delegation_guard",
    "boundary": "process_trace",
    "citation": false
  }
]
```

Screenshot:

- `docs/evidence/EV-016-f020-supervisor-decision-live-ui.png`

## Artifacts

- Live simple chat session: `JLC8fAB3ttD6sc7eVjt6np`
- Live complex chat session: `KTkunuCnaxF2BDQpkSXNxs`
- Screenshot: `docs/evidence/EV-016-f020-supervisor-decision-live-ui.png`
- Focused verification commands:
  - `python -m pytest ScienceClaw\backend\tests\test_research_task_router.py ScienceClaw\backend\tests\test_research_tool_runtime.py::test_supervisor_guard_lifecycle_uses_explicit_decision_source ScienceClaw\backend\tests\test_research_tool_runtime.py::test_runner_task_calling_lifecycle_fallback_labels_deepagents_task ScienceClaw\backend\tests\test_research_session_routes.py::test_plan_mapping_preserves_multi_agent_decision_metadata ScienceClaw\backend\tests\test_research_agents_frontend_contract.py -q`
  - `npm.cmd run type-check`

## Limitations

- The guard intentionally covers only accepted strong conditions: simple single-agent turns, multi-material synthesis, and boundary/audit/trust checks.
- The guard is not a general Agent planner and does not replace model judgment for open-ended tasks.
- Reader/Auditor guard outputs remain `context_only` or `process_trace`; they are not citation evidence.

## Notes

An earlier live complex UI run on the current model completed without calling Reader or Auditor despite prompt guidance. EV-016 records the correction: prompt guidance remains, but accepted strong conditions now have a narrow Supervisor delegation guard so live behavior is reproducible.
