---
id: F012
doc_kind: feature
status: planned
owner: solitudeTG
created: 2026-06-28
updated: 2026-06-28
---

# F012: Chat To Library Promotion

## Goal

让普通 Chat 上传的论文保持临时理解语义，并只在用户显式点击“加入研究库”后，才写入指定 Research Project 并进入索引。

## Vision Anchor

- 原始请求或来源：用户确认普通 Chat 直接上传论文走通用 Agent 是合理的，但不应随意进入 RAG；回答底部只需要一个明确动作“加入研究库”。
- 用户痛点或工程问题：任意临时上传文件自动入库会污染可信研究资产；多个动作会增加用户认知负担。
- 期望结果：Chat 临时 PDF 回答底部出现单一“加入研究库”动作，确认 Project 后再入库并索引。
- 非目标或边界：不负责 Library 页面基础能力，不负责 Project-scoped retrieval，不负责复杂批量入库或自动质量评估。
- Exit Gate 对照来源：本 Feature、`F009` Library core、`F003` ingestion、Chat UI action tests。

## Feature Intake

- Original problem: Temporary Chat file understanding and trusted Research Library ingestion need a user-confirmed boundary.
- User pain point: Users want to inspect a paper first, then decide whether it is valuable enough to become trusted RAG material.
- Capability promise: Provide one clear promotion action from Chat to Library.
- Non-goals: Do not auto-promote uploads or expose multiple competing actions in the first version.
- Acceptance source: User-approved Chat upload boundary discussion on 2026-06-28.
- Open questions: Future quality review workflow before promotion is deferred.

## Capability Contract

- Chat-uploaded papers remain temporary unless promoted.
- The only first-version promotion action is “加入研究库”.
- Promotion requires a target Research Project.
- Promoted files reuse the Library ingestion/indexing path.
- Activity/trace reflects real promotion/indexing events only.

## Current Status

Planned. Depends on F009 for Library ingestion and Project target selection.

## Decision Context

### Why

Temporary file understanding is useful for quick inspection, but trusted RAG assets require explicit user confirmation and Project ownership.

### Why Not

Automatic promotion was rejected because arbitrary Chat uploads would pollute trusted research context. Multiple first-version actions were rejected because the intended user decision is singular: add this paper to the research library or leave it temporary.

### If Modifying This Area, Check

- `F009` for Library ingestion and Project target selection.
- `F003` for document ingestion.
- `F008` for real promotion/indexing trace.

## Links

### Evidence

- None yet.

### Decisions / ADRs

- [ADR-001 P0 Research Data and Retrieval Stack](../decisions/ADR-001-p0-research-data-and-retrieval-stack.md)

### Lessons

- None yet.

### Specs / Plans

- [F001 Feature Map and Rules Spec](../specs/F001-feature-map-and-rules-spec.md)

### Related Features

- [F003 Research Document Ingestion](F003-research-document-ingestion.md)
- [F008 Trace Honesty and Activity Panel](F008-trace-honesty-activity-panel.md)
- [F009 Research Project Library Core](F009-research-project-library-core.md)

### External Context

- None.

## Acceptance Criteria

- [ ] Temporary Chat upload does not automatically create Library paper assets.
- [ ] Chat answer can show one “加入研究库” action for eligible uploaded papers.
- [ ] User can choose a Project for promotion.
- [ ] Promotion writes and indexes through the Library path.
- [ ] Trace shows real promotion/indexing status.

## Acceptance Map

| Claim | Acceptance | Evidence | Status |
| --- | --- | --- | --- |
| Chat uploads remain temporary by default. | Temporary upload does not create Project paper records. | Pending. | Planned |
| Promotion is explicit. | Eligible answers expose only one "加入研究库" action. | Pending. | Planned |
| Promotion uses Library ingestion. | Confirmed action writes/indexes into a selected Project. | Pending. | Planned |

## State Timeline

| Date | State | Trigger | Evidence | Note |
| --- | --- | --- | --- | --- |
| 2026-06-28 | planned | User approved four-Feature breakdown | This Feature | Created to own temporary-to-trusted asset promotion. |

## Patch History

None yet.

## Evidence

No verification evidence yet.

## Recovery Snapshot

- Read first: this Feature, `F009`, `F003`, `F008`.
- Current capability state: Chat can read uploaded PDFs via generic Agent file path; no trusted promotion action exists yet.
- Known risks: Do not add multiple first-version actions; keep the user boundary explicit.
- Next safe action: Implement after Library upload/index path exists.

## Next Step

Implement after F009 provides the Library upload/index path and Project selection.
