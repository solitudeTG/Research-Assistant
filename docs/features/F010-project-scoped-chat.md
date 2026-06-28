---
id: F010
doc_kind: feature
status: planned
owner: solitudeTG
created: 2026-06-28
updated: 2026-06-28
---

# F010: Project Scoped Chat

## Goal

让 Chat 会话可以关联一个 Research Project，并确保关联后的研究问答只在当前 Project 的资产范围内检索 citation evidence。

## Vision Anchor

- 原始请求或来源：用户确认会话关联研究项目后，该项目下资产都是可用研究上下文，但不是每轮全部注入上下文。
- 用户痛点或工程问题：没有 Project scope 时，RAG 只能依赖 session 范围或全局资产，容易跨课题污染证据。
- 期望结果：创建/进入会话时可关联 Project；研究问答检索仅限当前 Project；Chat UI 显示当前 Project 状态。
- 非目标或边界：不负责 Project/Library 资产管理本身，不负责低相关 evidence threshold，不负责 Chat 临时 PDF 入库。
- Exit Gate 对照来源：本 Feature、`F005` 检索问答、`F004` citation boundary、Project scope route/frontend tests。

## Feature Intake

- Original problem: Chat needs a durable research context boundary before using Library assets.
- User pain point: Users cannot trust citations if a chat can silently retrieve across unrelated projects.
- Capability promise: Bind sessions to a Research Project and scope retrieval to that Project.
- Non-goals: Do not introduce a General/Research toggle; Project association is the primary context boundary.
- Acceptance source: User-approved Project-as-Notebook product decision on 2026-06-28.
- Open questions: Multi-project sessions, per-question source selection, and pinned source sets are deferred.

## Capability Contract

- A session may be associated with one Project for the MVP.
- Project-associated sessions show the current Project in Chat.
- Project-associated research questions retrieve only from that Project's indexed assets.
- General Chat sessions without Project association must not access Research Library assets.
- The backend trace must expose the actual retrieval scope.

## Current Status

Planned. Depends on F009 for the Project model and Library asset boundary.

## Decision Context

### Why

Research Project is the trusted context boundary. Chat should not ask users to manage a technical RAG toggle; it should make the active Project visible and scope retrieval to that Project.

### Why Not

A global Library retrieval path was rejected because unrelated research projects could contaminate citations. A General/Research mode switch was deferred because it would expose implementation mechanics before the Project boundary is established.

### If Modifying This Area, Check

- `F009` for Project and Library data contracts.
- `F005` for retrieval and grounded answer contracts.
- `F008` for trace honesty when emitting retrieval scope.

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

- [F009 Research Project Library Core](F009-research-project-library-core.md)
- [F005 Hybrid Retrieval and Grounded Answering](F005-hybrid-retrieval-grounded-answering.md)
- [F008 Trace Honesty and Activity Panel](F008-trace-honesty-activity-panel.md)

### External Context

- None.

## Acceptance Criteria

- [ ] User can associate a Chat session with one Project.
- [ ] Chat UI displays the associated Project.
- [ ] Research answer retrieval is limited to the associated Project.
- [ ] Unassociated sessions do not retrieve from Research Library.
- [ ] Trace records the Project retrieval scope.

## Acceptance Map

| Claim | Acceptance | Evidence | Status |
| --- | --- | --- | --- |
| Chat can bind to a Project. | Session metadata/API persists and returns the associated Project. | Pending. | Planned |
| Retrieval is Project-scoped. | Two Projects with different papers cannot cross-retrieve evidence. | Pending. | Planned |
| General Chat stays separate. | Unassociated sessions do not query Library assets. | Pending. | Planned |

## State Timeline

| Date | State | Trigger | Evidence | Note |
| --- | --- | --- | --- | --- |
| 2026-06-28 | planned | User approved four-Feature breakdown | This Feature | Created to own session-to-Project context binding. |

## Patch History

None yet.

## Evidence

No verification evidence yet.

## Recovery Snapshot

- Read first: this Feature, `F009`, `F005`, `F008`.
- Current capability state: Research answer route exists but is not yet Project-scoped.
- Known risks: Avoid adding a confusing RAG mode switch; Project association is the product primitive.
- Next safe action: Add route/service tests proving two Projects cannot cross-retrieve evidence.

## Next Step

Implement after F009 provides a Project model and Library asset records.
