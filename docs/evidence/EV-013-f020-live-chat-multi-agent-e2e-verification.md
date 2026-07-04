---
id: EV-013
doc_kind: evidence
scope: feature
feature_refs:
  - docs/features/F020-multi-agent-subagent-registry.md
status: complete
owner: solitudeTG
created: 2026-07-03
updated: 2026-07-03
---

# EV-013: F020 Live Chat Multi-Agent E2E Verification

## Supports Claim

F020 的真实 chat UI 旅程可以在一次复杂科研任务中触发 DeepAgents `task` subagent 调用，并在 ActivityPanel / trace 中呈现真实发生的 Reader Worker 与 Auditor Agent 生命周期；Reader / Auditor 输出保持为 context/process trace，不升级为 citation evidence。

## Verification Scope

- Live UI: in-app browser opened `http://127.0.0.1:5177` and submitted the task through the chat textbox.
- Backend: existing Docker backend on `http://127.0.0.1:12001`.
- Frontend: temporary Vite dev server on `http://127.0.0.1:5177`, pointing to the live backend.
- Auth: local UI login with the default development admin account.
- Session: `8RU57a4VFZk3kTQkiyA36W`.
- Task shape: complex multi-material Chinese research synthesis, explicitly asking Supervisor to use `paper_reader_worker` and `research_auditor` under the F020 boundary.

## Artifacts

- Screenshot: [EV-013-f020-live-chat-multi-agent-e2e.png](EV-013-f020-live-chat-multi-agent-e2e.png)
- Structured event capture: [EV-013-f020-live-chat-multi-agent-e2e-events.json](EV-013-f020-live-chat-multi-agent-e2e-events.json)
- Runtime workspace outputs:
  - `workspace/8RU57a4VFZk3kTQkiyA36W/original_materials.json`
  - `workspace/8RU57a4VFZk3kTQkiyA36W/supervisor_draft.md`
  - `workspace/8RU57a4VFZk3kTQkiyA36W/audit_report.md`

## Checks

| Check | Result | Evidence |
| --- | --- | --- |
| UI login and chat submission use the real app surface. | Pass | Browser journey created session `8RU57a4VFZk3kTQkiyA36W`; screenshot shows Chat UI, final state, and ActivityPanel. |
| Session completed. | Pass | Event capture records `status=completed`, `assistant_count=1`, `done_count=1`. |
| Reader Workers run as real subagents. | Pass | Two `task` calls requested `paper_reader_worker`; both completed with `agent=paper_reader_worker`, `phase=completed`, `boundary=context_only`, `citation_evidence=false`. |
| Auditor Agent runs as an independent worker. | Pass | One `task` call requested `research_auditor`; it completed with `agent=research_auditor`, `phase=completed`, `boundary=process_trace`, `citation_evidence=false`. |
| ActivityPanel shows real lifecycle/tool activity. | Pass with caveat | Screenshot shows actual task/tool rows from the live run. Completion events carry lifecycle metadata; calling events expose subagent type through task args rather than the normalized lifecycle metadata envelope. |
| Evidence boundary is preserved. | Pass | Subagent completion metadata marks Reader notes as `context_only` and Auditor output as `process_trace`; neither is marked as citation evidence. |
| Focused backend F020 tests pass. | Pass | `python -m pytest ... -q --basetemp=.pytest_tmp_verify` returned `15 passed, 97 warnings`. |
| Frontend type contract passes. | Pass | `npm.cmd run type-check` under `ScienceClaw/frontend` returned success. |
| Harness strict check has no new F020/EV-013 template errors. | Partial | `knowledge_check.py --strict` still reports 8 historical errors in F018/F019/EV-009/EV-010; F020 and EV-013 are no longer listed. |
| Temporary live UI server is cleaned up. | Pass | Port `5177` no longer has a listening process after stopping the temporary Vite process. |

## Results

Pass with caveats.

- The live chat journey completed through the real UI and backend.
- The run produced two completed `paper_reader_worker` task events with `boundary=context_only` and `citation_evidence=false`.
- The run produced one completed `research_auditor` task event with `boundary=process_trace` and `citation_evidence=false`.
- ActivityPanel rendered real tool/task activity from this run.
- Caveats are limited to lifecycle metadata normalization on calling events, an extra real `general-purpose` task invocation, and the fact that this test used an explicit complex prompt.
- Focused backend and frontend contract checks passed after the live UI run.
- Global Harness strict validation remains blocked by pre-existing F018/F019/EV-009/EV-010 template gaps, not by F020 or EV-013.

## Notes

- DeepAgents also invoked a real `general-purpose` task for the Supervisor draft step. This is not fake UI state, but it is outside the intended narrow F020 first-slice vocabulary of `Supervisor + Auditor Agent + Reader Workers`. If F020 needs a strict allowlist, the next increment should constrain or relabel this path.
- `task` calling/start events do not yet carry the same `metadata.subagent_lifecycle` envelope as completion events. The UI can still display the subagent name from `args_subagent_type`, but the lifecycle contract should be tightened if started/deferred/failed states need the same normalized metadata.
- The prompt explicitly requested the F020 subagents. This verifies the live UI and runtime integration path, but it does not prove autonomous implicit selection for every complex task.
- The visible final chat answer mainly summarized generated artifacts; the substantive draft and audit details were in workspace files and trace. This is acceptable for trace verification, but product UX may later require richer inline synthesis.

## Limitations

This evidence does not cover Registry editing, enable/disable rollback, validation examples, recent-run previews, or a strict autonomous trigger policy. It covers the end-to-end live chat path for invoking and observing F020 subagents from the UI.
