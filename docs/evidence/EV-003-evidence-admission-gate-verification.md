---
id: EV-003
doc_kind: evidence
scope: project
feature_refs:
  - docs/features/F011-evidence-admission-gate.md
created: 2026-06-28
---

# EV-003: Evidence Admission Gate Verification

## Supports Claim

本 Evidence 支撑 F011 的完成声明：系统具备可测试的 evidence admission gate，能跳过明显非证据回合，拒绝低分 retrieval candidates 进入 citation context，并在 answer payload 与 ActivityPanel trace metadata 中展示 admission decision。

## Verification Scope

覆盖 admission policy、answering skip/accept/insufficient 路径、route trace metadata、frontend metadata types、ActivityPanel admission 展示契约、完整后端测试、前端类型检查和生产构建。

未覆盖基于真实论文集合的阈值调优、LLM/Agentic RAG 路由、reranker、per-project 自适应阈值、真实浏览器截图验证或人工标注 eval set。

## Checks

```text
pytest backend/tests/test_research_admission.py backend/tests/test_research_answering.py::test_answer_research_question_skips_retrieval_for_non_evidence_turn backend/tests/test_research_answering.py::test_answer_research_question_rejects_weak_retrieval_hits backend/tests/test_research_answering.py::test_answer_research_question_refuses_when_no_paper_evidence backend/tests/test_research_session_routes.py::test_research_answer_trace_and_message_keep_memory_context_separate -q

pytest backend/tests/test_research_frontend_contracts.py::test_activity_panel_surfaces_evidence_admission_trace_metadata -q

pytest backend/tests -q

npm.cmd run type-check

npm.cmd run build

python C:\Users\HUAWEI\.codex\skills\using-agentmentor\scripts\knowledge_check.py --root E:\Self-Project\Research-Assistant --docs-path docs --feature-index docs\features\F011-evidence-admission-gate.md

python C:\Users\HUAWEI\.codex\skills\using-agentmentor\scripts\knowledge_check.py --root E:\Self-Project\Research-Assistant --docs-path docs --strict
```

## Results

Pass.

- F011 focused backend tests: 7 passed, 47 warnings.
- Evidence admission frontend contract: 1 passed.
- Full backend tests: 160 passed, 2071 warnings.
- Frontend type-check: passed.
- Frontend build: passed.
- AgentMentor F011 feature-index check: passed after EV-003 was linked from F011.
- AgentMentor strict knowledge check: passed after EV-003 was linked from F011.

Build retained existing non-blocking warnings: outdated Browserslist data, CSS minify warnings, and large chunk warnings.

## Artifacts

- Feature: `docs/features/F011-evidence-admission-gate.md`
- Plan: `docs/superpowers/plans/2026-06-28-evidence-admission-gate.md`
- Backend:
  - `ScienceClaw/backend/research_assistant/admission.py`
  - `ScienceClaw/backend/research_assistant/answering.py`
  - `ScienceClaw/backend/route/sessions.py`
- Frontend:
  - `ScienceClaw/frontend/src/types/event.ts`
  - `ScienceClaw/frontend/src/types/message.ts`
  - `ScienceClaw/frontend/src/api/agent.ts`
  - `ScienceClaw/frontend/src/components/ActivityPanel.vue`

## Limitations

本 Evidence 证明 deterministic gate 的行为正确，但不证明阈值已经在真实科研语料上最优。`MIN_EVIDENCE_RELEVANCE_SCORE = 0.015` 是首版保守阈值，需要后续 eval set 调优。

## Notes

F011 明确拒绝在 MVP 中加入 mandatory AI router 或 reranker。Project scope 决定“可搜索资产集合”，admission gate 决定“本轮可进入 citation context 的证据”。
