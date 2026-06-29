---
id: F013
doc_kind: feature
status: active
owner: solitudeTG
created: 2026-06-29
updated: 2026-06-29
---

# F013: Research Task Router and Whole Paper Summary

## Goal

建立任务感知的科研工作流路由，让系统区分普通对话、局部证据问答和整篇论文理解；当用户要求总结整篇论文时，不再只依赖普通 top-k RAG，而是走覆盖全文 chunk 的摘要工作流。

## Vision Anchor

- 原始请求或来源：用户确认第一轮先解决“什么时候 RAG、什么时候总结整篇”的核心质量问题，Research Synthesis + 多 Agent 放到第二轮。
- 用户痛点或工程问题：普通 top-k RAG 适合局部问答，但用于“总结整篇论文”会遗漏没有被召回的章节、实验、局限或结论。
- 期望结果：每轮研究问题先得到可追踪 route；明显寒暄不检索，局部问题走 evidence QA，整篇总结走 whole-paper summary workflow。
- 非目标或边界：本 Feature 不实现多文献 Research Synthesis、不启用多 Agent、不做完整综述报告、不替代 F011 的 evidence admission threshold。
- Exit Gate 对照来源：本 Feature、F005 grounded answering、F008 trace honesty、F010 Project scope、F011 evidence admission。

## Feature Intake

- Original problem: Research questions need task-aware routing before choosing retrieval or summarization.
- User pain point: Users expect whole-paper summaries to cover the paper, not only the few chunks selected by semantic top-k.
- Capability promise: Add a deterministic-first task router and a whole-paper summary workflow for single-paper summary requests.
- Non-goals: Do not implement multi-paper synthesis, multi-agent workflow, long-form literature review, or a user-facing General/Research mode switch.
- Acceptance source: User-approved F013 scope discussion on 2026-06-29.
- Open questions: LLM-based ambiguous routing can be added after deterministic routes and traceable behavior are measurable.

## Capability Contract

- The router classifies research turns as `general_chat`, `evidence_qa`, or `whole_paper_summary`.
- Deterministic rules handle obvious non-evidence turns and strong whole-paper summary intents before any LLM router.
- `evidence_qa` keeps using the existing Project/session-scoped RAG plus F011 admission gate.
- `whole_paper_summary` covers the available paper chunks rather than only top-k retrieval hits.
- Route metadata is included in answer metadata and backend trace so ActivityPanel can show the real selected workflow.

## Current Status

Completed for the first MVP slice. The backend now classifies research turns as `general_chat`, `evidence_qa`, or `whole_paper_summary`; existing evidence QA keeps the F005/F011 path, while whole-paper summary uses a bounded latest-paper evidence sweep instead of ordinary top-k hybrid search. Route metadata is returned with answers and displayed in ActivityPanel from real backend step metadata.

## Decision Context

### Why

Project assets are available context, but the system still needs to decide which workflow is appropriate for the question. Whole-paper understanding is a global document task and needs a different path from local evidence retrieval.

### Why Not

Pure LLM routing was deferred because deterministic product boundaries such as "thanks does not retrieve" and "summarize this paper is not ordinary top-k RAG" should be testable and auditable first. Multi Agent synthesis was deferred because single-paper routing and summary quality need to be stable before adding cross-paper roles.

### If Modifying This Area, Check

- F005 for retrieval and grounded answer behavior.
- F008 for trace honesty and ActivityPanel metadata.
- F010 for Project/session retrieval scope.
- F011 for evidence admission and deterministic skip behavior.

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

- [F005 Hybrid Retrieval and Grounded Answering](F005-hybrid-retrieval-grounded-answering.md)
- [F008 Trace Honesty and Activity Panel](F008-trace-honesty-activity-panel.md)
- [F010 Project Scoped Chat](F010-project-scoped-chat.md)
- [F011 Evidence Admission Gate](F011-evidence-admission-gate.md)

### External Context

- LlamaIndex Router Query Engine and common RAG router patterns support separating summary and semantic search engines.

## Acceptance Criteria

- [x] Obvious non-evidence turns route to `general_chat` and skip retrieval.
- [x] Local research questions route to `evidence_qa` and preserve existing RAG/admission behavior.
- [x] Whole-paper summary requests route to `whole_paper_summary`.
- [x] Whole-paper summary uses available paper chunks beyond ordinary top-k and returns citation evidence.
- [x] Route metadata is visible in backend answer metadata and trace.

## Acceptance Map

| Claim | Acceptance | Evidence | Status |
| --- | --- | --- | --- |
| Research turns are routed before execution. | Answer metadata includes route, decision source, confidence, reason, and scope. | `test_research_task_router.py`; answering route assertions. | Passed |
| Whole-paper summary does not depend on ordinary top-k only. | Summary path lists latest-paper evidence for the current session/project scope and does not call ordinary top-k hybrid search. | `test_answer_research_question_routes_whole_paper_summary_to_full_paper_evidence`; database source-identity boundary test. | Passed |
| Existing evidence QA remains compatible. | F005/F011 answer tests continue to pass. | Full backend suite, frontend contract suite, type-check, and build. | Passed |

## State Timeline

| Date | State | Trigger | Evidence | Note |
| --- | --- | --- | --- | --- |
| 2026-06-29 | active | User approved F013 first slice | This Feature | Created to own task routing and single-paper whole-summary behavior. |
| 2026-06-29 | completed | First F013 implementation slice | Backend/frontend tests, type-check, build | Deterministic task router, whole-paper summary evidence path, route trace metadata, and ActivityPanel display landed. |

## Patch History

| Patch | Date | Commit | Symptom | Root Cause | Protection | Status |
| --- | --- | --- | --- | --- | --- | --- |
| F013.1 | 2026-06-29 | `61a303b` | Whole-paper summary requests used the same ordinary top-k RAG path as local evidence questions, risking missed sections. | The answer flow had only skip vs retrieval admission; it did not classify research task type before selecting workflow. | Route tests, whole-paper summary answer test, database source identity test, route trace/frontend contracts, full backend suite, type-check, and build. | verified |

## Evidence

- `pytest ScienceClaw/backend/tests/test_research_task_router.py ScienceClaw/backend/tests/test_research_answering.py ScienceClaw/backend/tests/test_research_database.py ScienceClaw/backend/tests/test_research_frontend_contracts.py -q` -> `70 passed`.
- `pytest ScienceClaw/backend/tests/test_research_session_routes.py -k "research_answer" -q` -> `7 passed`.
- `pytest ScienceClaw/backend/tests --basetemp .pytest_tmp/run -q` with `TMP`/`TEMP` set to workspace `.pytest_tmp` -> `185 passed`.
- `npm.cmd run type-check` from `ScienceClaw/frontend` -> passed.
- `npm.cmd run build` from `ScienceClaw/frontend` -> passed with existing Browserslist/CSS/chunk-size warnings.
- `python -m py_compile` for F013-touched backend modules -> passed.
- Live container verification after restarting `backend` and `frontend`: calling `answer_research_question` against Project `research-project-LuDEUgC2rBAofjdcg9KmpK` with `请总结这篇论文的核心内容与主要观点` returned `task_route.route=whole_paper_summary`, `citation_count=24`, `evidence_admission.decision=accepted`, and a whole-paper summary content preview.

## Recovery Snapshot

- Read first: this Feature, F005, F008, F010, F011.
- Current capability state: Existing answering path now has deterministic task routing, extractive whole-paper summary, and route trace metadata.
- Known risks: Whole-paper summary is an extractive first slice over a bounded latest-paper evidence window; LLM-based ambiguous routing, richer section summarization, explicit paper selection, and multi-paper synthesis remain follow-ups.
- Next safe action: Validate the live UI after service restart, then decide whether F013.2 should add LLM structured routing for ambiguous cases or move to the Chat upload boundary fix.

## Next Step

Validate the live UI after service restart and decide the next F013.2 slice.
