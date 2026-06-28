---
id: F004
doc_kind: feature
status: active
owner: solitudeTG
created: 2026-06-28
updated: 2026-06-28
---

# F004: Citation Evidence Boundary

## Goal

明确 Research Assistant 中哪些来源可以成为 citation evidence，哪些只能作为 context 或 trace，防止 memory、模型推理或工具日志伪装成证据。

## Vision Anchor

- 原始请求或来源：`AGENTS.md` 证据边界军规、`F001`、`ADR-001`。
- 用户痛点或工程问题：科研结论需要可审查来源；没有 source identity 的摘要、记忆或日志不能支撑 citation。
- 期望结果：paper / web / database evidence 可作为 citation evidence；memory、LLM reasoning、tool logs、process trace 只能作为 context-only 或 trace。
- 非目标或边界：本 Feature 不负责具体检索排名、报告版式或多 Agent 编排。
- Exit Gate 对照来源：本 Feature、source identity 测试、retrieval/audit/report 边界测试。

## Feature Intake

- Original problem: Research answers need a strict source eligibility boundary.
- User pain point: Users cannot audit conclusions if context, memory, and trace are mixed with citations.
- Capability promise: Enforce and display a paper/web/database citation-evidence contract.
- Non-goals: Do not classify every source quality dimension or build a full web crawler here.
- Acceptance source: `AGENTS.md`, `F001`, `ADR-001`, focused evidence-boundary tests.
- Open questions: Source quality scoring beyond identity metadata remains future work.

## Capability Contract

- Citation evidence may come from paper, web, or database sources with source identity.
- Memory is always context-only and must not become citation evidence.
- LLM reasoning, tool logs, process trace, and source-less summaries must not become citation evidence.
- UI/report surfaces must distinguish citation evidence from context-only memory and process trace.

## Decision Context

### Why

The product promise is auditability. Evidence eligibility must be decided before presentation, not cleaned up after the answer is already displayed.

### Why Not

Treating all helpful context as evidence was rejected because it would make reports and answers look more certain than the backend can prove.

### If Modifying This Area, Check

- `AGENTS.md` evidence boundary rules.
- Retrieval filters for source identity.
- Evidence Audit source validity rules.
- Report and Chat citation rendering.

## Current Status

In Progress. Paper/web/database citation boundary has initial implementation evidence aggregated in `F001`.

## Links

### Evidence

- [EV-001 Feature Governance Split Validation](../evidence/EV-001-feature-governance-split-validation.md)
- Historical verification currently recorded in [F001](F001-project-vision-and-scope.md).

### Decisions / ADRs

- [ADR-001 P0 Research Data and Retrieval Stack](../decisions/ADR-001-p0-research-data-and-retrieval-stack.md)

### Lessons

- None yet.

### Specs / Plans

- [F001 Feature Map and Rules Spec](../specs/F001-feature-map-and-rules-spec.md)

### Related Features

- [F005 Hybrid Retrieval and Grounded Answering](F005-hybrid-retrieval-grounded-answering.md)
- [F006 Evidence Audit](F006-evidence-audit.md)
- [F007 Research Artifact Generation](F007-research-artifact-generation.md)

### External Context

- None.

## Acceptance Criteria

- [ ] Paper/web/database evidence can be represented with source identity.
- [ ] Incomplete web/database source identity is excluded from citation evidence.
- [ ] Memory appears only as context-only memory.
- [ ] UI/report wording avoids uploaded-paper-only claims when the contract is broader.

## Acceptance Map

| Claim | Acceptance | Evidence | Status |
| --- | --- | --- | --- |
| Citation evidence accepts paper/web/database sources. | Backend and frontend source-type contracts allow paper, web, and database evidence. | Historical tests in `F001`; move focused boundary evidence here on next change. | Partial |
| Memory is context-only. | Memory is stored and displayed separately from citation evidence. | Historical memory/report evidence in `F001`. | Partial |

## State Timeline

| Date | State | Trigger | Evidence | Note |
| --- | --- | --- | --- | --- |
| 2026-06-28 | active | Feature split from F001 | This Feature and `INDEX.md` | Created to own evidence eligibility boundaries. |

## Patch History

None yet.

## Evidence

Focused evidence-boundary verification should be moved here from `F001` during the next boundary change.

## Recovery Snapshot

- Read first: `AGENTS.md`, this Feature, `ADR-001`.
- Current capability state: Paper/web/database and context-only memory boundaries exist, but historical evidence is still concentrated in `F001`.
- Known risks: Wording drift can reintroduce paper-only assumptions or overstate evidence quality.
- Next safe action: Attribute source-type, citation, memory, or boundary wording changes here.
- Unblock condition: None.

## Next Step

Move source-type and memory-boundary evidence from `F001` into this Feature as follow-up cleanup.
