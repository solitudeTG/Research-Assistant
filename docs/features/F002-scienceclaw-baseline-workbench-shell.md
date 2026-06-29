---
id: F002
doc_kind: feature
status: active
owner: solitudeTG
created: 2026-06-28
updated: 2026-06-28
---

# F002: ScienceClaw Baseline Workbench Shell

## Goal

确保 Research Assistant 以 ScienceClaw 作为可运行 application shell 和工程底座，而不是重写一套独立工作台。

## Vision Anchor

- 原始请求或来源：`AGENTS.md`、`F001`、`docs/baseline-import-notes.md`。
- 用户痛点或工程问题：科研工作台需要稳定的聊天壳、ActivityPanel、文件/产物面板、沙箱、SSE trace 和 Docker Compose 编排；从零重写会把主要风险转移到基础设施而非科研能力。
- 期望结果：Research Assistant 在 ScienceClaw 现有架构、UI 和服务编排上增量融合科研能力。
- 非目标或边界：不重建独立 UI 体系；不把 landing page 当主体验；不因为局部不满意而替换整套 application shell。
- Exit Gate 对照来源：本 Feature、`F001`、`docs/baseline-import-notes.md`、`AGENTS.md`。

## Feature Intake

- Original problem: Research Assistant needs a runnable workbench shell before research-specific capabilities can be verified.
- User pain point: Rebuilding infrastructure would delay paper RAG, evidence audit, trace, and artifact workflows.
- Capability promise: Keep ScienceClaw as the inherited shell for UI, chat, panels, sandbox, trace, and compose orchestration.
- Non-goals: Do not replace ScienceClaw wholesale unless an explicit Research Assistant target is blocked and rollback criteria are documented.
- Acceptance source: `AGENTS.md`, `F001`, and baseline import notes.
- Open questions: Which ScienceClaw legacy features should be hidden or trimmed when they do not serve research workflows.

## Capability Contract

- The main user surface remains the ScienceClaw workbench shell.
- Chat is the primary interaction surface.
- ActivityPanel / trace panel remains visible for real backend events.
- File / artifact panel remains the delivery surface for research artifacts.
- Docker Compose remains the default local orchestration boundary unless a later ADR changes it.

## Decision Context

### Why

ScienceClaw already provides the operational shell needed for an Agent research workbench. Reusing it keeps the first capability increments focused on research evidence, not framework construction.

### Why Not

An independent Research Assistant shell was rejected because it would duplicate UI, orchestration, trace, and file-management infrastructure without proving a stronger research workflow.

### If Modifying This Area, Check

- `F001` project scope and UI rules.
- `docs/baseline-import-notes.md`.
- Frontend build/type-check and any affected backend route tests.
- Whether the change preserves visible trace and artifact surfaces.

## Current Status

In Progress. ScienceClaw baseline is present and being adapted incrementally.

## Links

### Evidence

- [Baseline import notes](../baseline-import-notes.md)
- [EV-001 Feature Governance Split Validation](../evidence/EV-001-feature-governance-split-validation.md)

### Decisions / ADRs

- [ADR-001 P0 Research Data and Retrieval Stack](../decisions/ADR-001-p0-research-data-and-retrieval-stack.md)

### Lessons

- None yet.

### Specs / Plans

- [F001 Feature Map and Rules Spec](../specs/F001-feature-map-and-rules-spec.md)

### Related Features

- [F001 Project Vision and Scope](F001-project-vision-and-scope.md)
- [F008 Trace Honesty and Activity Panel](F008-trace-honesty-activity-panel.md)

### External Context

- [THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md)

## Acceptance Criteria

- [x] Repository contains the imported ScienceClaw application shell.
- [x] Project rules state that ScienceClaw is the baseline for incremental development.
- [ ] Research-specific UI additions remain consistent with ScienceClaw workbench style.
- [ ] Any replacement of ScienceClaw infrastructure documents the blocked research goal, why incremental adaptation is insufficient, acceptance criteria, and rollback path.

## Acceptance Map

| Claim | Acceptance | Evidence | Status |
| --- | --- | --- | --- |
| ScienceClaw is the inherited shell. | The repository keeps `ScienceClaw/` and project docs define it as the application baseline. | `ScienceClaw/`, `AGENTS.md`, `F001`, baseline import notes. | Verified |
| Research UI should extend the workbench, not replace it. | Chat, ActivityPanel, file/artifact panel, and report preview remain the expected UI surfaces. | `AGENTS.md` and `F001` UI/workbench constraints. | Partial |

## State Timeline

| Date | State | Trigger | Evidence | Note |
| --- | --- | --- | --- | --- |
| 2026-06-28 | active | Feature split from F001 | This Feature and `INDEX.md` | Created during Feature governance cleanup. |

## Patch History

| Patch | Date | Commit | Symptom | Root Cause | Protection | Status |
| --- | --- | --- | --- | --- | --- | --- |
| F002.1 | 2026-06-29 | `146727e` | Long research prompts containing paper titles or filenames were visually clipped inside the user message bubble. | User message HTML did not have long-token wrapping rules, while the gradient bubble used `overflow-hidden`. | Frontend contract requires `.user-message-content` with `overflow-wrap: anywhere` and `word-break: break-word`. | verified |

## Evidence

Detailed historical evidence remains in `F001` until each workstream moves its verification records into the owning Feature.
- 2026-06-29 user bubble layout verification: `pytest ScienceClaw/backend/tests/test_research_frontend_contracts.py -q` -> `37 passed`; `npm.cmd run type-check` -> passed; `npm.cmd run build` -> passed with existing Browserslist/CSS/chunk-size warnings. Browser automation reached the authenticated chat UI, but did not produce a stable target user-bubble DOM assertion.

## Recovery Snapshot

- Read first: `F001`, this Feature, `docs/baseline-import-notes.md`.
- Current capability state: Baseline shell exists; research-specific adaptation continues inside it.
- Known risks: Accidental UI redesign or infrastructure replacement could drift from the project direction.
- Next safe action: Attribute shell/UI infrastructure changes here before implementation.
- Unblock condition: None.

## Next Step

When the next shell or UI infrastructure change occurs, move its concrete verification evidence from `F001` into this Feature.
