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

F025 provides a repo-local one-command validation chain that organizes F019/F022/F023/F024 into reproducible quick/full demo artifacts. The chain produces machine-readable JSON and human-readable Markdown, runs stable payload golden eval, calls real live UI E2E paths, and preserves honest blocked status for optional live LLM Case C.

## Verification Scope

Covered:

- Environment/preflight and F024 corpus fixture checks.
- Focused pytest for golden eval, UI E2E assertions, demo validation runner, and research evaluation.
- Payload golden eval with 15 payload cases.
- Four new F025 payload cases:
  - method / limitation summary.
  - citation-grounded QA with multi-citation support.
  - insufficient-evidence refusal with no fabricated citation.
  - literature-review matrix negative gate with `expected_result=fail`.
- Quick validation chain.
- Full validation chain using live UI health, live UI smoke, optional Case C, and F024 Case D.
- Review hardening for required live blocker aggregation.
- AgentMentor strict validation and F025 Feature Index validation.

Not covered:

- Required live LLM Case C completion in this run; model returned `PermissionDeniedError`.
- New research capability beyond existing F019/F022/F023/F024 paths.
- UI redesign, new Workbench shell, or new ActivityPanel events.

## Case Set

新增 F025 payload cases:

- `f025_method_limitation_summary_payload_001`
- `f025_multicitation_evidence_qa_payload_001`
- `f025_insufficient_refusal_no_fabricated_citation_payload_001`
- `f025_literature_review_matrix_negative_payload_001`

Negative case behavior:

- `expected_result=fail`
- `actual_quality_passed=false`
- observed findings include `citation_source_type_invalid`, `evidence_matrix_paper_count_too_low`, `evidence_matrix_theme_count_too_low`, `evidence_matrix_linked_cell_count_too_low`, `literature_review_report_section_missing`, and `multi_paper_citation_coverage_too_low`.

## Checks

Focused pytest:

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'
python -m pytest ScienceClaw\backend\tests -k "research_golden_eval or research_ui_e2e_script or demo_validation or research_evaluation" -q --basetemp .pytest_tmp\f025-focused
```

Initial result: Pass, `46 passed, 264 deselected, 1 warning`.

Review hardening result after P1 fix:

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'
python -m pytest ScienceClaw\backend\tests -k "demo_validation or research_golden_eval or research_ui_e2e_script or research_evaluation" -q --basetemp .pytest_tmp\f025-review-focused
```

Result: Pass, `49 passed, 264 deselected, 1 warning`.

Golden eval:

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'
python ScienceClaw\backend\scripts\research_golden_eval.py --cases docs\evals\research_golden_cases.json --payload-dir docs\evals\payloads --output-dir .pytest_tmp\f025-golden
```

Result: Pass, `cases=15 passed=15 failed=0`.

Quick validation chain:

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'
python ScienceClaw\backend\scripts\research_demo_validation.py --mode quick --output-dir .pytest_tmp\f025-demo-validation-quick
```

Result: Pass, `overall_status=pass`.

Full validation chain:

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

Result after review hardening: Partial, `overall_status=partial`.

- Environment precheck: pass.
- Corpus fixture check: pass.
- Focused tests inside chain: pass, 46 passed.
- Golden eval inside chain: pass, 15/15.
- Live UI health: pass.
- Live UI smoke: pass.
- Case C semantic auditor: blocked, session `Nrn7kidUrq8BboRExjKVNg`, `semantic_auditor_mode=llm_failed`, model `qwen3.7-plus`, finding code `insufficient_evidence_should_refuse`, failure `PermissionDeniedError`.
- Case D literature review: pass, session `V48aUaZPveXwNJN8MpvDqU`, `paper_count=7`, `theme_count=4`, `linked_cell_count=28`, `citation_count=53`.

P1 review hardening:

- Function-level regression reproduced the bug: blocked `live-ui-health-check`, blocked required `live-ui-smoke`, and blocked required `case-d-literature-review-7paper` previously produced `overall_status=partial`.
- `_overall_status()` now returns `partial` only when the blocked set contains optional `case-c-semantic-auditor` and no other blocked steps.
- Any non-Case-C blocked step now returns `overall_status=blocked`.
- `--llm-case-c required` with blocked Case C still returns `blocked`.

AgentMentor strict:

```powershell
python C:\Users\HUAWEI\.codex\skills\using-agentmentor\scripts\knowledge_check.py --root E:\Self-Project\Research-Assistant --docs-path docs --strict
```

Result: Pass after F025/EV-026 updates, `Errors: 0`, `Warnings: 0`.

F025 Feature Index:

```powershell
python C:\Users\HUAWEI\.codex\skills\using-agentmentor\scripts\knowledge_check.py --root E:\Self-Project\Research-Assistant --docs-path docs --feature-index docs\features\F025-reproducible-demo-validation-chain.md
```

Result: Pass after Feature Index update, `Errors: 0`, `Warnings: 0`.

## Results

Pass for F025 quick validation and full validation orchestration; full run is intentionally `partial` because optional live LLM Case C was blocked by model permission. This does not mark F023 live LLM as passed in this run.

Accepted F025 completion interpretation:

- F025 runner exists and is tested.
- Quick validation passes.
- Full validation generates complete `results.json` and `summary.md`.
- F024 Case D passes through real live UI.
- Case C optional blocked is explicitly recorded and does not become a pass.
- Golden eval and focused tests pass.
- AgentMentor strict and F025 feature-index pass.

## Artifacts

- `.pytest_tmp/f025-focused`
- `.pytest_tmp/f025-review-focused`
- `.pytest_tmp/f025-golden/results.json`
- `.pytest_tmp/f025-golden/summary.md`
- `.pytest_tmp/f025-demo-validation-quick/results.json`
- `.pytest_tmp/f025-demo-validation-quick/summary.md`
- `.pytest_tmp/f025-demo-validation-quick/commands.json`
- `.pytest_tmp/f025-demo-validation-quick/environment.json`
- `.pytest_tmp/f025-demo-validation-full/results.json`
- `.pytest_tmp/f025-demo-validation-full/summary.md`
- `.pytest_tmp/f025-demo-validation-full/commands.json`
- `.pytest_tmp/f025-demo-validation-full/environment.json`
- `.pytest_tmp/f025-demo-validation-full/live-ui-smoke/results.json`
- `.pytest_tmp/f025-demo-validation-full/case-c-semantic-auditor/results.json`
- `.pytest_tmp/f025-demo-validation-full/case-c-semantic-auditor/case-c-answer.json`
- `.pytest_tmp/f025-demo-validation-full/case-d-literature-review-7paper/results.json`
- `.pytest_tmp/f025-demo-validation-full/case-d-literature-review-7paper/answer.json`
- `.pytest_tmp/f025-demo-validation-full/case-d-literature-review-7paper/evidence-matrix.json`
- `.pytest_tmp/f025-demo-validation-full/case-d-literature-review-7paper/literature-review.md`
- `docs/evals/payloads/f025_method_limitation_summary_payload_001.answer.json`
- `docs/evals/payloads/f025_multicitation_evidence_qa_payload_001.answer.json`
- `docs/evals/payloads/f025_insufficient_refusal_no_fabricated_citation_payload_001.answer.json`
- `docs/evals/payloads/f025_literature_review_matrix_negative_payload_001.answer.json`
- `docs/evals/payloads/f025_literature_review_matrix_negative_payload_001.report.json`

## Notes

- F025 does not promote memory, tool logs, model reasoning, or process trace into citation evidence.
- Live UI smoke and Case D use existing ScienceClaw UI/E2E script; no fake trace or fake artifact was introduced.
- The full chain returns process exit 0 for `partial` so optional Case C blockers can still produce a usable validation report. Consumers must read `overall_status` and `case_c.status`.
- The F024 corpus manifest records source URLs from arXiv open-access records.

## Limitations

- Required Case C should be rerun only when live model permission is available; current artifact is blocked evidence, not F023 live LLM success evidence.
- Full validation depends on local frontend/backend services at `127.0.0.1:5180`.
- `.pytest_tmp` artifacts are local verification outputs and must not be committed.

## Recovery Snapshot

- To reproduce quick: run the quick command above.
- To reproduce live/full: start the local ScienceClaw stack, then run the full command above.
- If quick fails, inspect `focused-tests/stdout.txt`, `golden-eval/results.json`, and `corpus-fixture-check`.
- If full is blocked before Case D, inspect live health and smoke logs under `.pytest_tmp/f025-demo-validation-full/live-ui-smoke/`.
- If Case D fails, inspect upload/indexing, Chat send button, and report sidecar paths in `.pytest_tmp/f025-demo-validation-full/case-d-literature-review-7paper/`.
- If Case C is needed as required evidence, rerun with `--llm-case-c required` after fixing model permissions; do not reuse blocked `llm_failed` artifacts.
