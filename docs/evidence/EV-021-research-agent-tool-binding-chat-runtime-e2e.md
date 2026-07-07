---
id: EV-021
doc_kind: evidence
feature: F021
feature_refs:
  - docs/features/F021-research-agent-capability-binding.md
scope: Research Agent Tool binding live chat runtime E2E
created: 2026-07-06
updated: 2026-07-06
---

# EV-021: Research Agent Tool Binding Chat Runtime E2E

## Supports Claim

F021 Tool bindings are not only saved by the Research Agents page; they are consumed by chat runtime on the next turn.

The live browser E2E verifies both directions:

- Associate `audit_evidence_claims` with `paper_reader_worker` in the real Research Agents UI.
- Validate/enable the edited agent.
- Open a real chat session and start `/sessions/{session_id}/chat`.
- Confirm the chat runtime capability snapshot includes `paper_reader_worker.tools = ["read_research_evidence", "audit_evidence_claims"]`.
- Return to Research Agents UI and cancel the `audit_evidence_claims` association.
- Validate/enable the edited agent again.
- Open a second real chat session and start `/sessions/{session_id}/chat`.
- Confirm the chat runtime capability snapshot now includes only `paper_reader_worker.tools = ["read_research_evidence"]`.

## Verification Scope

Scope includes Research Agents UI Tool association/cancellation, backend validation/enablement after those UI edits, and chat runtime consumption of the resulting enabled subagent definition on the next chat turn.

Out of scope: proving the model autonomously chooses to invoke `paper_reader_worker`, changing Supervisor delegation policy, or treating capability snapshots as citation evidence.

## Live Environment

- Frontend: production `dist` served through the local same-origin proxy at `http://127.0.0.1:4176`.
- Backend: running Docker service `research-assistant-backend-1`, exposed through the proxy to the browser.
- Auth: local admin login through the real login page.
- UI path: `/chat/research-agents` for Tool association/cancellation.
- Chat path: real `/chat/{session_id}` pages plus real `/api/v1/sessions/{session_id}/chat` SSE requests from the browser context.

## Checks

```powershell
$env:PYTHONPATH='ScienceClaw'
python -m pytest ScienceClaw\backend\tests\test_research_tool_runtime.py -k "research_subagents or registry_subagent or bound_external_tool or active_tool_packs" -q --basetemp .pytest_tmp\f021-runtime-focused
python -m pytest ScienceClaw\backend\tests\test_research_subagents.py -q --basetemp .pytest_tmp\f021-subagents-focused

python .pytest_tmp\f021_chat_runtime_e2e.py
```

## Results

- Runtime focused tests: `4 passed, 13 deselected`.
- Subagent contract tests: `15 passed`.
- Live UI + chat runtime E2E: passed.

## Runtime Evidence

Associated state:

```json
{
  "associated_session": "GYaPmyF4fdKjgWjwZpukjs",
  "associated_tools": ["read_research_evidence", "audit_evidence_claims"],
  "active_tool_packs": []
}
```

Cancelled state:

```json
{
  "cancelled_session": "9cHkdFJ8EWVvinFnhNf9fG",
  "cancelled_tools": ["read_research_evidence"],
  "active_tool_packs": []
}
```

The empty `active_tool_packs` value is intentional: subagent Tool binding is a concrete subagent authorization boundary and does not require exposing the same Tool Pack to the main Agent for that turn.

## Artifacts

- Screenshot: `docs/evidence/EV-021-research-agent-tool-binding-chat-runtime-e2e.png`
- Runtime summary: `docs/evidence/EV-021-research-agent-tool-binding-chat-runtime-e2e-summary.json`

## Limitations

- The E2E verifies runtime configuration consumption at chat start, not model choice to invoke the custom subagent.
- The test uses built-in research tools for deterministic verification. External Tools Library runtime exposure is covered by focused backend tests for explicitly bound external tools.
- The runtime snapshot is process trace and should not be rendered or cited as research evidence.

## Notes

The test restores `paper_reader_worker` after execution. The chat runtime evidence comes from the real DeepAgent subagent configuration snapshot emitted at chat start; it is process trace, not citation evidence and not a fabricated subagent/tool call.
