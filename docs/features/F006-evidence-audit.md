---
id: F006
doc_kind: feature
status: active
owner: solitudeTG
created: 2026-06-28
updated: 2026-06-29
---

# F006: Evidence Audit

## Goal

检查研究答案和报告中的 claim 是否被 citation evidence 支撑，并把 unsupported、invalid-source 或弱支撑结论显式暴露。

## Vision Anchor

- 原始请求或来源：`F001`、`AGENTS.md` 证据边界军规。
- 用户痛点或工程问题：有 citation 不等于 claim 被支持；系统需要检查结论和来源之间的关系。
- 期望结果：Evidence Audit 对 answer/report claim 产生可展示、可持久化、可恢复的审计结果。
- 非目标或边界：本 Feature 不负责生成新的 evidence，也不替代人工同行评审。
- Exit Gate 对照来源：本 Feature、audit tests、report/Chat audit rendering tests。

## Feature Intake

- Original problem: Research outputs need claim-level support checking.
- User pain point: Reports can look credible while containing unsupported or overclaimed conclusions.
- Capability promise: Audit claims against citation evidence and expose approved/unsupported/invalid-source states.
- Non-goals: Do not claim full scientific truth verification or source-quality scoring here.
- Acceptance source: `F001`, `AGENTS.md`, focused audit tests.
- Open questions: Stronger semantic entailment and source-quality scoring remain future work.

## Capability Contract

- Audit answer/report claims against eligible citation evidence.
- Distinguish approved, unsupported, and invalid-source claims.
- Persist audit results where answer/report subjects need recovery.
- Surface audit summaries and claim checks in Chat and Markdown reports.
- Keep context-only memory visible but non-citation.

## Decision Context

### Why

Citation presence alone is insufficient. A claim may cite a valid source while still overclaiming beyond the quote.

### Why Not

Hiding unsupported claims was rejected because research users need to see evidence gaps and unresolved conclusions.

### If Modifying This Area, Check

- F004 citation evidence boundary.
- Audit support-score, explicit-label, and invalid-source tests.
- Chat audit panel and Markdown Claim Checks.

## Current Status

In Progress. Evidence Audit has multiple verified slices recorded in `F001`; answer-level audit visibility now lives in ActivityPanel rather than below the Chat answer card.

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

- [F004 Citation Evidence Boundary](F004-citation-evidence-boundary.md)
- [F007 Research Artifact Generation](F007-research-artifact-generation.md)

### External Context

- None.

## Acceptance Criteria

- [ ] Audit approves only claims supported by eligible citation evidence.
- [ ] Unsupported and invalid-source claims remain visible as gaps.
- [ ] Audit results can be persisted and recovered for answer/report subjects.
- [ ] Chat and Markdown reports expose audit state without overstating trust.

## Acceptance Map

| Claim | Acceptance | Evidence | Status |
| --- | --- | --- | --- |
| Evidence Audit checks claim support. | Claims receive approved/unsupported/invalid-source status. | Historical audit evidence in `F001`. | Partial |
| Audit state is visible in outputs. | Chat answer audit now appears in ActivityPanel; Markdown reports still carry report audit sections. | Frontend contract and browser E2E from 2026-06-29. | Partial |

## State Timeline

| Date | State | Trigger | Evidence | Note |
| --- | --- | --- | --- | --- |
| 2026-06-28 | active | Feature split from F001 | This Feature and `INDEX.md` | Created to own audit behavior and recovery. |
| 2026-06-29 | patched | User identified Evidence Audit as process-state data that belongs in the right reasoning panel | Frontend contract tests, type-check, build, browser E2E | F006.1 moved answer audit summary and claim checks out of ChatMessage and into ActivityPanel. |
| 2026-06-29 | patched | User clarified that audit detail should not flood the ActivityPanel by default | Frontend contract tests, type-check, build | F006.2 keeps approved claims visible and collapses unsupported/invalid audit claims behind an explicit disclosure. |

## Patch History

| Patch | Date | Commit | Symptom | Root Cause | Protection | Status |
| --- | --- | --- | --- | --- | --- | --- |
| F006.1 | 2026-06-29 | `f18d0cf` | Evidence Audit appeared as a large block below each answer, making the Chat stream carry process/audit data. | Audit display was coupled to the answer component instead of the ScienceClaw ActivityPanel semantics. | Frontend contract requires `证据审计` to be rendered through ActivityPanel research sidecar and absent from ChatMessage answer cards. | verified |
| F006.2 | 2026-06-29 | `d2d986a` | ActivityPanel rendered every audit claim by default, so long answers could display dozens of unsupported claim rows. | Claim-level audit data was technically correct but lacked a progressive disclosure boundary. | Frontend contract requires approved claims to render by default while unsupported/invalid claims are collapsed behind `unsupportedAuditClaimsExpanded`. | verified |

## Evidence

- 2026-06-29 audit UI verification: `pytest ScienceClaw/backend/tests/test_research_frontend_contracts.py -q` -> `35 passed`.
- 2026-06-29 frontend verification: `npm.cmd run type-check` -> passed; `npm.cmd run build` -> passed with existing warnings.
- Browser E2E on project `E2E UI链路验证 06290349`: right ActivityPanel showed `证据审计 partial` and claim status rows; the Chat answer card did not render the audit block.
- 2026-06-29 audit density verification: `pytest ScienceClaw/backend/tests/test_research_frontend_contracts.py -q` -> `36 passed`; `npm.cmd run type-check` -> passed; `npm.cmd run build` -> passed with existing Browserslist/CSS/chunk-size warnings. Browser automation reached the authenticated chat shell, but historical-session panel inspection timed out before a stable ActivityPanel DOM assertion.

## Recovery Snapshot

- Read first: this Feature, F004, F007 if report output is involved.
- Current capability state: Evidence Audit exists with historical verification in `F001`; answer audit sidecar is visible in ActivityPanel.
- Known risks: Lexical support scoring may not cover all semantic entailment cases.
- Next safe action: Attribute audit changes here and verify focused audit plus affected output tests.
- Unblock condition: None.

## Next Step

Migrate audit-specific Acceptance Map rows from `F001` into this Feature as the next document cleanup slice.
