---
id: EV-026
doc_kind: evidence
scope: project
feature_refs:
  - docs/features/F025-reproducible-demo-validation-chain.md
  - docs/features/F019-research-quality-evaluation-harness.md
  - docs/features/F023-llm-semantic-auditor.md
  - docs/features/F024-evidence-matrix-literature-review.md
created: 2026-07-07
updated: 2026-07-07
---

# EV-026: Reproducible Demo Validation Chain Verification

## Supports Claim

F025 provides a repo-local validation chain that organizes F019/F022/F023/F024 into reproducible quick/full demo artifacts. The chain produces machine-readable JSON and human-readable Markdown, runs stable payload golden eval, calls real live UI E2E paths, and can produce a full `pass` for interview/release evidence by reusing a previously accepted real `llm_enhanced` Case C artifact.

## Verification Scope

Covered:

- Environment/preflight and F024 corpus fixture checks.
- Focused pytest for golden eval, UI E2E assertions, demo validation runner, and research evaluation.
- Payload golden eval with 15 payload cases.
- Four F025 payload cases:
  - method / limitation summary.
  - citation-grounded QA with multi-citation support.
  - insufficient-evidence refusal with no fabricated citation.
  - literature-review matrix negative gate with `expected_result=fail`.
- Quick validation chain.
- Full validation chain using live UI health, live UI smoke, accepted Case C reuse, and F024 Case D.
- Review hardening for required live blocker aggregation.
- AgentMentor strict validation and F025 Feature Index validation.

Not covered:

- A fresh rerun of F023 live LLM Case C in the latest full pass; it intentionally reused `.pytest_tmp/f023-live-case-c-qwen37` because the accepted artifact already contains real browser `llm_enhanced` evidence.
- New research capability beyond existing F019/F022/F023/F024 paths.
- UI redesign, new Workbench shell, or new ActivityPanel events.

## Case Set

F025 payload cases:

- `f025_method_limitation_summary_payload_001`
- `f025_multicitation_evidence_qa_payload_001`
- `f025_insufficient_refusal_no_fabricated_citation_payload_001`
- `f025_literature_review_matrix_negative_payload_001`

Negative case behavior:

- `expected_result=fail`
- `actual_quality_passed=false`
- observed findings include `citation_source_type_invalid`, `evidence_matrix_paper_count_too_low`, `evidence_matrix_theme_count_too_low`, `evidence_matrix_linked_cell_count_too_low`, `literature_review_report_section_missing`, and `multi_paper_citation_coverage_too_low`.

## Checks

Focused demo validation unit test:

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'
python -m pytest ScienceClaw\backend\tests\test_research_demo_validation.py -q --basetemp .pytest_tmp\f025-reuse-test
```

Result: Pass, `10 passed`.

Quick validation chain:

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'
python ScienceClaw\backend\scripts\research_demo_validation.py --mode quick --output-dir .pytest_tmp\completion-assessment-quick
```

Result: Pass, `overall_status=pass`.

- Environment precheck: pass.
- Corpus fixture check: pass, `paper_count=7`, `manifest_paper_count=7`.
- Focused tests: pass, `49 passed` at the time of the assessment run.
- Golden eval: pass, `cases=15 passed=15 failed=0`.

Full validation chain with accepted Case C reuse:

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'
python ScienceClaw\backend\scripts\research_demo_validation.py `
  --mode full `
  --frontend-url http://127.0.0.1:5180 `
  --api-base-url http://127.0.0.1:5180/api/v1 `
  --output-dir .pytest_tmp\f025-full-reuse-accepted-case-c `
  --require-live-ui `
  --require-7paper-review `
  --llm-case-c optional `
  --reuse-existing-llm-artifact .pytest_tmp\f023-live-case-c-qwen37 `
  --timeout-ms 600000
```

Result: Pass, `overall_status=pass`.

- Environment precheck: pass.
- Corpus fixture check: pass.
- Focused tests inside chain: pass, `50 passed`.
- Golden eval inside chain: pass, `15/15`.
- Live UI health: pass, HTTP `200`.
- Live UI smoke: pass, session `MtQUGAUZ7ihuB6UFXvS748`, `citation_count=1`.
- Case C semantic auditor: pass by accepted artifact reuse, session `FjQPSdT36Q4CE5AauEQmEd`, `semantic_auditor_mode=llm_enhanced`, model `qwen3.7-plus`, finding code `llm_insufficient_evidence`.
- Case D literature review: pass, session `bufxV6bGDfCg3aET6BCDS3`, `paper_count=7`, `theme_count=4`, `linked_cell_count=28`, `citation_count=53`.

Historical fresh full validation:

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'
python ScienceClaw\backend\scripts\research_demo_validation.py `
  --frontend-url http://127.0.0.1:5180 `
  --api-base-url http://127.0.0.1:5180/api/v1 `
  --output-dir .pytest_tmp\f025-demo-validation-full `
  --mode full `
  --require-live-ui `
  --require-7paper-review `
  --llm-case-c optional `
  --timeout-ms 600000
```

Historical result: Partial, `overall_status=partial`.

- Case C semantic auditor was blocked because the live model returned `PermissionDeniedError`.
- Case D still passed with 7 papers, 4 themes, 28 linked cells, and 53 citations.
- This artifact remains valid blocked evidence and must not be described as a Case C pass.

AgentMentor strict:

```powershell
python C:\Users\HUAWEI\.codex\skills\using-agentmentor\scripts\knowledge_check.py --root E:\Self-Project\Research-Assistant --docs-path docs --strict
```

Result: Pass, `Errors: 0`, `Warnings: 0`.

F025 Feature Index:

```powershell
python C:\Users\HUAWEI\.codex\skills\using-agentmentor\scripts\knowledge_check.py --root E:\Self-Project\Research-Assistant --docs-path docs --feature-index docs\features\F025-reproducible-demo-validation-chain.md
```

Result: Pass, `Errors: 0`, `Warnings: 0`.

## Results

Pass for F025 quick validation and interview/release full validation.

Accepted F025 completion interpretation:

- F025 runner exists and is tested.
- Quick validation passes.
- Full validation can pass when Case C uses the accepted real `llm_enhanced` artifact and Case D runs live.
- Fresh Case C failures remain honest blocked/partial evidence instead of being converted to pass.
- F024 Case D passes through real live UI.
- Golden eval and focused tests pass.
- AgentMentor strict and F025 feature-index pass.

## Artifacts

- `.pytest_tmp/completion-assessment-quick/results.json`
- `.pytest_tmp/completion-assessment-quick/summary.md`
- `.pytest_tmp/f025-reuse-test`
- `.pytest_tmp/f025-full-reuse-accepted-case-c/results.json`
- `.pytest_tmp/f025-full-reuse-accepted-case-c/summary.md`
- `.pytest_tmp/f025-full-reuse-accepted-case-c/commands.json`
- `.pytest_tmp/f025-full-reuse-accepted-case-c/environment.json`
- `.pytest_tmp/f025-full-reuse-accepted-case-c/live-ui-smoke/results.json`
- `.pytest_tmp/f025-full-reuse-accepted-case-c/case-d-literature-review-7paper/results.json`
- `.pytest_tmp/f025-full-reuse-accepted-case-c/case-d-literature-review-7paper/answer.json`
- `.pytest_tmp/f025-full-reuse-accepted-case-c/case-d-literature-review-7paper/evidence-matrix.json`
- `.pytest_tmp/f025-full-reuse-accepted-case-c/case-d-literature-review-7paper/literature-review.md`
- `.pytest_tmp/f023-live-case-c-qwen37/results.json`
- `.pytest_tmp/f023-live-case-c-qwen37/case-c-answer.json`
- `docs/evals/payloads/f025_method_limitation_summary_payload_001.answer.json`
- `docs/evals/payloads/f025_multicitation_evidence_qa_payload_001.answer.json`
- `docs/evals/payloads/f025_insufficient_refusal_no_fabricated_citation_payload_001.answer.json`
- `docs/evals/payloads/f025_literature_review_matrix_negative_payload_001.answer.json`
- `docs/evals/payloads/f025_literature_review_matrix_negative_payload_001.report.json`

## Notes

- F025 does not promote memory, tool logs, model reasoning, or process trace into citation evidence.
- Live UI smoke and Case D use existing ScienceClaw UI/E2E script; no fake trace or fake artifact was introduced.
- Reused Case C evidence is only accepted because `.pytest_tmp/f023-live-case-c-qwen37` was already produced through real browser UI and contains `semantic_auditor.mode=llm_enhanced`.
- The historical fresh full artifact remains useful for proving the runner records optional LLM permission failures honestly.

## Limitations

- A fresh required Case C should be rerun only when live model permission is available.
- Full validation depends on local frontend/backend services at `127.0.0.1:5180`.
- `.pytest_tmp` artifacts are local verification outputs and must not be committed.

## Recovery Snapshot

- To reproduce quick: run the quick command above.
- To reproduce interview full: start the local ScienceClaw stack, then run the full command with `--reuse-existing-llm-artifact .pytest_tmp\f023-live-case-c-qwen37`.
- To prove fresh LLM availability: rerun with `--llm-case-c required` and no reused artifact after verifying model permission.
- If quick fails, inspect `focused-tests/stdout.txt`, `golden-eval/results.json`, and `corpus-fixture-check`.
- If full is blocked before Case D, inspect live health and smoke logs under `.pytest_tmp/f025-full-reuse-accepted-case-c/live-ui-smoke/`.
- If Case D fails, inspect upload/indexing, Chat send button, and report sidecar paths in `.pytest_tmp/f025-full-reuse-accepted-case-c/case-d-literature-review-7paper/`.
- If Case C is needed as fresh required evidence, do not reuse blocked `llm_failed` artifacts.
