---
id: F024
doc_kind: feature
status: completed
owner: solitudeTG
created: 2026-07-07
updated: 2026-07-07
---

# F024: Evidence Matrix Literature Review

## Goal

Productize multi-paper answering as a ScienceClaw-native literature review workflow. A user uploads or selects papers in the existing UI, asks for a review in Chat, and receives a structured Evidence Matrix, a Markdown literature review report, real ActivityPanel trace, and paper-grounded citations.

## Vision Anchor

- Source: User requested the second major gap for 90%+ project completeness: Evidence Matrix plus multi-paper Literature Review.
- User pain point: Multi-paper answers can become untestable paper-by-paper summaries without a matrix, cross-paper themes, traceable claims, or live UI acceptance.
- Desired outcome: At least 7 real PDFs pass through UI upload/indexing/Chat, producing matrix and report artifacts with citation-grounded synthesis.
- Non-goals: No one-click total Demo; no three-layer memory productization; no new workbench/UI shell; no fake multi-agent/tool/trace events; no context-only source promoted to citation.
- Exit Gate source: This Feature, EV-025, focused tests, payload golden eval, live 7-paper UI E2E, and AgentMentor knowledge checks.

## Feature Intake

- Original problem: F022/F023 provided semantic audit and multi-paper synthesis foundations, but did not provide a 7-paper Evidence Matrix, report sidecar, artifact preview, or live Case D acceptance.
- User pain point: Researchers need cross-paper theme comparison, agreements, tensions, gaps, limitations, and citation-grounded conclusions instead of a stack of per-paper summaries.
- Capability promise: A literature review request collects scoped evidence across papers, returns `evidence_matrix` metadata, and writes Markdown report, `.evidence.json`, and `.evidence-matrix.json` artifacts.
- Non-goals: Do not implement the later one-click Demo, productize memory, redesign UI, fabricate agents/tools/trace, or cite memory/tool logs/model reasoning.
- Acceptance source: The user's F024 Evidence Matrix, Literature Review, Quality Gate, Golden Eval, and Live UI E2E requirements.
- Open questions: Some arXiv PDFs still have weak fallback title extraction; paper identity remains traceable through `paper_id`, citation labels, local filenames, and the corpus manifest.

## Capability Contract

- Chat is the product entry point; live E2E submits through the visible Chat textarea/send path.
- ActivityPanel records only true steps: upload, parse, index, selected papers, matrix build, synthesis audit, and report generation.
- `answer.evidence_matrix` exposes paper count, papers, themes, cells, agreements, disagreements, gaps, and limitations.
- Matrix cells preserve paper identity, theme, stance, contribution, method, limitation, evidence ids, citation labels, quote snippets, and support status.
- Report artifact includes Scope / corpus summary, Evidence Matrix, Cross-paper synthesis, Agreements, Disagreements / tensions, Methods comparison, Limitations and evidence gaps, and Citation-grounded conclusion.
- Citations remain limited to `paper`, `web`, or `database` evidence. The accepted live corpus uses `paper` citations only.
- F023 LLM semantic auditor may participate, but the base review flow must pass with deterministic audit floor when live LLM is unavailable.

## Decision Context

### Why

The acceptance unit for a research review is not prose that resembles a review; it is a structured matrix, report artifact, true trace, and quality gate that can be re-read by tests and future Demo tooling.

### Why Not

No new UI/workbench was created because ScienceClaw already owns Chat, ActivityPanel, file/artifact panel, and report generation. The literature review branch does not reuse `list_whole_paper_evidence_in_database`, because that helper intentionally selects the latest single paper; F024 uses reader-scope evidence across papers.

### If Modifying This Area, Check

- F004 Citation Evidence Boundary.
- F006 Evidence Audit.
- F007 Research Artifact Generation.
- F008 Trace Honesty and Activity Panel.
- F019 Research Quality Evaluation Harness.
- F022 Semantic Evidence Audit and Multi-paper Synthesis.
- F023 LLM Semantic Auditor.
- EV-025 verification commands and artifacts.

## Current Status

Completed. Latest accepted live UI session: `fbStXYrymmqCgeRnZUeKQ2`; `paper_count=7`, `theme_count=4`, `linked_cell_count=28`, `citation_count=53`, `quality_reports.literature_review.passed=true`, and report-level synthesis audit produced `12` partial / `0` unsupported claims under the deterministic floor.

## Links

### Evidence

- [EV-025 Evidence Matrix Literature Review Verification](../evidence/EV-025-evidence-matrix-literature-review-verification.md)

### Decisions / ADRs

- None.

### Lessons

- None yet.

### Specs / Plans

- None. The user request provided the accepted task boundary.

### External Context

- Live corpus: `paper_data/f024_7paper_corpus/manifest.json` and 7 arXiv/open-access PDFs under `paper_data/f024_7paper_corpus/`.

### Related Features

- [F007 Research Artifact Generation](F007-research-artifact-generation.md)
- [F008 Trace Honesty and Activity Panel](F008-trace-honesty-activity-panel.md)
- [F019 Research Quality Evaluation Harness](F019-research-quality-evaluation-harness.md)
- [F022 Semantic Evidence Audit and Multi-paper Synthesis](F022-semantic-evidence-audit-and-multi-paper-synthesis.md)
- [F023 LLM Semantic Auditor](F023-llm-semantic-auditor.md)

## Acceptance Criteria

- [x] Live UI E2E uploads/indexes at least 7 real PDFs through ScienceClaw UI and submits the literature review request through Chat.
- [x] Answer payload exposes structured `evidence_matrix` with `paper_count >= 7`.
- [x] Evidence Matrix contains at least 4 themes and at least 10 evidence-linked cells.
- [x] Literature review report artifact exists and includes the required sections.
- [x] Matrix/report synthesis claims are grounded in paper citation labels and quote snippets.
- [x] ActivityPanel trace includes true upload/parse/index/matrix/audit/report steps.
- [x] Golden eval includes a 7-paper payload fixture validating matrix structure, citation grounding, and report sections.
- [x] Focused tests pass without weakening F019/F022/F023 gates.
- [x] AgentMentor strict and F024 feature-index checks pass.

## Acceptance Map

| Claim | Acceptance | Evidence | Status |
| --- | --- | --- | --- |
| 7-paper live UI path is real. | Browser uploaded 7 PDFs and Chat submitted the review question. | `.pytest_tmp/f024-review-live-literature-review-7papers/results.json` session `fbStXYrymmqCgeRnZUeKQ2`. | Passed |
| Matrix is structured and readable. | `paper_count=7`, `theme_count=4`, `linked_cell_count=28`. | `.pytest_tmp/f024-review-live-literature-review-7papers/evidence-matrix.json`. | Passed |
| Report exists as artifact. | Markdown report and evidence/evidence-matrix sidecars are listed in session files and script asserts source/readable output files. | `research-report-JMX9bVRh5ypupMqhRLNng5.md`, `.evidence.json`, `.evidence-matrix.json`. | Passed |
| Citations remain paper-grounded. | Quality report has citation source type `paper` only and matrix cells carry evidence ids/citation labels. | Live `answer.json` and `results.json`. | Passed |
| Report-level synthesis audit is real. | Audit checks synthesis claims, agreements, tensions, limitations/gaps, and conclusion with citation labels plus quote basis, not only matrix snippets. | Live `answer.json`: `claim_count=12`, `partial_claim_count=12`, `unsupported_claim_count=0`. | Passed |
| Golden eval preserves regression coverage. | 11 golden cases passed, including F024 payload case. | `.pytest_tmp/f024-review-golden-final/summary.md`. | Passed |

## State Timeline

| Date | State | Trigger | Evidence | Note |
| --- | --- | --- | --- | --- |
| 2026-07-07 | active | User requested second 90%+ gap | This Feature | Scope excludes one-click Demo and memory productization. |
| 2026-07-07 | verified | Live UI 7-paper Case D passed | EV-025 | Session `9U7hLAES5D3TJyrxXHq837`; matrix/report artifacts generated. |
| 2026-07-07 | review-fixed | Review found audit target and sidecar assertion gaps | EV-025 | Added report-level synthesis audit coverage and strict report sidecar/readability assertions. |
| 2026-07-07 | completed | Focused tests, golden eval, live Case D, AgentMentor checks passed | EV-025 | Latest session `fbStXYrymmqCgeRnZUeKQ2`; no commit/push performed. |

## Patch History

| Patch | Date | Commit | Symptom | Root Cause | Protection | Status |
| --- | --- | --- | --- | --- | --- | --- |
| F024.1 | 2026-07-07 | pending | Literature review request retrieved only one latest paper and produced no matrix. | Single-paper whole-paper helper was reused for multi-paper review. | Literature review branch now uses reader-scope evidence across papers; live 7-paper E2E asserts matrix count. | verified |
| F024.2 | 2026-07-07 | pending | Live E2E waited forever after 7 PDFs were indexed. | Status endpoint returned `paper_count`, while script only accepted `indexed_paper_count`/`papers[]`. | E2E status wait accepts `paper_count >= expected_papers`. | verified |
| F024.3 | 2026-07-07 | pending | Deterministic audit marked abstract synthesis lines as unsupported despite matrix quote grounding. | Audit input used high-level theme claims instead of evidence-cell quote snippets. | Literature-review audit content now checks matrix quote snippets with citation labels. | verified |
| F024.4 | 2026-07-07 | pending | Review showed audit approved matrix snippet claims rather than final report synthesis claims. | F024 audit input did not include report-level Agreements, Disagreements/tensions, Limitations/gaps, and conclusion claims. | Audit input now covers synthesis claims with citation labels and quote basis; audit floor marks evidence-basis synthesis as partial rather than unsupported. | verified |
| F024.5 | 2026-07-07 | pending | Review showed live E2E could pass with weak report sidecar checks, and Chat send was intermittent. | Case D checked `report_payload` only and `_copy_report_markdown` skipped missing files; script used a broad send-button selector / Enter behavior. | Case D asserts `markdown_path`, `evidence_map_path`, `evidence_matrix_path`, output files, and enabled Chat send button click. | verified |

## Patch Churn Review

F024 has five patch rows because live acceptance and review exposed harness boundary failures: wrong evidence retrieval scope, E2E status polling mismatch, matrix-only audit input, weak sidecar checks, and intermittent Chat send. They protect one invariant: a 7-paper review must be verifiable through real UI, structured matrix/report artifacts, and citation-grounded report-level audit. No feature split or ADR is needed yet because all fixes harden the same acceptance path rather than expanding scope.

## Evidence

- [EV-025 Evidence Matrix Literature Review Verification](../evidence/EV-025-evidence-matrix-literature-review-verification.md)

## Recovery Snapshot

- Read first: AGENTS.md, this Feature, F019, F022, F023, EV-025.
- Current implementation files: `answering.py`, `reports.py`, `evaluation.py`, `golden_eval.py`, `sessions.py`, `research_ui_e2e.py`, focused tests, `ChatPage.vue`, golden payloads, `paper_data/f024_7paper_corpus/manifest.json`.
- Latest live artifact path: `.pytest_tmp/f024-review-live-literature-review-7papers/`.
- Latest live session: `fbStXYrymmqCgeRnZUeKQ2`.
- Latest matrix metrics: `paper_count=7`, `theme_count=4`, `linked_cell_count=28`.
- Latest report artifact: `research-report-JMX9bVRh5ypupMqhRLNng5.md` with sidecars `research-report-JMX9bVRh5ypupMqhRLNng5.evidence.json` and `research-report-JMX9bVRh5ypupMqhRLNng5.evidence-matrix.json`.
- Latest report audit metrics: `claim_count=12`, `partial_claim_count=12`, `unsupported_claim_count=0`, `invalid_source_count=0`.
- Next safe action: keep F024 live Case D in the manual release checklist until the later one-click Demo/validation-chain Feature owns full demo orchestration.

## Next Step

Keep F024 as the owner for Evidence Matrix/report regressions. The next independent project gap is the real Golden Eval Corpus + one-click Demo/validation chain, which should be handled by a separate Feature rather than expanding F024.
