---
id: F006
doc_kind: feature
status: active
owner: solitudeTG
created: 2026-06-28
updated: 2026-06-29
---

# F006: Evidence Audit

## Goal

检查研究答案和报告中的 claim 是否被 citation evidence 支撑，并把 unsupported、invalid-source 或弱支撑结论显式暴露。

## Vision Anchor

- 原始请求或来源：`F001`、`AGENTS.md` 证据边界军规。
- 用户痛点或工程问题：有 citation 不等于 claim 被支持；系统需要检查结论和来源之间的关系。
- 期望结果：Evidence Audit 对 answer/report claim 产生可展示、可持久化、可恢复的审计结果。
- 非目标或边界：本 Feature 不负责生成新的 evidence，也不替代人工同行评审。
- Exit Gate 对照来源：本 Feature、audit tests、report/Chat audit rendering tests。

## Feature Intake

- Original problem: Research outputs need claim-level support checking.
- User pain point: Reports can look credible while containing unsupported or overclaimed conclusions.
- Capability promise: Audit claims against citation evidence and expose approved/unsupported/invalid-source states.
- Non-goals: Do not claim full scientific truth verification or source-quality scoring here.
- Acceptance source: `F001`, `AGENTS.md`, focused audit tests.
- Open questions: Stronger semantic entailment and source-quality scoring remain future work.

## Capability Contract

- Audit answer/report claims against eligible citation evidence.
- Distinguish approved, unsupported, and invalid-source claims.
- Persist audit results where answer/report subjects need recovery.
- Surface audit summaries and claim checks in Chat and Markdown reports.
- Keep context-only memory visible but non-citation.

## Decision Context

### Why

Citation presence alone is insufficient. A claim may cite a valid source while still overclaiming beyond the quote.

### Why Not

Hiding unsupported claims was rejected because research users need to see evidence gaps and unresolved conclusions.

### If Modifying This Area, Check

- F004 citation evidence boundary.
- Audit support-score, explicit-label, and invalid-source tests.
- Chat audit panel and Markdown Claim Checks.

## Current Status

Completed for MVP scope.

Evidence Audit can classify answer/report claims against eligible citation evidence, persist and recover audit results, expose unsupported/invalid-source gaps, and surface audit state in ActivityPanel and Markdown reports without placing process detail in the Chat answer body. This does not claim full semantic entailment or peer-review-grade truth verification.

## Links

### Evidence

- [EV-001 Feature Governance Split Validation](../evidence/EV-001-feature-governance-split-validation.md)
- [EV-023 Semantic Audit Multi-paper Verification](../evidence/EV-023-semantic-audit-multi-paper-verification.md)
- [EV-024 LLM Semantic Auditor Verification](../evidence/EV-024-llm-semantic-auditor-verification.md)
- Historical verification currently recorded in [F001](F001-project-vision-and-scope.md).

### Decisions / ADRs

- None.

### Lessons

- None yet.

### Specs / Plans

- [F001 Feature Map and Rules Spec](../specs/F001-feature-map-and-rules-spec.md)

### Related Features

- [F004 Citation Evidence Boundary](F004-citation-evidence-boundary.md)
- [F007 Research Artifact Generation](F007-research-artifact-generation.md)

### External Context

- None.

## Acceptance Criteria

- [x] Audit approves only claims supported by eligible citation evidence.
- [x] Unsupported and invalid-source claims remain visible as gaps.
- [x] Audit results can be persisted and recovered for answer/report subjects.
- [x] Chat and Markdown reports expose audit state without overstating trust.

## Acceptance Map

| Claim | Acceptance | Evidence | Status |
| --- | --- | --- | --- |
| Evidence Audit checks claim support. | Claims receive approved, unsupported, or invalid-source status against eligible paper/web/database citation evidence. | Historical audit red-green verification from `F001`; current research backend suite passed on 2026-06-29. | MVP done |
| Audit handles known overclaim and label failure modes. | Audit rejects context-only citations, no-citation answers, unlabeled evidence claims, invalid-source claims, and overclaims beyond quoted support; it can approve jointly supported claims. | Historical explicit-label, invalid-source, overclaim, multi-citation, and support-score tests from `F001`. | MVP done |
| Audit state is persisted and recoverable. | Answer/report audit results are stored under stable subjects and can be fetched through session-scoped APIs. | Historical audit persistence/retrieval route tests from `F001`; current research backend suite passed on 2026-06-29. | MVP done |
| Audit state is visible without overstating trust. | ActivityPanel shows answer audit sidecars with progressive disclosure; Markdown reports include Claim Checks, Evidence Gaps, Trust Summary, and limitations. | F006.1/F006.2 frontend verification plus report/audit historical tests from `F001`. | MVP done |

## State Timeline

| Date | State | Trigger | Evidence | Note |
| --- | --- | --- | --- | --- |
| 2026-06-28 | active | Feature split from F001 | This Feature and `INDEX.md` | Created to own audit behavior and recovery. |
| 2026-06-29 | patched | User identified Evidence Audit as process-state data that belongs in the right reasoning panel | Frontend contract tests, type-check, build, browser E2E | F006.1 moved answer audit summary and claim checks out of ChatMessage and into ActivityPanel. |
| 2026-06-29 | patched | User clarified that audit detail should not flood the ActivityPanel by default | Frontend contract tests, type-check, build | F006.2 keeps approved claims visible and collapses unsupported/invalid audit claims behind an explicit disclosure. |
| 2026-06-29 | MVP completed | F001 historical evidence migrated to owning Feature | Current research backend suite and AgentMentor strict check | Stronger semantic entailment and source-quality scoring remain future scope. |

## Patch History

| Patch | Date | Commit | Symptom | Root Cause | Protection | Status |
| --- | --- | --- | --- | --- | --- | --- |
| F006.1 | 2026-06-29 | `f18d0cf` | Evidence Audit appeared as a large block below each answer, making the Chat stream carry process/audit data. | Audit display was coupled to the answer component instead of the ScienceClaw ActivityPanel semantics. | Frontend contract requires `证据审计` to be rendered through ActivityPanel research sidecar and absent from ChatMessage answer cards. | verified |
| F006.2 | 2026-06-29 | `d2d986a` | ActivityPanel rendered every audit claim by default, so long answers could display dozens of unsupported claim rows. | Claim-level audit data was technically correct but lacked a progressive disclosure boundary. | Frontend contract requires approved claims to render by default while unsupported/invalid claims are collapsed behind `unsupportedAuditClaimsExpanded`. | verified |
| F006.3 | 2026-07-07 | pending | Interview-facing workflow needed claim-level semantic audit fields and stable finding codes beyond the MVP counters. | The MVP audit payload exposed support counters but not enough machine-checkable rationale, source quality, semantic relevance, or cited-evidence details per claim. | F022 adds backward-compatible `support_status`, semantic/source quality scores, `cited_evidence`, rationale, and finding codes; focused audit/evaluation/golden tests verify the contract. | pending |

## Patch Churn Review

F006 reached three patch rows because the audit surface has evolved from MVP support counters into calibrated ActivityPanel display and now semantic claim-level payloads. The patches converge on one invariant: claim support must be inspectable without turning context, process, or model output into citation evidence.

- F006.1 moved audit detail out of Chat answer cards and into ActivityPanel.
- F006.2 added progressive disclosure for noisy unsupported/invalid rows.
- F006.3 adds machine-checkable semantic fields and stable finding codes while preserving the old counters for compatibility.

Current judgment: F006.3 is still aligned with F006 because it strengthens the audit contract rather than adding a separate source-acquisition or peer-review truth feature. Further changes that introduce LLM entailment judging or source-quality modeling should be split into a new Feature or ADR.

## Evidence

Historical Evidence Audit evidence migrated from `F001`:

- `test_research_audit.py` verified approved/unsupported/invalid-source classification, context-only source rejection, web/database citation eligibility, explicit citation-label requirements, support scores, overclaim rejection, and jointly supported claims.
- Answer/report/route tests verified no-citation answers are unsupported and answer/report audit results persist under stable subjects.
- Report tests verified Claim Checks, Evidence Gaps, Trust Summary, limitations, approved findings gating, and sidecar audit metadata.
- Frontend tests verified audit recovery, ActivityPanel rendering, and collapsed unsupported/invalid claim disclosure.

- 2026-06-29 audit UI verification: `pytest ScienceClaw/backend/tests/test_research_frontend_contracts.py -q` -> `35 passed`.
- 2026-06-29 frontend verification: `npm.cmd run type-check` -> passed; `npm.cmd run build` -> passed with existing warnings.
- Browser E2E on project `E2E UI链路验证 06290349`: right ActivityPanel showed `证据审计 partial` and claim status rows; the Chat answer card did not render the audit block.
- 2026-06-29 audit density verification: `pytest ScienceClaw/backend/tests/test_research_frontend_contracts.py -q` -> `36 passed`; `npm.cmd run type-check` -> passed; `npm.cmd run build` -> passed with existing Browserslist/CSS/chunk-size warnings. Browser automation reached the authenticated chat shell, but historical-session panel inspection timed out before a stable ActivityPanel DOM assertion.
- Current document-convergence verification: `$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python -m pytest ScienceClaw\backend\tests -k research -q --basetemp .pytest_tmp\progress-audit` -> `178 passed`; `knowledge_check.py --strict` -> 0 errors, 0 warnings.

## Recovery Snapshot

- Read first: this Feature, F004, F007 if report output is involved.
- Current capability state: MVP Evidence Audit is complete; answer audit sidecar is visible in ActivityPanel and report audit state is durable.
- Known risks: Lexical support scoring may not cover all semantic entailment cases.
- Next safe action: Attribute audit changes here and verify focused audit plus affected output tests.
- Unblock condition: None.

## Next Step

Create a new audit-quality slice before claiming stronger semantic entailment, contradiction detection, or source-quality scoring.
