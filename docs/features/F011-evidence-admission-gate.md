---
id: F011
doc_kind: feature
status: planned
owner: solitudeTG
created: 2026-06-28
updated: 2026-06-28
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

Planned. Depends on F010 for Project-scoped retrieval.

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

- None yet.

### Decisions / ADRs

- [ADR-001 P0 Research Data and Retrieval Stack](../decisions/ADR-001-p0-research-data-and-retrieval-stack.md)

### Lessons

- None yet.

### Specs / Plans

- [F001 Feature Map and Rules Spec](../specs/F001-feature-map-and-rules-spec.md)

### Related Features

- [F004 Citation Evidence Boundary](F004-citation-evidence-boundary.md)
- [F005 Hybrid Retrieval and Grounded Answering](F005-hybrid-retrieval-grounded-answering.md)
- [F008 Trace Honesty and Activity Panel](F008-trace-honesty-activity-panel.md)
- [F010 Project Scoped Chat](F010-project-scoped-chat.md)

### External Context

- None.

## Acceptance Criteria

- [ ] Obvious non-evidence utterances do not trigger RAG.
- [ ] Low-score retrieval results are not injected as citation evidence.
- [ ] Accepted evidence is traceable to Project scope and source identity.
- [ ] UI/trace exposes admission decision metadata.
- [ ] Tests cover inject and abstain paths.

## Acceptance Map

| Claim | Acceptance | Evidence | Status |
| --- | --- | --- | --- |
| Non-evidence turns skip RAG. | Deterministic rules cover obvious thanks/continue/rewrite cases. | Pending. | Planned |
| Weak retrieval is not injected. | Low-score candidates produce evidence-insufficient behavior. | Pending. | Planned |
| Admission is observable. | Trace exposes top-k, thresholds, accepted/rejected counts, and decision. | Pending. | Planned |

## State Timeline

| Date | State | Trigger | Evidence | Note |
| --- | --- | --- | --- | --- |
| 2026-06-28 | planned | User approved four-Feature breakdown | This Feature | Created to own evidence thresholding and admission behavior. |

## Patch History

None yet.

## Evidence

No verification evidence yet.

## Recovery Snapshot

- Read first: this Feature, `F004`, `F005`, `F008`, `F010`.
- Current capability state: Research answer route can retrieve evidence, but does not yet have Project-scoped admission telemetry.
- Known risks: Overly aggressive thresholds can cause false abstention; overly loose thresholds cause weak citations.
- Next safe action: Add deterministic tests for skip, inject, and abstain decisions before tuning.

## Next Step

Implement after F010 scopes retrieval to Project assets.
