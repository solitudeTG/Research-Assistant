---
id: EV-002
doc_kind: evidence
scope: project
feature_refs:
  - docs/features/F010-project-scoped-chat.md
created: 2026-06-28
---

# EV-002: Project Scoped Chat Verification

## Supports Claim

本 Evidence 支撑 F010 的完成声明：Chat 会话可以关联一个 Research Project；绑定后 research answer 检索使用 Project 资产范围；未绑定会话保留 session-scoped retrieval；Chat UI 暴露当前 Project context；trace metadata 记录真实 retrieval scope。

## Verification Scope

覆盖后端 schema、repository、database wrapper、retrieval SQL、answering 传参、session route、前端 API contract、ChatPage Project context UI、前端类型检查和生产构建。

未覆盖真实浏览器手动点击 Project selector、真实 PostgreSQL 多 Project 端到端数据隔离、证据 relevance threshold、Agentic RAG 判断、解除 Project 绑定、多 Project 会话或 Chat 上传论文入库。

## Commands

```text
pytest backend/tests/test_research_store_schema.py::test_research_store_schema_defines_pgvector_and_evidence_tables backend/tests/test_research_repository.py::test_upsert_session_research_project_persists_binding backend/tests/test_research_repository.py::test_get_session_research_project_reads_binding backend/tests/test_research_retrieval.py::test_hybrid_search_evidence_can_scope_to_project backend/tests/test_research_answering.py::test_answer_research_question_passes_project_id_to_retrieval backend/tests/test_research_session_routes.py::test_set_session_research_project_route_persists_binding backend/tests/test_research_session_routes.py::test_get_session_research_project_route_returns_binding backend/tests/test_research_frontend_contracts.py::test_frontend_exposes_session_project_binding_contracts -q

pytest backend/tests -q

npm.cmd run type-check

npm.cmd run build

python C:\Users\HUAWEI\.codex\skills\using-agentmentor\scripts\knowledge_check.py --root E:\Self-Project\Research-Assistant --docs-path docs --feature-index docs\features\F010-project-scoped-chat.md

python C:\Users\HUAWEI\.codex\skills\using-agentmentor\scripts\knowledge_check.py --root E:\Self-Project\Research-Assistant --docs-path docs --strict
```

## Checks

## Results

Pass.

- Focused F010 tests: 8 passed, 93 warnings.
- Full backend tests: 154 passed, 2071 warnings.
- Frontend type-check: passed.
- Frontend build: passed.
- AgentMentor F010 feature-index check: passed after EV-002 was linked from F010.
- AgentMentor strict knowledge check: passed after EV-002 was linked from F010.

Build retained existing non-blocking warnings: outdated Browserslist data, CSS minify warnings, and large chunk warnings.

## Artifacts

- Feature: `docs/features/F010-project-scoped-chat.md`
- Plan: `docs/superpowers/plans/2026-06-28-project-scoped-chat.md`
- Backend touched paths:
  - `ScienceClaw/backend/research_assistant/storage/schema.sql`
  - `ScienceClaw/backend/research_assistant/storage/repository.py`
  - `ScienceClaw/backend/research_assistant/storage/database.py`
  - `ScienceClaw/backend/research_assistant/retrieval.py`
  - `ScienceClaw/backend/research_assistant/answering.py`
  - `ScienceClaw/backend/route/sessions.py`
- Frontend touched paths:
  - `ScienceClaw/frontend/src/api/agent.ts`
  - `ScienceClaw/frontend/src/pages/ChatPage.vue`

## Limitations

本 Evidence 证明 F010 的 MVP 代码路径和自动化验证通过，但不能证明真实用户环境中所有 Project 资产隔离组合都已完成端到端验证。F011 仍需定义低分 evidence withholding / threshold 策略；F012 仍需定义 Chat 上传论文加入 Research Library 的显式动作。

## Notes

为了保持兼容性，`answer_research_question` 仅在 `project_id` 非空时向 retrieval wrapper 传递 Project scope。session route 中 Project binding lookup 失败会降级为 session-scoped retrieval；真正的回答检索仍会通过原回答链路暴露数据库错误。
