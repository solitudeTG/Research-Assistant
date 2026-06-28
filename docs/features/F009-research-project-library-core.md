---
id: F009
doc_kind: feature
status: active
owner: solitudeTG
created: 2026-06-28
updated: 2026-06-28
---

# F009: Research Project Library Core

## Goal

建立 Research Project 与 Research Library 的最小资产管理闭环，让论文进入可信研究库时必须归属到明确研究项目，并能在 UI 中查看项目下的论文资产、索引状态和基础元数据。

## Vision Anchor

- 原始请求或来源：用户确认 Research Assistant 定位接近 Notebook/Workspace，Project 作为数据隔离边界，Research Library 管理 Project 与资产。
- 用户痛点或工程问题：普通 Chat 上传论文会产生临时理解，但不应该自动污染 RAG；用户需要看得见、管得住已经进入研究库的可信资产。
- 期望结果：Research Library 页面可以创建/选择 Project，上传论文到 Project，展示 Project 下的论文资产和索引状态。
- 非目标或边界：本 Feature 不负责 Chat 会话绑定 Project、不负责 RAG 路由门控、不负责临时 Chat 文件提升入库动作、不改变 citation evidence 合同。
- Exit Gate 对照来源：本 Feature、`F003` 文档摄取、`F004` 证据边界、`ADR-001` 研究域存储决策、Research Library UI/route/backend tests。

## Feature Intake

- Original problem: Trusted research assets need a visible project-scoped home before they are used by RAG.
- User pain point: Without a Research Library, users cannot tell which papers are indexed, trusted, or available for citation.
- Capability promise: Provide a ScienceClaw-styled Library page for project creation, project selection, paper upload, and paper asset visibility.
- Non-goals: Do not implement project-scoped chat retrieval or admission thresholding here.
- Acceptance source: User-approved four-Feature breakdown on 2026-06-28 and existing F003/F004/F005 contracts.
- Open questions: Full paper metadata editing, tags, collections, notes, and collaboration are deferred.

## Capability Contract

- Research Project is the primary data-isolation boundary for trusted research assets.
- A paper added through Research Library must be associated with exactly one Project in the MVP.
- Library upload writes into the research-domain storage path, not the temporary Chat-only file path.
- The UI keeps ScienceClaw's dense, restrained workbench style and does not introduce a marketing or decorative page.
- Asset rows expose enough status for users to distinguish uploaded, parsed, indexed, failed, and citation-ready states.

## Decision Context

### Why

Project ownership is the first-principles boundary for trusted scientific context. Users should not manage a technical RAG toggle; they should manage research projects and the evidence assets available inside each project.

### Why Not

Automatically indexing every Chat upload was rejected because arbitrary files would pollute trusted RAG state. A standalone Project admin center was deferred because Project's first value is asset isolation, so it belongs naturally inside Research Library.

### If Modifying This Area, Check

- `F003` for ingestion and canonical paper model constraints.
- `F004` for citation evidence eligibility.
- `ADR-001` for PostgreSQL/pgvector research-domain storage.
- `F002` for ScienceClaw UI shell/style consistency.

## Current Status

Planned. This Feature is the first implementation slice in the Research Project + Library capability sequence.

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
- [F004 Citation Evidence Boundary](F004-citation-evidence-boundary.md)
- [F005 Hybrid Retrieval and Grounded Answering](F005-hybrid-retrieval-grounded-answering.md)
- [F010 Project Scoped Chat](F010-project-scoped-chat.md)
- [F011 Evidence Admission Gate](F011-evidence-admission-gate.md)
- [F012 Chat To Library Promotion](F012-chat-to-library-promotion.md)

### External Context

- None.

## Acceptance Criteria

- [ ] User can create a Research Project from Research Library.
- [ ] User can select a Project and see its paper assets.
- [ ] User can upload a paper from Research Library into the selected Project.
- [ ] Uploaded paper records expose parsing/indexing/citation-readiness status.
- [ ] UI follows ScienceClaw workbench density, spacing, and restrained visual language.

## Acceptance Map

| Claim | Acceptance | Evidence | Status |
| --- | --- | --- | --- |
| Research Project exists as a visible asset boundary. | Library UI and backend API create/list/select projects. | Pending. | Planned |
| Papers can be uploaded into a Project. | Library upload indexes or records a paper under the selected Project. | Pending. | Planned |
| Project assets are inspectable. | Library table shows Project-scoped paper rows and status. | Pending. | Planned |

## State Timeline

| Date | State | Trigger | Evidence | Note |
| --- | --- | --- | --- | --- |
| 2026-06-28 | planned | User approved four-Feature breakdown | This Feature | Created to own Research Library and Project asset management. |

## Patch History

None yet.

## Evidence

No verification evidence yet.

## Recovery Snapshot

- Read first: this Feature, `F003`, `F004`, `F005`, `ADR-001`.
- Current capability state: Session-scoped research ingestion/retrieval exists; Project/Library asset management is not yet implemented.
- Known risks: Data model changes must not break existing session-scoped tests; UI must not diverge from ScienceClaw style.
- Next safe action: Add backend/API tests for Project creation and Project paper listing before implementation.
- Unblock condition: None.

## Next Step

Implement the smallest vertical slice: project table/API, Research Library page shell, project list, and paper asset list.
