---
id: F005
doc_kind: feature
status: active
owner: solitudeTG
created: 2026-06-28
updated: 2026-06-28
---

# F005: Hybrid Retrieval and Grounded Answering

## Goal

通过 PostgreSQL full-text search 与 pgvector hybrid retrieval 返回可追溯 citation evidence，并生成不越过证据边界的研究答案。

## Vision Anchor

- 原始请求或来源：`F001` P0 论文 RAG 目标、`ADR-001`。
- 用户痛点或工程问题：科研问题需要同时命中术语、年份、编号和语义相似片段；答案必须能回到 evidence record。
- 期望结果：检索返回 citation evidence，答案基于这些 evidence，并在无 citation evidence 时明确说明。
- 非目标或边界：本 Feature 不负责 parser、Evidence Audit 内部判定、报告文件生成或 full reranker。
- Exit Gate 对照来源：本 Feature、retrieval/answering/route tests、`ADR-001`。

## Feature Intake

- Original problem: Research answers need retrievable, inspectable evidence.
- User pain point: Vector-only or summary-only answers cannot support reliable scholarly claims.
- Capability promise: Use hybrid retrieval and answer only from eligible citation evidence.
- Non-goals: Do not implement full reranking, web search crawling, or multi-agent research here.
- Acceptance source: `F001`, `ADR-001`, retrieval and answering tests.
- Open questions: Final hybrid scoring formula and reranker strategy remain follow-ups.

## Capability Contract

- Retrieve candidate evidence using PostgreSQL FTS and pgvector.
- Return citation evidence records with source identity and chunk identity.
- Generate research answers from retrieved citation evidence.
- Use generic no-citation evidence wording when no eligible evidence is found.
- Preserve answer route metadata and UI language aligned with the citation-evidence contract.

## Decision Context

### Why

Hybrid retrieval keeps lexical and semantic evidence recall in one P0 path without adding a separate search infrastructure.

### Why Not

Vector-only retrieval was rejected because scholarly terms, years, identifiers, and citation markers often require lexical recall.

### If Modifying This Area, Check

- `ADR-001` retrieval decision.
- Retrieval, answering, route, and frontend citation contract tests.
- F004 evidence boundary when changing eligible source types.

## Current Status

In Progress. Initial retrieval and grounded answer slices have verification evidence recorded in `F001`.

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

- [F003 Research Document Ingestion](F003-research-document-ingestion.md)
- [F004 Citation Evidence Boundary](F004-citation-evidence-boundary.md)
- [F006 Evidence Audit](F006-evidence-audit.md)

### External Context

- None.

## Acceptance Criteria

- [ ] Hybrid retrieval combines lexical and vector candidates.
- [ ] Retrieval returns inspectable citation evidence records.
- [ ] Research answers use citation evidence and expose citations.
- [ ] No-citation answers do not imply an evidence source that was not searched.

## Acceptance Map

| Claim | Acceptance | Evidence | Status |
| --- | --- | --- | --- |
| Hybrid retrieval returns citation evidence. | Retrieval combines FTS and pgvector candidates and returns evidence records. | Historical retrieval evidence in `F001`. | Partial |
| Research answers are citation-grounded. | Answer generation uses retrieved evidence and exposes citation metadata. | Historical answering/route/frontend evidence in `F001`. | Partial |

## State Timeline

| Date | State | Trigger | Evidence | Note |
| --- | --- | --- | --- | --- |
| 2026-06-28 | active | Feature split from F001 | This Feature and `INDEX.md` | Created to own retrieval and answer recovery. |

## Patch History

None yet.

## Evidence

Move focused retrieval/answering evidence here on the next retrieval or answer behavior change.

## Recovery Snapshot

- Read first: `ADR-001`, this Feature, F004 for citation eligibility.
- Current capability state: Initial retrieval/answering path exists; detailed evidence remains in `F001`.
- Known risks: Scoring formula and online LLM-backed E2E remain incomplete.
- Next safe action: Attribute retrieval or answer-route changes here and verify focused tests.
- Unblock condition: Provider key/model is needed for LLM-backed E2E claims.

## Next Step

Move retrieval and answer-specific evidence from `F001` into this Feature during the next behavior change.
