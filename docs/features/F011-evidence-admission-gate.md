---
id: F011
doc_kind: feature
status: completed
owner: solitudeTG
created: 2026-06-28
updated: 2026-06-29
---

# F011: Evidence Admission Gate

## Goal

在 Project-scoped RAG 之后增加 evidence admission gate，用可解释、可测试的规则决定检索结果是否足够可靠进入回答上下文并成为 citation evidence。

## Vision Anchor

- 原始请求或来源：用户认可“项目资产都是可用上下文”不等于“每轮全部注入上下文”，并关注低分 TopK 是否应注入。
- 用户痛点或工程问题：低相关检索结果如果被硬塞进回答，会制造错误引用和幻觉引用。
- 期望结果：系统记录 top-k、阈值、accepted/rejected、decision，并在证据不足时拒绝注入 citation evidence。
- 非目标或边界：第一版不做完整 Agentic RAG；不做复杂 reranker 或自动调参平台。
- Exit Gate 对照来源：本 Feature、`F004` citation boundary、`F005` retrieval answering、trace tests。

## Feature Intake

- Original problem: Retrieval returns candidates, but not every candidate should become answer context.
- User pain point: Users need to know when current project evidence is insufficient instead of receiving weak citations.
- Capability promise: Add a transparent gate that admits or rejects evidence based on relevance and count.
- Non-goals: Do not use AI as the mandatory per-turn RAG router in the MVP.
- Acceptance source: User-approved relevance gate discussion on 2026-06-28.
- Open questions: Final threshold values need empirical tuning with a small eval set.

## Capability Contract

- Simple non-evidence utterances such as thanks/continue/rewrite may skip retrieval by deterministic rule.
- Retrieval candidates must pass configured relevance/count criteria before injection.
- Low-confidence retrieval produces an explicit evidence-insufficient response instead of fabricated citations.
- Trace records retrieval scope, top-k, threshold, accepted count, rejected count, highest score, and decision.
- Thresholds must be centralized and testable.

## Current Status

Completed for MVP scope. A deterministic admission policy now handles obvious non-evidence skip turns, filters weak retrieval candidates, and exposes admission telemetry in answer payloads and ActivityPanel trace metadata.

## Decision Context

### Why

Project assets define what may be searched, but relevance gates decide what may enter a specific answer. This prevents low-score matches from becoming misleading citations.

### Why Not

Mandatory AI routing before every retrieval was rejected for the MVP because it would add opaque behavior before deterministic skip/inject/abstain paths are measurable.

### If Modifying This Area, Check

- `F004` for citation evidence eligibility.
- `F005` for retrieval scoring and answer behavior.
- `F008` for real trace metadata.
- `F010` for Project scope.

## Links

### Evidence

- [EV-003 Evidence Admission Gate Verification](../evidence/EV-003-evidence-admission-gate-verification.md)

### Decisions / ADRs

- [ADR-001 P0 Research Data and Retrieval Stack](../decisions/ADR-001-p0-research-data-and-retrieval-stack.md)

### Lessons

- None yet.

### Specs / Plans

- [F001 Feature Map and Rules Spec](../specs/F001-feature-map-and-rules-spec.md)
- [Evidence Admission Gate Implementation Plan](../superpowers/plans/2026-06-28-evidence-admission-gate.md)

### Related Features

- [F004 Citation Evidence Boundary](F004-citation-evidence-boundary.md)
- [F005 Hybrid Retrieval and Grounded Answering](F005-hybrid-retrieval-grounded-answering.md)
- [F008 Trace Honesty and Activity Panel](F008-trace-honesty-activity-panel.md)
- [F010 Project Scoped Chat](F010-project-scoped-chat.md)

### External Context

- None.

## Acceptance Criteria

- [x] Obvious non-evidence utterances do not trigger RAG.
- [x] Low-score retrieval results are not injected as citation evidence.
- [x] Accepted evidence remains traceable to retrieval scope and source identity.
- [x] UI/trace exposes admission decision metadata.
- [x] Tests cover inject, skip, and abstain paths.

## Acceptance Map

| Claim | Acceptance | Evidence | Status |
| --- | --- | --- | --- |
| Non-evidence turns skip RAG. | Deterministic rules cover obvious thanks/continue/rewrite cases and answer path does not call retrieval. | `pytest backend/tests/test_research_admission.py backend/tests/test_research_answering.py::test_answer_research_question_skips_retrieval_for_non_evidence_turn -q`. | Passed |
| Weak retrieval is not injected. | Low-score candidates produce evidence-insufficient behavior and no citations. | `pytest backend/tests/test_research_answering.py::test_answer_research_question_rejects_weak_retrieval_hits -q`. | Passed |
| Admission is observable. | Trace exposes top-k, threshold, accepted/rejected counts, highest score, and decision. | `pytest backend/tests/test_research_session_routes.py::test_research_answer_trace_and_message_keep_memory_context_separate backend/tests/test_research_frontend_contracts.py::test_activity_panel_surfaces_evidence_admission_trace_metadata -q`. | Passed |

## State Timeline

| Date | State | Trigger | Evidence | Note |
| --- | --- | --- | --- | --- |
| 2026-06-28 | planned | User approved four-Feature breakdown | This Feature | Created to own evidence thresholding and admission behavior. |
| 2026-06-28 | completed | F011 implementation and verification | EV-003 | MVP deterministic admission gate landed. |
| 2026-06-29 | patched | Real E2E showed skipped turns still appeared as completed retrieval in Activity trace | Route regression test and browser/backend event verification | F011.1 separates "checking need" from completed retrieval and labels deterministic skips honestly. |

## Patch History

| Patch | Date | Commit | Symptom | Root Cause | Protection | Status |
| --- | --- | --- | --- | --- | --- | --- |
| F011.1 | 2026-06-29 | `515bd25` | A trivial turn such as `谢谢` correctly skipped evidence admission, but ActivityPanel still displayed `Citation evidence retrieval completed`. | The route emitted the same completed step description for accepted and skipped admission decisions. | Route regression test requires skipped admission to emit `Citation evidence retrieval skipped`; backend event E2E verified `decision=skipped`, `reason=deterministic_non_evidence_turn`, and `citation_count=0`. | verified |

## Evidence

- `pytest backend/tests -q` from `ScienceClaw`: 160 passed, 2071 warnings.
- `npm.cmd run type-check` from `ScienceClaw/frontend`: passed.
- `npm.cmd run build` from `ScienceClaw/frontend`: passed with existing Browserslist/CSS/chunk-size warnings.
- Focused F011 tests cover skip, accepted, insufficient, route trace, and frontend ActivityPanel contracts.
- 2026-06-29 patch verification: `pytest ScienceClaw/backend/tests/test_research_session_routes.py -k "trace_names_skipped or citation_evidence_wording or trace_and_message_keep_memory" -q` -> `3 passed`; live session event tail showed `Checking whether citation evidence is needed` followed by `Citation evidence retrieval skipped`.

## Recovery Snapshot

- Read first: this Feature, `F004`, `F005`, `F008`, `F010`.
- Current capability state: Research answer route now has deterministic admission telemetry and filters weak citation evidence.
- Known risks: The first threshold is not empirically tuned; overly aggressive thresholds can cause false abstention and overly loose thresholds can cause weak citations.
- Next safe action: Start F012 Chat-to-Library promotion or create an eval set for threshold tuning.

## Next Step

Start F012 Chat-to-Library promotion.
