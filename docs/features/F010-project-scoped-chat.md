---
id: F010
doc_kind: feature
status: completed
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

Completed for MVP scope. Chat sessions can bind to one Research Project, Chat UI shows the Project context, and research-answer retrieval uses Project-scoped citation evidence when a binding exists while preserving session-scoped behavior for unbound chats.

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

- [EV-002 Project Scoped Chat Verification](../evidence/EV-002-project-scoped-chat-verification.md)

### Decisions / ADRs

- [ADR-001 P0 Research Data and Retrieval Stack](../decisions/ADR-001-p0-research-data-and-retrieval-stack.md)

### Lessons

- None yet.

### Specs / Plans

- [F001 Feature Map and Rules Spec](../specs/F001-feature-map-and-rules-spec.md)
- [Project Scoped Chat Implementation Plan](../superpowers/plans/2026-06-28-project-scoped-chat.md)

### Related Features

- [F009 Research Project Library Core](F009-research-project-library-core.md)
- [F005 Hybrid Retrieval and Grounded Answering](F005-hybrid-retrieval-grounded-answering.md)
- [F008 Trace Honesty and Activity Panel](F008-trace-honesty-activity-panel.md)

### External Context

- None.

## Acceptance Criteria

- [x] User can associate a Chat session with one Project.
- [x] Chat UI displays the associated Project.
- [x] Research answer retrieval is limited to the associated Project.
- [x] Unassociated sessions preserve session-scoped retrieval instead of querying Project Library assets.
- [x] Trace records the Project retrieval scope.

## Acceptance Map

| Claim | Acceptance | Evidence | Status |
| --- | --- | --- | --- |
| Chat can bind to a Project. | Session metadata/API persists and returns the associated Project; Chat UI exposes Project context. | `pytest backend/tests/test_research_repository.py::test_upsert_session_research_project_persists_binding backend/tests/test_research_session_routes.py::test_set_session_research_project_route_persists_binding backend/tests/test_research_frontend_contracts.py::test_frontend_exposes_session_project_binding_contracts -q`; `npm.cmd run type-check`. | Passed |
| Retrieval is Project-scoped. | Bound research answers pass `project_id` into retrieval and SQL constrains candidates with `p.project_id = $6`. | `pytest backend/tests/test_research_retrieval.py::test_hybrid_search_evidence_can_scope_to_project backend/tests/test_research_answering.py::test_answer_research_question_passes_project_id_to_retrieval -q`. | Passed |
| General Chat stays separate. | Unbound research answers preserve session-scoped retrieval and do not pass `project_id=None` into legacy retrieval stubs. | `pytest backend/tests/test_research_answering.py::test_answer_research_question_uses_only_citation_evidence backend/tests/test_research_session_routes.py::test_research_answer_persists_audit_result -q`. | Passed |

## State Timeline

| Date | State | Trigger | Evidence | Note |
| --- | --- | --- | --- | --- |
| 2026-06-28 | planned | User approved four-Feature breakdown | This Feature | Created to own session-to-Project context binding. |
| 2026-06-28 | completed | F010 implementation and verification | Full backend tests, frontend type-check, frontend build | MVP Project-scoped chat binding landed. |

## Patch History

None yet.

## Evidence

- `pytest backend/tests -q` from `ScienceClaw`: 154 passed, 2071 warnings.
- `npm.cmd run type-check` from `ScienceClaw/frontend`: passed.
- `npm.cmd run build` from `ScienceClaw/frontend`: passed with existing Browserslist/CSS/chunk-size warnings.
- Focused F010 tests: 8 passed for schema, repository, retrieval, answering, routes, and frontend binding contracts.

## Recovery Snapshot

- Read first: this Feature, `F009`, `F005`, `F008`.
- Current capability state: Research answer route is Project-scoped when a session binding exists; otherwise it remains session-scoped.
- Known risks: F010 does not implement evidence relevance thresholds, per-question source selection, multi-project sessions, or chat-upload promotion.
- Next safe action: Start F011 evidence admission thresholds and retrieval decision policy.

## Next Step

Start F011 to decide when low-quality or low-score retrieved evidence should be withheld from context.
