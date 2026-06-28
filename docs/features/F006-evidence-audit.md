---
id: F006
doc_kind: feature
status: active
owner: solitudeTG
created: 2026-06-28
updated: 2026-06-28
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

In Progress. Evidence Audit has multiple verified slices recorded in `F001`.

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
| Audit state is visible in outputs. | Chat and Markdown reports expose audit summary and claim checks. | Historical frontend/report evidence in `F001`. | Partial |

## State Timeline

| Date | State | Trigger | Evidence | Note |
| --- | --- | --- | --- | --- |
| 2026-06-28 | active | Feature split from F001 | This Feature and `INDEX.md` | Created to own audit behavior and recovery. |

## Patch History

None yet.

## Evidence

Move focused audit verification here when the next audit change lands.

## Recovery Snapshot

- Read first: this Feature, F004, F007 if report output is involved.
- Current capability state: Evidence Audit exists with historical verification in `F001`.
- Known risks: Lexical support scoring may not cover all semantic entailment cases.
- Next safe action: Attribute audit changes here and verify focused audit plus affected output tests.
- Unblock condition: None.

## Next Step

Migrate audit-specific Acceptance Map rows from `F001` into this Feature as the next document cleanup slice.
