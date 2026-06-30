---
id: F018
doc_kind: feature
status: completed
owner: solitudeTG
created: 2026-06-30
updated: 2026-06-30
---

# F018: Claim-Level Citation Audit Calibration

## Goal

Calibrate Evidence Audit for long-document research answers so structural Markdown is not audited as a claim, cited synthesis claims can be distinguished as partial instead of unsupported, and ScienceClaw's right-side ActivityPanel remains the place for compact audit inspection.

## Vision Anchor

- Source: User approved the next step after F017 live UI E2E: strengthen the answer trust loop before adding Multi-Agent synthesis.
- User pain point: F017 can produce useful whole-paper summaries, but Evidence Audit can flood the right panel with unsupported rows for headings, section labels, and cited synthesis claims that are semantically related but not extractive quote matches.
- Desired outcome: Final answers remain readable while the audit panel gives a calibrated view of approved, partial, unsupported, and invalid-source claims.
- Non-goals: No peer-review-grade truth verification, no new visual system, no Multi-Agent workflow, no full entailment model, no generated summary as citation evidence.
- Exit Gate source: This Feature, F004, F006, F017, focused audit tests, frontend contract tests, type-check, and live UI E2E with a real paper.

## Feature Intake

- Original problem: Evidence Audit is too literal for hierarchical LLM synthesis and treats some non-claims as unsupported claims.
- Capability promise: Audit claim extraction and support classification become more faithful to the citation contract while preserving explicit evidence boundaries.
- Non-goals: Do not relax citation eligibility; do not hide unsupported claims; do not move audit detail into Chat answer cards.
- Acceptance source: User request on 2026-06-30 to start implementation and run live UI E2E.
- Open questions: Later slices can add LLM entailment judging or evaluation datasets if lexical calibration becomes insufficient.

## Capability Contract

- Structural Markdown headings, labels, separators, and empty formatting lines are not auditable claims.
- Claims with explicit eligible citation labels and strong direct/joint quote support are `approved`.
- Claims with explicit eligible citation labels and measurable but incomplete support are `partial`.
- Claims without explicit citation labels remain `unsupported` when labeled citation evidence exists.
- Context-only sources still produce `invalid_source`; partial support must not turn memory, process trace, model reasoning, or tool logs into citation evidence.
- ActivityPanel keeps ScienceClaw's compact sidecar style: summary counters first, approved claims visible, partial/unsupported detail progressively disclosed.

## Current Status

Completed. F018 calibrates claim extraction and audit status classification for long-document synthesis, adds `partial` audit surfacing in the right ActivityPanel, keeps audit detail out of Chat answer cards, and prevents long-running research answer/report calls from being marked failed by the default 30s frontend timeout.

## Links

### Evidence

- [EV-009 F018 Claim-Level Audit Calibration Verification](../evidence/EV-009-f018-claim-level-audit-calibration-verification.md)

### Decisions / ADRs

- [ADR-001 P0 Research Data and Retrieval Stack](../decisions/ADR-001-p0-research-data-and-retrieval-stack.md)

### Lessons

- None yet.

### Specs / Plans

- None.

### Related Features

- [F004 Citation Evidence Boundary](F004-citation-evidence-boundary.md)
- [F006 Evidence Audit](F006-evidence-audit.md)
- [F017 LLM Section Summary to Global Synthesis](F017-llm-section-summary-global-synthesis.md)

## Acceptance Criteria

- [ ] Audit extraction ignores structural Markdown headings such as `**Global synthesis:**`.
- [ ] Cited synthesis claims with incomplete lexical support are classified as `partial`, not `unsupported`.
- [ ] Unsupported unlabeled claims remain visible and are not silently downgraded.
- [ ] Frontend types and ActivityPanel render partial counts without moving audit data into Chat answer cards.
- [ ] Live UI E2E with a real PDF shows the research answer route, right-panel audit summary, and no audit block in the chat answer body.

## State Timeline

| Date | State | Trigger | Evidence | Note |
| --- | --- | --- | --- | --- |
| 2026-06-30 | active | User approved F018 | This Feature | Created to own claim-level audit calibration and right-panel UI alignment. |
| 2026-06-30 | completed | Implementation and live UI verification passed | [EV-009](../evidence/EV-009-f018-claim-level-audit-calibration-verification.md) | Partial claim status, structural-line filtering, ActivityPanel display, long-running research timeout, and live PDF upload/answer flow verified. |

## Patch History

| Patch | Date | Commit | Symptom | Root Cause | Protection | Status |
| --- | --- | --- | --- | --- | --- | --- |
| F018.1 | 2026-06-30 | pending | Live UI showed calibrated audit but initially displayed `推理失败` after a successful long-running research answer. | Research answer used the global 30s axios timeout while whole-paper LLM synthesis can exceed 30s. | Research answer/report API calls override timeout to 300s; frontend contract test and live UI E2E confirm `panel_has_reasoning_failed=false`. | verified |

## Evidence

[EV-009 F018 Claim-Level Audit Calibration Verification](../evidence/EV-009-f018-claim-level-audit-calibration-verification.md)

## Recovery Snapshot

- Read first: this Feature, F006 Evidence Audit, F004 Citation Evidence Boundary, F017 LLM Section Summary to Global Synthesis.
- Current capability: calibrated audit statuses and ScienceClaw-style right-panel audit display are implemented.
- Known risks: Lexical support remains heuristic; partial is a warning state, not proof of scientific truth. Live UI still showed unsupported claims when the LLM produced broad synthesis claims without enough direct quote overlap.
- Next safe action: Improve final-answer citation discipline or add entailment evaluation before claiming stronger audit precision.

## Next Step

Consider a later slice for stricter LLM output shaping or entailment-based audit review if unsupported synthesis claims remain too noisy.
