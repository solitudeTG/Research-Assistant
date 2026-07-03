---
id: F004
doc_kind: feature
status: active
owner: solitudeTG
created: 2026-06-28
updated: 2026-06-29
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

Completed for MVP scope.

The current MVP enforces a paper/web/database citation-evidence contract, excludes incomplete external source identities from retrieval, keeps memory/process/model context out of citations, and exposes boundary metadata in answer/report/ActivityPanel surfaces. This does not claim full source-quality scoring or automated web crawling.

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

- [x] Paper/web/database evidence can be represented with source identity.
- [x] Incomplete web/database source identity is excluded from citation evidence.
- [x] Memory appears only as context-only memory.
- [x] UI/report wording avoids uploaded-paper-only claims when the contract is broader.

## Acceptance Map

| Claim | Acceptance | Evidence | Status |
| --- | --- | --- | --- |
| Citation evidence accepts paper/web/database sources. | Backend, retrieval, audit, report, and frontend contracts allow paper, web, and database evidence with source identity. | Historical F001 web/database evidence tests, source-quality route tests, frontend source-ingestion contracts, and current research backend suite. | MVP done |
| Incomplete external source identity is excluded. | Retrieval returns web evidence only with URL and database evidence only with database name/query. | Historical retrieval identity-gate red/green verification from 2026-06-21; current research backend suite passed on 2026-06-29. | MVP done |
| Memory remains context-only. | Memory is stored, recalled, shown, promoted, and deleted as `source_type='memory'` / `context_only=true`, never as citation evidence. | Historical memory-boundary answer/report/route/frontend verification migrated from `F001`; current research backend suite passed on 2026-06-29. | MVP done |
| UI/report wording reflects the broader contract. | Answer/report routes, trace descriptions, Chat wording, report sidecars, and ActivityPanel context boundaries distinguish citation evidence, context-only memory, process trace, and model reasoning. | Historical generic wording and context-boundary manifest verification from `F001`; F004.1 UI boundary verification. | MVP done |

## State Timeline

| Date | State | Trigger | Evidence | Note |
| --- | --- | --- | --- | --- |
| 2026-06-28 | active | Feature split from F001 | This Feature and `INDEX.md` | Created to own evidence eligibility boundaries. |
| 2026-06-29 | patched | User clarified that full RAG evidence is process/audit UI, not answer-body UI | Frontend contract tests, type-check, build, browser E2E | F004.1 keeps Chat answer cards focused on final answer while ActivityPanel displays citation evidence. |
| 2026-06-29 | MVP completed | F001 historical evidence migrated to owning Feature | Current research backend suite and AgentMentor strict check | Source-quality scoring and automated source acquisition remain future scope. |

## Patch History

| Patch | Date | Commit | Symptom | Root Cause | Protection | Status |
| --- | --- | --- | --- | --- | --- | --- |
| F004.1 | 2026-06-29 | `f18d0cf` | Chat answers rendered full citation evidence cards below the final answer. | Early acceptance compressed "inspectable citation evidence" into the Chat answer card instead of preserving ScienceClaw's answer/process panel split. | Frontend contract requires ChatMessage answer cards to exclude citation/evidence panels and ActivityPanel to render source-type-aware citation evidence. | verified |

## Evidence

Historical citation-boundary evidence migrated from `F001`:

- Web evidence persistence/retrieval/session/UI/source-quality tests passed after adding `evidence_type='web'`, URL identity, retrieval timestamp, and source-quality metadata.
- Database evidence persistence/session/UI/source-quality tests passed after adding `evidence_type='database'`, database name, query, retrieval timestamp, and source-quality metadata.
- Retrieval identity-gate verification passed after incomplete web/database source identities were excluded from citation evidence.
- Generic citation-evidence wording tests passed for no-citation answers, answer/report routes, trace descriptions, mode metadata, tooltips, and report wording.
- Context-boundary manifest tests passed for answer payloads, report sidecars, route trace metadata, assistant messages, and frontend rendering.
- Context-only memory tests passed for storage constraints, same-user recall, promotion/revocation, relevance threshold, age decay, conflict marking, report display, and UI actions while preserving `citation_evidence=false` for memory.

- 2026-06-29 UI boundary verification: `pytest ScienceClaw/backend/tests/test_research_frontend_contracts.py -q` -> `35 passed`.
- 2026-06-29 frontend verification: `npm.cmd run type-check` -> passed; `npm.cmd run build` -> passed with existing Browserslist/CSS/chunk-size warnings.
- Browser E2E on session `2ifbtVAgF5jS26d9pUq93Z`: the assistant answer card did not contain `Citation evidence`, `引用证据`, `Evidence audit`, or `证据审计`; the right ActivityPanel contained `研究证据`, `引用证据`, and source-type labels.
- Current document-convergence verification: `$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python -m pytest ScienceClaw\backend\tests -k research -q --basetemp .pytest_tmp\progress-audit` -> `178 passed`; `knowledge_check.py --strict` -> 0 errors, 0 warnings.

## Recovery Snapshot

- Read first: `AGENTS.md`, this Feature, `ADR-001`.
- Current capability state: MVP citation/context/process/model boundary is complete; Chat answer cards no longer host the full citation evidence panel, and ActivityPanel exposes the inspectable evidence sidecar.
- Known risks: Wording drift can reintroduce paper-only assumptions or overstate evidence quality.
- Next safe action: Attribute source-type, citation, memory, or boundary wording changes here.
- Unblock condition: None.

## Next Step

Start a separate source-quality Feature before claiming reliability scoring beyond basic source identity and warnings.
