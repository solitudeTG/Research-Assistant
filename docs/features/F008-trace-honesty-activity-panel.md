---
id: F008
doc_kind: feature
status: active
owner: solitudeTG
created: 2026-06-28
updated: 2026-06-29
---

# F008: Trace Honesty and Activity Panel

## Goal

保证 ActivityPanel / trace panel 只展示真实发生的后端事件、工具事件和工作流步骤，不为展示效果伪造 Agent、并行关系、证据或 workflow state。

## Vision Anchor

- 原始请求或来源：`AGENTS.md` 多 Agent 与 UI 军规、`F001`。
- 用户痛点或工程问题：科研工作台的过程可观察性只有在 trace 真实时才可信。
- 期望结果：上传、解析、索引、检索、回答、报告、工具验证等步骤以真实 step/done/failed/deferred 事件进入 UI。
- 非目标或边界：本 Feature 不负责决定业务能力本身，只负责事件真实性和展示边界。
- Exit Gate 对照来源：本 Feature、route tests、SSE/ActivityPanel checks、UI E2E。

## Feature Intake

- Original problem: Research workflows need observable, truthful process state.
- User pain point: Fake traces make the system look capable while hiding failures or skipped steps.
- Capability promise: Display only real backend events and preserve failure/deferred states.
- Non-goals: Do not invent decorative workflow visualizations or simulated agents.
- Acceptance source: `AGENTS.md`, `F001`, upload/report/validation trace tests and UI E2E.
- Open questions: Future multi-agent UI state mapping should be added only when real agent lifecycles exist.

## Capability Contract

- ActivityPanel receives real backend trace events.
- Failed or deferred steps attach to the actual failed/deferred operation.
- UI can simplify or group events, but cannot invent missing agents, tools, parallelism, or evidence.
- Tool validation and research workflows expose pass/fail metadata where available.

## Decision Context

### Why

Research users need to know whether an answer came from successful retrieval, failed parsing, missing evidence, or a degraded path.

### Why Not

Decorative or simulated trace was rejected because it undermines evidence auditability and multi-agent honesty.

### If Modifying This Area, Check

- `AGENTS.md` trace honesty and multi-agent rules.
- Route tests for failed/deferred events.
- UI E2E that inspects ActivityPanel steps.
- Any tool-validation trace contract.

## Current Status

Completed for MVP scope.

ActivityPanel and trace surfaces now expose real upload, parse, index, retrieval, report, tool validation, runtime-result audit, source-quality, context-boundary, and research sidecar metadata without inventing agent/tool/parallel states. Future multi-agent lifecycle UI remains out of scope until real agent lifecycles exist.

## Links

### Evidence

- [EV-001 Feature Governance Split Validation](../evidence/EV-001-feature-governance-split-validation.md)
- Historical verification currently recorded in [F001](F001-project-vision-and-scope.md).

### Decisions / ADRs

- None.

### Lessons

- None yet.

### Specs / Plans

- [F001 Feature Map and Rules Spec](../specs/F001-feature-map-and-rules-spec.md)

### Related Features

- [F002 ScienceClaw Baseline Workbench Shell](F002-scienceclaw-baseline-workbench-shell.md)
- [F003 Research Document Ingestion](F003-research-document-ingestion.md)
- [F007 Research Artifact Generation](F007-research-artifact-generation.md)

### External Context

- None.

## Acceptance Criteria

- [x] Upload/parse/index/retrieval/report steps appear only when emitted by backend flow.
- [x] Failed and deferred operations are represented as such.
- [x] UI does not invent Agent/tool/parallel states.
- [x] Tool validation trace includes real validation result metadata.

## Acceptance Map

| Claim | Acceptance | Evidence | Status |
| --- | --- | --- | --- |
| Upload trace exposes real workflow steps. | Upload path emits separate upload, parse, and index step events, including failed/deferred states. | Historical upload trace evidence from `F001`; current research backend suite passed on 2026-06-29. | MVP done |
| Answer/report traces are honest. | Retrieval, admission, answer, report, memory lifecycle, and report completion metadata are emitted from actual route/backend flow. | Historical route trace, context-boundary trace, report failure/completion, and F011 skipped-retrieval verification. | MVP done |
| Tool validation/runtime traces preserve process boundaries. | Tool validation and runtime-result audit expose pass/fail/result metadata as process trace with `citation_evidence=false`. | Historical tool validation, runtime result-contract, audit API/export/UI evidence from `F001`. | MVP done |
| ActivityPanel does not invent workflow state. | ActivityPanel renders real event metadata and answer-attached research sidecars; future multi-agent states are not shown until real lifecycles exist. | F008.1 frontend/browser verification plus current frontend contracts. | MVP done |

## State Timeline

| Date | State | Trigger | Evidence | Note |
| --- | --- | --- | --- | --- |
| 2026-06-28 | active | Feature split from F001 | This Feature and `INDEX.md` | Created to own trace honesty and ActivityPanel recovery. |
| 2026-06-29 | patched | User clarified that RAG evidence/audit belongs in the right reasoning panel | Frontend contract tests, type-check, build, browser E2E | F008.1 adds an ActivityPanel research sidecar fed by real answer metadata, without inventing backend trace events. |
| 2026-06-29 | MVP completed | F001 historical evidence migrated to owning Feature | Current research backend suite and AgentMentor strict check | Real multi-agent lifecycle display remains future scope. |

## Patch History

| Patch | Date | Commit | Symptom | Root Cause | Protection | Status |
| --- | --- | --- | --- | --- | --- | --- |
| F008.1 | 2026-06-29 | `f18d0cf` | The right ActivityPanel showed evidence admission telemetry but not the actual answer citations/audit sidecar. | Research answer metadata was only rendered by ChatMessage, leaving ActivityPanel underused for process/audit inspection. | Frontend contract requires `displayResearchSidecar` and ActivityPanel sections for `研究证据`, `引用证据`, `证据审计`, and `上下文边界`; browser E2E verified the sidecar appears in the right panel. | verified |

## Evidence

Historical trace/ActivityPanel evidence migrated from `F001`:

- Upload route tests verified separate upload, parse, index, and failure/deferred trace states.
- Answer/report route tests verified retrieval/admission/answer/report completion and failure events, skipped retrieval wording, context-boundary metadata, and context-only memory lifecycle events.
- Source-quality tests verified web/database source-quality metadata and non-HTTPS warnings appear in real ingestion trace metadata and ActivityPanel.
- Tool validation/runtime tests verified sandbox validation pass/fail trace, typed result contracts, runtime result summaries, persisted runtime-result audit, pack filtering, export manifests, and file export actions as process trace only.
- Browser/UI E2E verified ActivityPanel showed real upload/parse/index/retrieval/report steps and file-panel artifacts for the uploaded-paper pipeline.

- 2026-06-29 ActivityPanel verification: `pytest ScienceClaw/backend/tests/test_research_frontend_contracts.py -q` -> `35 passed`.
- 2026-06-29 frontend verification: `npm.cmd run type-check` -> passed; `npm.cmd run build` -> passed with existing warnings.
- Browser E2E on session `2ifbtVAgF5jS26d9pUq93Z`: the right panel at x≈984, width≈600 contained `推理完成`, `任务进度`, `研究证据 5`, `证据审计`, `引用证据`, and `上下文边界`.
- Current document-convergence verification: `$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python -m pytest ScienceClaw\backend\tests -k research -q --basetemp .pytest_tmp\progress-audit` -> `178 passed`; `knowledge_check.py --strict` -> 0 errors, 0 warnings.

## Recovery Snapshot

- Read first: this Feature, F002, `AGENTS.md`.
- Current capability state: MVP trace honesty and ActivityPanel research sidecar contract is complete.
- Known risks: Future multi-agent UI could drift into simulated workflow state if not tied to backend events.
- Next safe action: Attribute trace/UI event changes here and verify route plus UI checks.
- Unblock condition: None.

## Next Step

Before adding multi-agent UI, create the real backend lifecycle events first and verify ActivityPanel renders only those events.
