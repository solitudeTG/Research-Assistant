---
id: EV-025
doc_kind: evidence
scope: project
feature_refs:
  - docs/features/F024-evidence-matrix-literature-review.md
created: 2026-07-07
updated: 2026-07-07
---

# EV-025: Evidence Matrix Literature Review Verification

## Supports Claim

F024 implements a ScienceClaw-native 7-paper literature review workflow that starts from Chat UI, builds a structured Evidence Matrix, generates a Markdown literature review report with sidecar artifacts, records true ActivityPanel trace events, and preserves paper-only citation grounding for the accepted live corpus.

## Verification Scope

Covered:

- Backend Evidence Matrix construction and literature review answer metadata.
- Report generation sidecar for `.evidence-matrix.json`.
- Session route trace steps for selected papers, matrix build, synthesis audit, and report generation.
- Evaluation and golden eval gates for matrix structure, distinct paper count, linked cells, report sections, and citation source types.
- Live UI E2E Case D with 7 real PDFs uploaded through ScienceClaw UI and question submitted through Chat.

Not covered:

- The later one-click Demo/validation-chain Feature.
- Three-layer memory productization.
- Large-scale literature search/corpus discovery UI.

## Corpus

Local path: `paper_data/f024_7paper_corpus/`

Manifest: `paper_data/f024_7paper_corpus/manifest.json`

The live corpus contains 7 open-access arXiv PDFs on LEO satellite beamforming / communications:

| File | Source | Note |
| --- | --- | --- |
| `01-space-time-beamforming-leo.pdf` | `https://arxiv.org/abs/2505.07547` | arXiv PDF, open access |
| `02-joint-beamforming-satellite-selection-ican.pdf` | `https://arxiv.org/abs/2410.19358` | arXiv PDF, open access |
| `03-scalable-distributed-beamforming-networked-leo.pdf` | `https://arxiv.org/abs/2506.01382` | arXiv PDF, open access |
| `04-direct-leo-satellite-to-smartphone-distributed-beamforming.pdf` | `https://arxiv.org/abs/2308.05055` | arXiv PDF, open access |
| `05-hybrid-beamforming-massive-mimo-leo.pdf` | `https://arxiv.org/abs/2104.11158` | arXiv PDF, open access |
| `06-isac-enabled-leo-satellite-systems.pdf` | `https://arxiv.org/abs/2304.00941` | arXiv PDF, open access |
| `07-llm-channel-prediction-predictive-beamforming-leo.pdf` | `https://arxiv.org/abs/2510.10561` | arXiv PDF, open access |

## Checks

Focused pytest:

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'
python -m pytest ScienceClaw\backend\tests -k "research_answering or research_audit or research_evaluation or research_golden_eval or research_ui_e2e_script or research_session_routes" -q --basetemp .pytest_tmp\f024-focused
```

Final review-fix result:

```powershell
python -m pytest ScienceClaw\backend\tests -k "research_answering or research_audit or research_evaluation or research_golden_eval or research_ui_e2e_script or research_session_routes" -q --basetemp .pytest_tmp\f024-review-focused-final
```

Result: Pass, `147 passed, 155 deselected, 3340 warnings`.

Golden eval:

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'
python ScienceClaw\backend\scripts\research_golden_eval.py --cases docs\evals\research_golden_cases.json --payload-dir docs\evals\payloads --output-dir .pytest_tmp\f024-golden
```

Final review-fix result:

```powershell
python ScienceClaw\backend\scripts\research_golden_eval.py --cases docs\evals\research_golden_cases.json --payload-dir docs\evals\payloads --output-dir .pytest_tmp\f024-review-golden-final
```

Result: Pass, `cases=11 passed=11 failed=0`.

Live UI Case D:

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'
python ScienceClaw\backend\scripts\research_ui_e2e.py `
  --frontend-url http://127.0.0.1:5180 `
  --api-base-url http://127.0.0.1:5180/api/v1 `
  --literature-review `
  --paper-dir "E:\Self-Project\Research-Assistant\paper_data\f024_7paper_corpus" `
  --min-paper-count 7 `
  --question "Build a literature review across these papers. Compare the main methods, evidence strength, agreements, disagreements, limitations, and open research gaps. Include an evidence matrix." `
  --output-dir .pytest_tmp\f024-live-literature-review-7papers `
  --timeout-ms 360000
```

Final review-fix result:

```powershell
python ScienceClaw\backend\scripts\research_ui_e2e.py `
  --frontend-url http://127.0.0.1:5180 `
  --api-base-url http://127.0.0.1:5180/api/v1 `
  --literature-review `
  --paper-dir "E:\Self-Project\Research-Assistant\paper_data\f024_7paper_corpus" `
  --min-paper-count 7 `
  --question "Build a literature review across these papers. Compare the main methods, evidence strength, agreements, disagreements, limitations, and open research gaps. Include an evidence matrix." `
  --output-dir .pytest_tmp\f024-review-live-literature-review-7papers `
  --timeout-ms 360000
```

Result: Pass.

- Session: `fbStXYrymmqCgeRnZUeKQ2`
- Question delivery: `chat_ui`
- Report delivery: `chat_ui`
- Citation count: `53`
- Matrix `paper_count`: `7`
- Matrix `theme_count`: `4`
- Matrix evidence-linked cells: `28`
- Quality report: `quality_reports.literature_review.passed=true`
- Report-level audit: `claim_count=12`, `partial_claim_count=12`, `unsupported_claim_count=0`, `invalid_source_count=0`
- Output files: `results.json`, `answer.json`, `evidence-matrix.json`, `literature-review.md`, `summary.md`, and `case-a-report.json` exist and are readable.
- Round files:
  - `research-report-JMX9bVRh5ypupMqhRLNng5.evidence-matrix.json`
  - `research-report-JMX9bVRh5ypupMqhRLNng5.evidence.json`
  - `research-report-JMX9bVRh5ypupMqhRLNng5.md`

AgentMentor checks:

```powershell
python C:\Users\HUAWEI\.codex\skills\using-agentmentor\scripts\knowledge_check.py --root E:\Self-Project\Research-Assistant --docs-path docs --strict
```

Result: Pass, `Errors: 0`, `Warnings: 0`.

```powershell
python C:\Users\HUAWEI\.codex\skills\using-agentmentor\scripts\knowledge_check.py --root E:\Self-Project\Research-Assistant --docs-path docs --feature-index docs\features\F024-evidence-matrix-literature-review.md
```

Result: Pass, `Errors: 0`, `Warnings: 0`.

## Results

Pass; F024 completion evidence captured.

- Live UI uploaded and indexed exactly 7 real PDFs from `paper_data/f024_7paper_corpus/`.
- Answer payload contains `summary_synthesis.mode=evidence_matrix_literature_review`.
- Evidence Matrix artifact exists at `.pytest_tmp/f024-live-literature-review-7papers/evidence-matrix.json`.
- Literature review report dump exists at `.pytest_tmp/f024-live-literature-review-7papers/literature-review.md`.
- Report sidecars exist in session files as `.evidence.json` and `.evidence-matrix.json`.
- Review fix evidence exists at `.pytest_tmp/f024-review-live-literature-review-7papers/`.
- The audit now covers final report-level synthesis claims, agreements, disagreements/tensions, limitations/gaps, and conclusion through citation labels plus quote basis; it is not limited to matrix quote snippets.
- Live Case D now fails if `markdown_path`, `evidence_map_path`, or `evidence_matrix_path` is missing/unreadable, or if copied `literature-review.md` / `evidence-matrix.json` is missing.
- ActivityPanel steps include true upload/parse/index and F024 matrix/report steps.
- Citations are paper evidence only for the accepted live corpus.

## Artifacts

- `.pytest_tmp/f024-focused`
- `.pytest_tmp/f024-review-focused-final`
- `.pytest_tmp/f024-golden/results.json`
- `.pytest_tmp/f024-golden/summary.md`
- `.pytest_tmp/f024-review-golden-final/results.json`
- `.pytest_tmp/f024-review-golden-final/summary.md`
- `.pytest_tmp/f024-live-literature-review-7papers/results.json`
- `.pytest_tmp/f024-live-literature-review-7papers/answer.json`
- `.pytest_tmp/f024-live-literature-review-7papers/evidence-matrix.json`
- `.pytest_tmp/f024-live-literature-review-7papers/literature-review.md`
- `.pytest_tmp/f024-live-literature-review-7papers/summary.md`
- `.pytest_tmp/f024-review-live-literature-review-7papers/results.json`
- `.pytest_tmp/f024-review-live-literature-review-7papers/answer.json`
- `.pytest_tmp/f024-review-live-literature-review-7papers/evidence-matrix.json`
- `.pytest_tmp/f024-review-live-literature-review-7papers/literature-review.md`
- `.pytest_tmp/f024-review-live-literature-review-7papers/summary.md`
- `.pytest_tmp/f024-review-live-literature-review-7papers/case-a-report.json`
- `docs/evals/payloads/f024_literature_review_7paper_payload_001.answer.json`
- `docs/evals/payloads/f024_literature_review_7paper_payload_001.report.json`

## Limitations

- Some PDF title extraction still falls back poorly for a subset of arXiv PDFs; matrix identity remains traceable via `paper_id`, citation labels, local filenames, and corpus manifest.
- The live E2E depends on a running local frontend/backend stack. During verification, Vite 5180 had to be pointed at the current backend on 12003 because Docker owned 12001.
- The deterministic literature-review audit gives report-level synthesis claims a conservative `partial` status when the claim includes paper citation labels and a matching quote basis. It does not upgrade broad synthesis to fully approved without stronger direct support.
- In the latest live run, the optional LLM semantic auditor did not provide a usable overlay (`llm_failed` metadata), so acceptance rests on the deterministic floor as required.

## Notes

- F019/F022/F023 remain related Features, but EV-025 is direct completion evidence only for F024.
- The final accepted live run used the requested `--timeout-ms 360000` and passed.

## Recovery Snapshot

- If live UI fails with `paper_count < 7`, do not mark F024 complete; inspect `paper_data/f024_7paper_corpus/`, upload events, and `research/status`.
- If live UI hangs at indexing, verify `research/status` returns `paper_count >= 7`.
- If answer lacks matrix, verify the literature-review branch uses `list_reader_scope_evidence_from_database`, not single-paper whole-paper retrieval.
- If report lacks sidecar, inspect `generate_markdown_research_report` and `MarkdownReportArtifact.evidence_matrix_path`.
- If quality fails on unsupported ratio, inspect `answer.audit.claims`; F024 deterministic audit should cover final report-level synthesis claims with citation labels and `Evidence basis`, not only matrix quote snippets or uncited generic synthesis prose.
- If live E2E fails before answer POST, inspect whether the ChatBox send button is enabled (`bg-gradient-to-r`) after upload/index reload; Case D submits by clicking the enabled Chat send button, not by calling backend APIs.
