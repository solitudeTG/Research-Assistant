---
id: F019
doc_kind: feature
status: completed
owner: solitudeTG
created: 2026-06-30
updated: 2026-06-30
---

# F019: Research Quality Evaluation Harness

## Goal

建立一个可复现的研究回答质量评测闭环，让后续调整 RAG 阈值、whole-paper summary prompt、citation discipline 或 Evidence Audit 规则时，有稳定的质量门判断是否破坏了可信科研工作流。

## Vision Anchor

- Source: 用户指出 Research Library、Chat Project 关联、Project-scoped RAG、ActivityPanel 等基础闭环已经完成，要求重新审视当前最有价值的下一步。
- User pain point: 系统已经能上传论文、关联课题、检索、总结和审计，但真实风险转移到了回答质量是否稳定、citation 是否仍然可信、unsupported claim 是否过多。
- Desired outcome: 用可断言的 quality gate 评估 research answer payload，而不是只靠人工看 UI 或只看测试是否通过。
- Non-goals: 不做新 UI，不做 Multi-Agent，不做完整评测平台，不引入外部标注系统，不把 generated summaries 变成 citation evidence。
- Exit Gate source: 本 Feature、F004 citation boundary、F011 evidence admission、F017 LLM synthesis、F018 audit calibration、新增 evaluation tests。

## Feature Intake

- Original problem: 当前缺少一个集中、可复用的研究回答质量断言层。
- User pain point: 后续 prompt 或阈值调整如果没有评测闭环，可能让功能“看起来更流畅”，但 citation discipline 和 evidence boundary 退化。
- Capability promise: 提供可复用的 `ResearchQualityRequirement` / `ResearchQualityReport`，并支持 CLI 校验 answer JSON。
- Non-goals: 不替代 live UI E2E；不判断科学结论真伪；不做 LLM entailment judge；不做多论文 synthesis。
- Acceptance source: 用户批准从整体项目初心出发继续 F019。
- Open questions: 后续需要用真实论文集沉淀 golden cases，并基于评测结果决定是否调 F011 阈值或 F017 prompt。

## Capability Contract

- Quality gate 输入是 `ResearchAnswer.to_dict()` 形状的 payload。
- Gate 必须检查 route、evidence admission、citation count、citation source type、evidence scope、summary synthesis mode、context boundaries 和 audit 指标。
- 只有 `paper` / `web` / `database` 可以通过 citation source type 检查。
- `whole_paper_summary` gate 默认要求 `llm_section_global`，并限制 unsupported claim ratio。
- `non_evidence_turn` gate 必须允许 0 citation，但要求 route=`general_chat` 且 admission=`skipped`。
- CLI 必须能对真实 E2E 导出的 answer JSON 做独立校验，并用退出码表达通过/失败。

## Current Status

Completed for the first evaluation-harness slice. The backend now has a reusable quality gate module, three default gate profiles, a CLI validator for answer JSON, and focused tests proving pass/fail behavior.

## Decision Context

### Why

Research Assistant 的核心价值不是更多入口，而是可信工作流。F009-F018 已经让工作流跑通；F019 把“回答是否仍可信”变成可回归的工程对象。

### Why Not

继续增强 Research Library UI 被拒绝，因为基础资产状态、Project 关联、Project-scoped Chat 和右侧 ActivityPanel 已经存在。Multi-Agent synthesis 继续延后，因为它会放大质量问题；先建立质量门更符合项目初心。

### If Modifying This Area, Check

- F004: citation evidence eligibility.
- F011: admission decision and threshold behavior.
- F017: LLM section/global synthesis metadata.
- F018: audit status and unsupported/partial interpretation.

## Links

### Evidence

- [EV-010 F019 Research Quality Evaluation Harness Verification](../evidence/EV-010-f019-research-quality-evaluation-harness-verification.md)

### Decisions / ADRs

- [ADR-001 P0 Research Data and Retrieval Stack](../decisions/ADR-001-p0-research-data-and-retrieval-stack.md)

### Lessons

- None yet.

### Specs / Plans

- None.

### Related Features

- [F004 Citation Evidence Boundary](F004-citation-evidence-boundary.md)
- [F011 Evidence Admission Gate](F011-evidence-admission-gate.md)
- [F017 LLM Section Summary to Global Synthesis](F017-llm-section-summary-global-synthesis.md)
- [F018 Claim-Level Citation Audit Calibration](F018-claim-level-citation-audit-calibration.md)

## Acceptance Criteria

- [x] A reusable evaluation module can validate research answer payloads against route/admission/citation/audit/synthesis requirements.
- [x] Whole-paper summary quality gate requires `whole_paper_summary`, accepted admission, original citation evidence, and `llm_section_global`.
- [x] Evidence QA quality gate rejects context-only sources such as memory as citations.
- [x] Non-evidence turn quality gate accepts skipped retrieval and zero citations.
- [x] CLI returns non-zero when a saved answer JSON fails the selected quality gate.

## Acceptance Map

| Claim | Acceptance | Evidence | Status |
| --- | --- | --- | --- |
| Quality gate is reusable. | `evaluate_research_answer` accepts `ResearchAnswer.to_dict()`-shaped mappings and returns structured metrics/findings. | EV-010 focused tests. | Passed |
| Citation boundary is guarded. | Memory source in citations fails the evidence QA gate. | EV-010 focused tests. | Passed |
| Route-specific expectations are explicit. | Whole-paper, evidence QA, and non-evidence turn gates encode different expectations. | EV-010 focused tests and CLI test. | Passed |

## State Timeline

| Date | State | Trigger | Evidence | Note |
| --- | --- | --- | --- | --- |
| 2026-06-30 | active | User approved F019 after current capability audit | This Feature | Created to own quality evaluation rather than another UI/product surface. |
| 2026-06-30 | completed | First harness implementation verified | EV-010 | Evaluation module, default gates, CLI, and tests landed. |

## Patch History

None yet.

## Evidence

[EV-010 F019 Research Quality Evaluation Harness Verification](../evidence/EV-010-f019-research-quality-evaluation-harness-verification.md)

## Recovery Snapshot

- Read first: this Feature, F004, F011, F017, F018.
- Current capability: quality gates can now fail route mismatches, weak citation count, invalid citation source type, wrong summary synthesis mode, context-boundary drift, invalid-source claims, and noisy unsupported ratio.
- Known risks: This is still a structural/contract quality gate, not a semantic truth judge. Real-paper golden cases and LLM entailment judging remain future work.
- Next safe action: Use this harness against live UI/API answer JSON from `paper_data` and then tune F017 prompt or F011 thresholds based on measured failures.

## Next Step

Create a small real-paper golden eval set and wire live UI/API answer export into the quality CLI.
