---
id: F023
doc_kind: feature
status: active
owner: solitudeTG
created: 2026-07-07
updated: 2026-07-07
---

# F023: LLM Semantic Auditor

## Goal

在 F022 的 deterministic / lexical semantic audit 底线之上，增加可配置、可测试、可解释、可安全降级的 LLM-backed Semantic Auditor，用于独立判断 claim 与 cited paper/web/database evidence 之间是否存在 supported、partial、unsupported、overreach、source_mismatch 或 insufficient_evidence 关系。

## Vision Anchor

- Source: 用户要求实现 “F023 规则底线 + LLM-backed Semantic Auditor”。
- User pain point: 只有 citation 或 lexical overlap 不能证明 claim 被 evidence entail；系统需要识别看似相关但实际过度推断的科研回答。
- Desired outcome: deterministic audit 始终作为安全底线；当模型配置存在时，LLM auditor 增强 audit payload 和 trace；当 LLM 不可用或失败时显式降级。
- Non-goals: 不重写 ScienceClaw UI，不做三层记忆产品化，不做新 landing page，不做 crawler/database 自动检索，不把 auditor rationale 当 citation evidence。
- Exit Gate source: 本 Feature、EV-024、聚焦测试、payload golden eval、live UI Case C artifact。

## Feature Intake

- Original problem: F022 的 semantic audit 仍主要是 deterministic / heuristic floor，不是真正的 entailment auditor。
- User pain point: 研究用户可能看到相关 citation 后误以为结论被支持，尤其是跨域、临床安全、强因果结论。
- Capability promise: LLM auditor 只消费 claim、cited evidence quote/snippet、source identity metadata 和 deterministic result，并输出机器可读 finding code。
- Non-goals: 不让 LLM 输出进入 citations；不伪造 Agent lifecycle；不降低 F019/F022 quality gate。
- Acceptance source: 用户任务说明中的 F023 验收清单。
- Open questions: 本地真实 LLM 配置和 UI 服务稳定性决定 live Case C 是否能实跑；无配置时必须记录 blocked 或降级状态。

## Capability Contract

- `audit_evidence_claims` 继续提供 deterministic-only audit。
- `audit_evidence_claims_with_semantic_auditor` 在 auditor 可用时叠加 LLM finding；失败或无配置时保留 deterministic result。
- Audit payload 包含 `semantic_auditor.mode`、`model`、`claim_count`、`overreach_count`、`unsupported_count`、`llm_auditor_status`。
- Claim payload 可包含 `deterministic_support_status`、`llm_support_status`、`llm_rationale`、`finding_code=llm_*`。
- LLM auditor 输入只包含 claim text、cited evidence quote/snippet、source identity metadata、deterministic audit result。
- ActivityPanel / trace 只记录真实 step：deterministic audit completed、LLM semantic auditor completed/unavailable/failed。
- Quality gate 可要求 `require_llm_semantic_audit=true`，缺字段或 mode 不匹配必须失败。

## Decision Context

### Why

F022 已经让 audit payload 可机器检查，但 semantic support 仍由 lexical heuristic 推断。F023 把 LLM 判断做成 overlay，而不是替代底线，可以在提高 overreach 检出率的同时保留 deterministic fail-safe。

### Why Not

没有把 auditor 作为 citation evidence，因为 auditor 是过程判断，不是 paper/web/database source。没有新增 Auditor Agent lifecycle，因为本 slice 没有真实 subagent 调度，只是 answer route 中的审计步骤。

### If Modifying This Area, Check

- F004 citation evidence boundary。
- F006 Evidence Audit。
- F018 claim-level calibration。
- F019 quality evaluation harness。
- F022 semantic audit and multi-paper synthesis。
- EV-024 verification commands and artifacts。

## Current Status

Active, blocked on live `llm_enhanced` evidence. Backend audit/answer/evaluation/golden/live E2E script changes have been added. Focused tests, payload golden eval, and AgentMentor strict knowledge check pass. The current live UI Case C run exercised safe degradation because the configured model returned `PermissionDeniedError`; that is valid fallback evidence but not sufficient F023 acceptance evidence for the LLM-backed live auditor.

## Links

### Evidence

- [EV-024 LLM Semantic Auditor Verification](../evidence/EV-024-llm-semantic-auditor-verification.md)

### Decisions / ADRs

- None.

### Lessons

- None yet.

### Specs / Plans

- None. The user request provided the accepted task boundary.

### External Context

- Local live UI Case C depends on a running ScienceClaw frontend/backend stack and at least one real PDF fixture under `paper_data/`.

### Related Features

- [F006 Evidence Audit](F006-evidence-audit.md)
- [F018 Claim-Level Citation Audit Calibration](F018-claim-level-citation-audit-calibration.md)
- [F019 Research Quality Evaluation Harness](F019-research-quality-evaluation-harness.md)
- [F022 Semantic Evidence Audit and Multi-paper Synthesis](F022-semantic-evidence-audit-and-multi-paper-synthesis.md)

## Acceptance Criteria

- [x] Deterministic audit remains available and is the default floor.
- [x] Optional LLM semantic auditor can overlay claim support status and `llm_*` finding codes.
- [x] LLM missing/failure/invalid output safely degrades to deterministic audit with metadata.
- [x] Answer route records real deterministic and LLM auditor trace steps.
- [x] Evaluation can require LLM enhanced audit fields and fail when missing.
- [x] Payload golden eval includes overreach and unsupported LLM-audited cases.
- [ ] Live UI Case C runs through real browser UI upload and Chat textarea question, writes artifacts, and passes with `semantic_auditor.mode=llm_enhanced` and at least one claim carrying `llm_support_status`, `llm_rationale`, and an `llm_*` finding code.

## Acceptance Map

| Claim | Acceptance | Evidence | Status |
| --- | --- | --- | --- |
| LLM auditor is an overlay, not a replacement. | Deterministic audit still returns without LLM; LLM failure preserves deterministic claims. | Focused `test_research_audit.py`. | Passed |
| Answer payload exposes LLM auditor metadata. | Injected auditor produces `llm_enhanced`, `llm_overreach`, and per-claim LLM fields. | Focused `test_research_answering.py`. | Passed |
| Quality gate enforces LLM audit when required. | Missing `semantic_auditor` fails with `llm_semantic_auditor_missing`. | Focused `test_research_evaluation.py` and golden eval tests. | Passed |
| Payload golden cases cover overreach and unsupported. | `leo_llm_overreach_payload_001` and `leo_llm_unsupported_payload_001` pass with required LLM audit. | `.pytest_tmp/f023-golden`. | Passed |
| Real UI path proves Case C behavior. | Browser uploads real PDF, asks overreach question through Chat textarea, records audit trace, and proves live `llm_enhanced` auditor judgment. | `.pytest_tmp/f023-live-case-c` currently shows `llm_failed/PermissionDeniedError`. | Blocked |

## State Timeline

| Date | State | Trigger | Evidence | Note |
| --- | --- | --- | --- | --- |
| 2026-07-07 | active | User requested F023 | This Feature | New boundary created after F022 to avoid overloading F006/F019 patch chains. |
| 2026-07-07 | partially verified | Backend and payload verification passed | EV-024 | Live UI Case C remains the completion blocker. |
| 2026-07-07 | blocked on live LLM evidence | Review found Case C accepted fallback as pass | EV-024 | Live model call failed with `PermissionDeniedError`; script now requires `llm_enhanced` and must fail this artifact until a valid model credential is available. |

## Patch History

| Patch | Date | Commit | Symptom | Root Cause | Protection | Status |
| --- | --- | --- | --- | --- | --- | --- |
| F023.1 | 2026-07-07 | pending | Semantic audit lacked a configurable LLM entailment overlay and LLM-required quality gate. | F022 semantic fields were deterministic heuristics only. | Added LLM auditor overlay, fallback metadata, route trace, quality checks, payload golden cases, and Case C script assertions. | backend/payload verified; live blocked |
| F023.2 | 2026-07-07 | pending | Live Case C passed even though `semantic_auditor.mode=llm_failed` and no claim had LLM support/rationale fields. | The Case C script accepted `insufficient_evidence_should_refuse` and did not require `require_llm_semantic_audit=True`. | Case C now requires `semantic_auditor.mode=llm_enhanced`, claim-level `llm_support_status`/`llm_rationale`, and an `llm_*` finding code; fallback is documented as limitation only. | verified |

## Evidence

- [EV-024 LLM Semantic Auditor Verification](../evidence/EV-024-llm-semantic-auditor-verification.md)

## Recovery Snapshot

- Read first: this Feature, F022, F019, EV-024.
- Current implementation files: `audit.py`, `answering.py`, `evaluation.py`, `golden_eval.py`, `sessions.py`, `research_ui_e2e.py`, focused tests, payload cases.
- Safe fallback invariant: if LLM auditor is absent, fails, or returns invalid JSON/status, the deterministic audit remains the returned audit and metadata records the fallback mode.
- Latest live state: Case C ran through real browser UI with zero citations and `insufficient_evidence_should_refuse`; LLM auditor metadata recorded `llm_failed` with `PermissionDeniedError`. This is fallback evidence only and must not satisfy F023 completion.
- Next safe action: provide a model credential/config that permits auditor calls, then rerun Case C to capture a live `llm_enhanced` artifact.

## Next Step

Rerun live Case C with a model credential that permits auditor calls to capture a live `llm_enhanced` artifact.
