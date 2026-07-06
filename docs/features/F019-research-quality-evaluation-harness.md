---
id: F019
doc_kind: feature
status: completed
owner: solitudeTG
created: 2026-06-30
updated: 2026-07-06
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

Completed for the F019.1 golden eval follow-up. The backend has a reusable quality gate module, default gate profiles, a CLI validator for answer JSON, deterministic payload golden cases, and live UI golden eval support.

F019.1 extends the first slice into a real-paper golden eval harness with payload mode and live UI mode. Payload mode passes 5/5 deterministic cases. Final live UI mode completes login, session creation, UI upload, indexing wait, answer/report generation, trace/file collection, artifact export, machine-readable result parsing, and the stricter whole-paper summary quality gate.

F019.2 expands the demo/benchmark loop without changing the ScienceClaw workbench shell. The golden cases now make the interview-facing coverage explicit: evidence QA, whole-paper summary, multi-paper synthesis, and insufficient evidence. The runner writes stable `results.json`, `summary.md`, case payload snapshots, and failure summaries; each failed finding is decorated with owning module hints such as F005 retrieval, F006 audit, F011 admission, F017 synthesis, F018 calibration, F019 harness, and F020 multi-agent when applicable. Payload mode is the reliable benchmark path; live UI remains a higher-cost partial path with one real-paper whole-paper summary case.

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
- [EV-018 F019 Golden Eval Live UI E2E](../evidence/EV-018-f019-golden-eval-live-ui-e2e.md)
- [EV-022 F019 Golden Eval Benchmark Expansion](../evidence/EV-022-f019-golden-eval-benchmark-expansion.md)

### Decisions / ADRs

- [ADR-001 P0 Research Data and Retrieval Stack](../decisions/ADR-001-p0-research-data-and-retrieval-stack.md)

### Lessons

- None yet.

### External Context

- Local live UI services at `http://127.0.0.1:5173` and proxied API `http://127.0.0.1:5173/api/v1` were used for EV-018.
- Real paper fixtures are local files under `paper_data/`.

### Specs / Plans

- [2026-07-04 Research Golden Eval Live UI Design](../superpowers/specs/2026-07-04-research-golden-eval-live-ui-design.md)
- [2026-07-04 Research Golden Eval Live UI Plan](../superpowers/plans/2026-07-04-research-golden-eval-live-ui.md)

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
- [x] Golden eval case file defines deterministic payload cases and a live UI case against real paper fixtures.
- [x] Payload golden eval writes JSON/Markdown run summaries and passes the deterministic seed set.
- [x] Live UI golden eval drives a real browser session through login, chat session creation, UI PDF upload, indexing wait, answer/report generation, trace/file collection, and artifact export.
- [x] Live UI golden eval maps quality findings back to likely owning modules such as F017 and F006.
- [x] Live whole-paper golden case passes the stricter `llm_section_global` and unsupported-claim quality gate.
- [x] Golden eval cases explicitly cover evidence QA, whole-paper summary, multi-paper synthesis/comparison, and insufficient evidence.
- [x] Payload runner emits machine-readable owner module hints per failed finding and per case.
- [x] Payload runner can write case-level answer snapshots and failed-case Markdown summaries while continuing after individual failures.
- [x] CLI supports an interview-friendly command shape with `--payload-dir` and `--output-dir` while retaining the prior `--output` path.

## Acceptance Map

| Claim | Acceptance | Evidence | Status |
| --- | --- | --- | --- |
| Quality gate is reusable. | `evaluate_research_answer` accepts `ResearchAnswer.to_dict()`-shaped mappings and returns structured metrics/findings. | EV-010 focused tests. | Passed |
| Citation boundary is guarded. | Memory source in citations fails the evidence QA gate. | EV-010 focused tests. | Passed |
| Route-specific expectations are explicit. | Whole-paper, evidence QA, and non-evidence turn gates encode different expectations. | EV-010 focused tests and CLI test. | Passed |
| Golden eval is runnable outside hand inspection. | CLI can run payload and live UI modes and emit parseable `results.json`, `summary.md`, and case artifacts. | EV-018 payload/live commands. | Passed |
| Live UI quality is currently acceptable for the seed case. | Live whole-paper summary should use `llm_section_global` and keep unsupported claim ratio under threshold. | EV-018 final live run. | Passed |
| Interview benchmark covers the major research-quality modes. | Payload golden cases cover evidence QA, whole-paper summary, multi-paper synthesis, and insufficient evidence with explicit citation/context boundaries. | EV-022 payload command and focused tests. | Passed |
| Failures are attributable. | Failed findings include stable codes and owner module hints; failed cases write Markdown summaries. | EV-022 focused tests. | Passed |

## State Timeline

| Date | State | Trigger | Evidence | Note |
| --- | --- | --- | --- | --- |
| 2026-06-30 | active | User approved F019 after current capability audit | This Feature | Created to own quality evaluation rather than another UI/product surface. |
| 2026-06-30 | completed | First harness implementation verified | EV-010 | Evaluation module, default gates, CLI, and tests landed. |
| 2026-07-04 | completed | User chose plan B with real live UI E2E | EV-018 | Golden eval now has payload/live modes; final live chain and quality gate pass for the seed whole-paper case. |
| 2026-07-06 | completed | User requested interview-facing benchmark expansion | EV-022 | Payload golden eval now has explicit coverage and failure attribution; live UI boundary remains documented. |

## Patch History

| Patch | Date | Commit | Symptom | Root Cause | Protection | Status |
| --- | --- | --- | --- | --- | --- | --- |
| F019.1 | 2026-07-04 | pending | F019 could validate saved answer JSON but could not run real-paper golden eval through live UI. | The first slice stopped at structural answer payload validation; no golden cases or live UI artifact capture existed. | Added golden eval module, CLI, deterministic payload fixtures, live UI bridge, answer/report artifact export, EV-018. | Completed for seed golden set. |
| F019.2 | 2026-07-06 | pending | Golden eval coverage and failure attribution were still too seed/demo-oriented for interview demonstration. | The F019.1 runner could pass seed payload/live cases, but case intent and owner-module attribution were not fully machine-readable. | Added explicit insufficient-evidence and multi-paper thresholds, owner hints in `results.json`, failed-case summaries, CLI aliases, focused tests, and EV-022. | Completed for payload benchmark expansion. |
| F019.3 | 2026-07-06 | pending | Review found payload mode could pass with missing declared paper fixtures or missing required report artifacts. | Payload evaluation treated `paper_paths` and `required_outputs` as descriptive metadata instead of preflighted case contract. | Added payload preflight findings for missing paper fixtures and required report artifacts, copied report payload snapshots when present, and added negative regression tests. | Completed review hardening. |

## Patch Churn Review

F019 has three follow-up rows because the first slice deliberately started as a small quality gate, then grew into an interview-facing golden eval loop. The patches are converging on one invariant rather than adding unrelated scenario branches:

- F019.1 moved from saved answer JSON validation to runnable real-paper golden eval artifacts.
- F019.2 made case coverage and failure attribution explicit for payload benchmark demonstration.
- F019.3 moved validation upstream from answer-only evaluation into case preflight, so declared fixtures and required artifacts are enforced before a case can pass.

Current judgment: another local patch is still acceptable only if it strengthens the same case-contract boundary. If future fixes add more ad hoc per-case rules, stop and consider splitting a new evaluation-schema Feature or ADR. The protection is now automated through focused regression tests for missing paper fixtures, missing required report payloads, multi-paper citation coverage, insufficient-evidence citation refusal, and owner-module attribution.

## Evidence

- [EV-010 F019 Research Quality Evaluation Harness Verification](../evidence/EV-010-f019-research-quality-evaluation-harness-verification.md)
- [EV-018 F019 Golden Eval Live UI E2E](../evidence/EV-018-f019-golden-eval-live-ui-e2e.md)
- [EV-022 F019 Golden Eval Benchmark Expansion](../evidence/EV-022-f019-golden-eval-benchmark-expansion.md)

## Recovery Snapshot

- Read first: this Feature, F004, F011, F017, F018.
- Current capability: quality gates can fail route mismatches, weak citation count, excessive citation count in insufficient-evidence cases, invalid citation source type, wrong summary synthesis mode, context-boundary drift, invalid-source claims, noisy unsupported ratio, missing multi-paper citation coverage, missing declared paper fixtures, missing required report artifacts, and now live UI golden eval regressions.
- Known risks: This is still a structural/contract quality gate, not a semantic truth judge. Only 2 real PDFs are currently available in `paper_data`; the third-paper golden case remains future work. Payload mode is deterministic and currently the recommended interview benchmark. Live UI still covers only one whole-paper case and should be treated as a higher-cost smoke/e2e path rather than the full benchmark.
- Latest live state: final execution chain passed and quality gate passed with `summary_mode=llm_section_global`, `citation_count=19`, and `unsupported_claim_ratio=0.3333`.
- Latest payload benchmark state: 2026-07-06 F019.3 review-hardening run passed 5/5 payload cases and emitted `.pytest_tmp/f0192-review-golden-output/results.json` plus `.pytest_tmp/f0192-review-golden-output/summary.md`.
- Next safe action: Add a third real paper and extend live UI coverage to at least one evidence-QA or multi-paper case before presenting live mode as representative of the whole benchmark.

## Next Step

Add a third real paper, add at least one live evidence-QA or multi-paper case, and measure repeated-run stability without weakening citation evidence boundaries.
