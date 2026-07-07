---
id: F022
doc_kind: feature
status: completed
owner: solitudeTG
created: 2026-07-07
updated: 2026-07-07
---

# F022: Semantic Evidence Audit and Multi-paper Synthesis

## Goal

打通 Semantic Evidence Audit + Multi-paper Research Synthesis 的可信研究工作流，让 Research Assistant 不只返回 citation，还能说明 claim 与多篇论文证据之间的支持关系，并在证据不足时拒绝无证据结论。

## Vision Anchor

- Source: 用户要求面向面试展示端到端可信研究能力：多论文上传、跨论文综合、citation answer/report、claim-level semantic audit、golden eval、payload artifact、live UI E2E evidence。
- User pain point: “检索并引用”不足以证明科研可信性；系统必须能解释证据支持关系、区分 partial/unsupported/insufficient，并拒绝超出论文证据的问题。
- Desired outcome: 真实 ScienceClaw UI 中可上传至少两篇论文，回答跨论文比较问题，并输出可复现的 audit/golden/live E2E 证据。
- Non-goals: 不做完整科学真伪判断，不做外部标注平台，不引入必须联网/付费 API 的验收路径，不做 crawler/PDF exporter/Agent marketplace，不重写 Research Library 或 ScienceClaw UI。
- Exit Gate source: 本 Feature、F004/F006/F011/F017/F018/F019、EV-023、focused tests、payload golden eval、live UI E2E artifacts。

## Feature Intake

- Original problem: 现有能力能做 citation-grounded answer 和结构质量门，但缺少 claim-level semantic audit fields、稳定 finding code、多论文综合正例和 live UI A/B 端到端验收。
- User pain point: 面试展示需要证明系统会拒绝无证据结论，而不是把任意检索片段包装成 citation。
- Capability promise: 增强 audit/answer/eval/live E2E，使 supported/partial/unsupported/source_mismatch/insufficient_evidence 可测、可追溯、可复现。
- Non-goals: 不替换 ScienceClaw app shell，不新增 landing page，不伪造 agent/tool/trace/evidence。
- Acceptance source: 用户 2026-07-07 Goal 与验收清单。
- Open questions: live UI 稳定性仍依赖本地 ScienceClaw 服务、浏览器和 PDF parsing/indexing 状态。

## Capability Contract

- 每个 audit claim 输出 `claim_id`、`claim_text`、`support_status`、semantic/source quality score、`cited_evidence`、`rationale`、稳定 `finding_code`。
- 合法 `support_status` 为 `supported`、`partial`、`unsupported`、`source_mismatch`、`insufficient_evidence`。
- citation evidence 只能来自 `paper` / `web` / `database`，memory/tool logs/model reasoning/process trace 只能作为 context/trace。
- 多论文综合正例必须引用至少两篇不同 paper，除非 admission 明确拒绝或 quality gate 标记 coverage too low。
- evidence insufficient 问题必须输出 insufficient/rejected/no_evidence，不得伪造支持性 citation。
- Golden eval 必须覆盖 supported、partial、semantic mismatch、context-only rejection、multi-paper positive、insufficient evidence refusal。
- Live UI E2E 必须通过真实浏览器和 ScienceClaw UI 上传真实 PDF，捕获 answer payload、trace/activity、artifact/report evidence sidecar。

## Decision Context

### Why

科研工作台的核心价值是可信研究闭环。citation 是 source identity，不是 semantic support；F022 把“有 citation”升级为“claim 与证据关系可审计”。

### Why Not

没有采用重写 UI、引入独立 workbench 或伪造展示 trace 的路线，因为这些会破坏 ScienceClaw 增量开发原则，也无法证明真实产品路径可信。

### If Modifying This Area, Check

- F004 citation evidence boundary。
- F006 audit status、claim extraction、ActivityPanel audit sidecar。
- F011 admission/refusal decision。
- F017/F018 synthesis and audit calibration。
- F019 golden eval payload/live contracts。

## Current Status

Completed. Backend semantic audit fields、multi-paper answer formatting、semantic quality gate、expanded payload golden cases、live UI E2E script support 已实现；review-hardened live UI A/B 实跑证据记录在 EV-023。

## Links

### Evidence

- [EV-023 Semantic Audit Multi-paper Verification](../evidence/EV-023-semantic-audit-multi-paper-verification.md)
- [EV-024 LLM Semantic Auditor Verification](../evidence/EV-024-llm-semantic-auditor-verification.md)

### Decisions / ADRs

- [ADR-001 P0 Research Data and Retrieval Stack](../decisions/ADR-001-p0-research-data-and-retrieval-stack.md)

### Lessons

- None yet.

### Specs / Plans

- None. 本 Feature 直接由用户 Goal 授权，未创建独立 Superpowers spec/plan。

### Related Features

- [F004 Citation Evidence Boundary](F004-citation-evidence-boundary.md)
- [F006 Evidence Audit](F006-evidence-audit.md)
- [F011 Evidence Admission Gate](F011-evidence-admission-gate.md)
- [F017 LLM Section Summary to Global Synthesis](F017-llm-section-summary-global-synthesis.md)
- [F018 Claim-Level Citation Audit Calibration](F018-claim-level-citation-audit-calibration.md)
- [F019 Research Quality Evaluation Harness](F019-research-quality-evaluation-harness.md)

### External Context

- Local ScienceClaw frontend/backend services at `http://127.0.0.1:5180` and Vite proxy `http://127.0.0.1:5180/api/v1` were used for EV-023 live UI E2E.

## Acceptance Criteria

- [x] 新 Feature 文档存在且可由 AgentMentor strict 校验。
- [x] Semantic audit payload 包含 claim-level support status、rationale、semantic relevance、source quality、cited evidence 和 finding code。
- [x] Multi-paper synthesis 正例引用至少两篇不同 paper。
- [x] Insufficient evidence case 拒绝无证据临床安全问题，不伪造 citation。
- [x] Golden eval payload 覆盖 supported、partial、mismatch、context-only rejection、multi-paper positive、insufficient evidence。
- [x] CLI 输出 `results.json` 和 `summary.md`。
- [x] Live UI E2E Case A 通过。
- [x] Live UI E2E Case B 通过。
- [x] Evidence 文档记录命令、产物路径和未覆盖限制。
- [x] memory/tool logs/model reasoning 不进入 citation evidence。
- [x] 未重写 ScienceClaw UI，仍走 Chat/ActivityPanel/file artifact/SSE trace 路径。

## Acceptance Map

| Claim | Acceptance | Evidence | Status |
| --- | --- | --- | --- |
| Semantic audit is claim-level and machine-checkable. | Audit claim dicts include support status, scores, rationale, cited evidence and finding code. | EV-023 focused audit/evaluation tests. | Passed |
| Multi-paper synthesis cites multiple papers. | Positive answer/eval requires at least two citations from distinct paper identities. | EV-023 answering tests and payload golden eval. | Passed |
| Unsupported evidence is refused. | Clinical safety question over LEO beamforming papers produces insufficient admission and zero final citations. | EV-023 answering test and live UI Case B. | Passed |
| Golden eval covers semantic cases. | Case file has supported, partial, mismatch, context-only rejection, multi-paper positive, insufficient evidence cases. | EV-023 payload CLI. | Passed |
| Real UI path is preserved. | E2E script uploads real PDFs through browser UI, submits questions through Chat textarea, clicks the assistant-message report action, and captures answer/report artifacts. | EV-023 review-hardened live UI command. | Passed |

## State Timeline

| Date | State | Trigger | Evidence | Note |
| --- | --- | --- | --- | --- |
| 2026-07-07 | active | User requested end-to-end semantic audit + multi-paper synthesis workflow | This Feature | Created as new capability boundary instead of overloading F006/F019. |
| 2026-07-07 | verified | Backend, payload golden eval, and live UI A/B passed | EV-023 | Two real PDFs uploaded through ScienceClaw UI; multi-paper answer cited 5 paper evidence records across 2 papers; insufficient clinical safety question refused with zero citations. |
| 2026-07-07 | verified | Review hardening for live Chat path and quality gate parity | EV-023 | Live E2E now submits Case A/B through Chat UI, clicks report in the assistant message, and fails if `evaluate_research_answer` fails. |

## Patch History

| Patch | Date | Commit | Symptom | Root Cause | Protection | Status |
| --- | --- | --- | --- | --- | --- | --- |
| F022.1 | 2026-07-07 | pending | Live UI E2E passed while bypassing Chat submit and while Case A failed the research quality gate. | The script triggered answer/report endpoints directly and used weaker bespoke assertions than `evaluate_research_answer`; truncated quote claims were also over-classified as unsupported without preserving enough audit evidence. | E2E now submits Case A/B through the Chat textarea, clicks the assistant-message report action, records delivery mode, and fails if `evaluate_research_answer` fails; semantic audit preserves nearest cited evidence and marks high-overlap truncated claims as partial. | verified |

## Evidence

- [EV-023 Semantic Audit Multi-paper Verification](../evidence/EV-023-semantic-audit-multi-paper-verification.md)

## Recovery Snapshot

- Read first: this Feature, F004, F006, F011, F018, F019, EV-023.
- Current capability state: semantic audit fields, expanded golden payload path, and live UI A/B are implemented and verified in the local ScienceClaw stack.
- Known risks: semantic scoring remains heuristic and not peer-review-grade entailment; live UI depends on local services and PDF parser readiness.
- Next safe action: Review output quality and consider semantic entailment improvements only after adding more real-paper eval cases.
- Unblock condition: ScienceClaw frontend/backend available locally and both PDFs parse/index successfully.

## Next Step

Use the F022 golden/live commands as the interview demo path; add more real-paper cases before broadening claims about semantic precision.
