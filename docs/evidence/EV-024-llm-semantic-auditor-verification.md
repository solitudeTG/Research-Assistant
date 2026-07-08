---
id: EV-024
doc_kind: evidence
scope: project
feature_refs:
  - docs/features/F023-llm-semantic-auditor.md
  - docs/features/F006-evidence-audit.md
  - docs/features/F019-research-quality-evaluation-harness.md
  - docs/features/F022-semantic-evidence-audit-and-multi-paper-synthesis.md
created: 2026-07-07
updated: 2026-07-07
---

# EV-024: LLM Semantic Auditor Verification

## Supports Claim

F023 adds an LLM-backed semantic auditor overlay while preserving deterministic audit as the safety floor. The audit payload and quality gate can distinguish LLM enhanced findings such as `llm_overreach` and `llm_unsupported`, and fallback states are machine-readable.

## Verification Scope

Covered so far:

- Audit overlay and safe fallback unit tests.
- Answering integration with injected semantic auditor and unavailable model config.
- Evaluation gate requiring LLM semantic auditor metadata.
- Golden eval schema and payload cases for `llm_overreach` and `llm_unsupported`.
- Live UI E2E script support for Case C assertions and artifacts.

Live UI Case C:

- Real browser live UI Case C executed against the local ScienceClaw stack at `http://127.0.0.1:5180`.
- Historical `qwen3.6-flash-2026-04-16` model calls failed with `PermissionDeniedError`; those answers safely downgraded to deterministic audit and recorded `semantic_auditor.mode=llm_failed`.
- Review result: the fallback artifact is not accepted as F023 live Case C completion evidence. Case C now requires `semantic_auditor.mode=llm_enhanced`, claim-level `llm_support_status`, `llm_rationale`, and an `llm_*` finding code.
- Accepted result: after refreshing the backend runtime to `qwen3.7-plus`, live Case C passed with `semantic_auditor.mode=llm_enhanced`, `llm_auditor_status=completed`, and `finding_code=llm_insufficient_evidence`.

## Case Set

New payload golden cases:

- `leo_llm_overreach_payload_001`: citation is related to LEO beamforming, but claim overreaches to hospital patient safety outcomes; expected `support_status=overreach`, `finding_code=llm_overreach`, and `semantic_auditor.mode=llm_enhanced`.
- `leo_llm_unsupported_payload_001`: citation is about communication/navigation beamforming, but claim says randomized clinical trial results; expected `support_status=unsupported`, `finding_code=llm_unsupported`, and `semantic_auditor.mode=llm_enhanced`.

Planned live UI Case C question:

```text
Do these LEO beamforming papers prove clinical safety outcomes for medical patients?
```

## Checks

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python -m pytest ScienceClaw\backend\tests -k "research_audit or research_answering or research_evaluation or research_golden_eval or research_ui_e2e_script" -q --basetemp .pytest_tmp\f023-focused
```

Result: Pass, `73 passed, 217 deselected, 107 warnings`.

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python ScienceClaw\backend\scripts\research_golden_eval.py --cases docs\evals\research_golden_cases.json --payload-dir docs\evals\payloads --output-dir .pytest_tmp\f023-golden
```

Result: Pass, `cases=10 passed=10 failed=0`.

```powershell
python C:\Users\HUAWEI\.codex\skills\using-agentmentor\scripts\knowledge_check.py --root E:\Self-Project\Research-Assistant --docs-path docs --strict
```

Result: Pass, `Errors: 0`, `Warnings: 0`.

Live UI Case C command:

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python ScienceClaw\backend\scripts\research_ui_e2e.py --frontend-url http://127.0.0.1:5180 --api-base-url http://127.0.0.1:5180/api/v1 --paper-path "E:\Self-Project\Research-Assistant\paper_data\Space-Time_Beamforming_for_LEO_Satellite_Communications_Enabling_Extremely_Narrow_Beams(1).pdf" --question "Do these LEO beamforming papers prove clinical safety outcomes for medical patients?" --semantic-overreach --output-dir .pytest_tmp\f023-live-case-c --timeout-ms 240000
```

Expected artifacts:

- `.pytest_tmp/f023-live-case-c/case-c-answer.json`
- `.pytest_tmp/f023-live-case-c/results.json`
- `.pytest_tmp/f023-live-case-c/summary.md`

Historical result before review hardening: Session `Rvfj349mtMfZzvqTw8QpC8`, `question_delivery=chat_ui`, `report_delivery=""`, `citation_count=0`, `quality_reports.case_c.passed=true`, `semantic_finding_codes=["insufficient_evidence_should_refuse"]`, ActivityPanel steps included `Deterministic evidence audit completed` and `LLM semantic auditor unavailable; deterministic audit used`.

Current interpretation: blocked for F023 live acceptance. The same artifact must fail after F023.2 because it has `semantic_auditor.mode=llm_failed`, `llm_auditor_status=PermissionDeniedError`, no claim `llm_support_status`, no `llm_rationale`, and no `llm_*` finding code.

Review-hardened live UI Case C command:

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python ScienceClaw\backend\scripts\research_ui_e2e.py --frontend-url http://127.0.0.1:5180 --api-base-url http://127.0.0.1:5180/api/v1 --paper-path "E:\Self-Project\Research-Assistant\paper_data\Space-Time_Beamforming_for_LEO_Satellite_Communications_Enabling_Extremely_Narrow_Beams(1).pdf" --question "Do these LEO beamforming papers prove clinical safety outcomes for medical patients?" --semantic-overreach --output-dir .pytest_tmp\f023-live-case-c-review --timeout-ms 240000
```

Result: Expected failure. Session `TqpgG3XRngC6H3AqUGzHui`, `quality_reports.case_c.passed=false`, `semantic_auditor_mode=llm_failed`, `semantic_auditor_status=PermissionDeniedError`. Findings: `llm_semantic_auditor_mode_invalid`, `llm_semantic_audit_status_missing`, `llm_semantic_audit_rationale_missing`.

Accepted `qwen3.7-plus` live UI Case C command:

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python ScienceClaw\backend\scripts\research_ui_e2e.py --frontend-url http://127.0.0.1:5180 --api-base-url http://127.0.0.1:5180/api/v1 --paper-path "E:\Self-Project\Research-Assistant\paper_data\Space-Time_Beamforming_for_LEO_Satellite_Communications_Enabling_Extremely_Narrow_Beams(1).pdf" --question "Do these LEO beamforming papers prove clinical safety outcomes for medical patients?" --semantic-overreach --output-dir .pytest_tmp\f023-live-case-c-qwen37 --timeout-ms 240000
```

Result: Pass. Session `FjQPSdT36Q4CE5AauEQmEd`, `question_delivery=chat_ui`, `citation_count=0`, `quality_reports.case_c.passed=true`, `semantic_auditor.mode=llm_enhanced`, `semantic_auditor.model=qwen3.7-plus`, `llm_auditor_status=completed`, `llm_support_status=insufficient_evidence`, `finding_code=llm_insufficient_evidence`. ActivityPanel steps included `Research document uploaded`, `Parsing research document`, `Indexing paper evidence`, `Deterministic evidence audit completed`, and `LLM semantic auditor completed`.

## Results

Pass; F023 live LLM acceptance evidence captured.

- LLM-enhanced overlay behavior passed through injected auditor unit tests and deterministic payload golden fixtures.
- Live UI Case C reached the real browser UI upload and Chat textarea submission path.
- Historical live model calls returned `PermissionDeniedError`, so those older artifacts prove safe degradation only. They do not prove live `llm_enhanced` auditor judgment.
- F023.2 corrected the live Case C assertion so fallback cannot pass the main LLM auditor acceptance path.
- F023.3 normalized non-`llm_*` auditor finding codes at the LLM overlay boundary and accepted `.pytest_tmp/f023-live-case-c-qwen37` as the live F023 completion artifact.

## Artifacts

- `.pytest_tmp/f023-focused`
- `.pytest_tmp/f023-golden/results.json`
- `.pytest_tmp/f023-golden/summary.md`
- `.pytest_tmp/f023-golden/cases/leo_llm_overreach_payload_001.answer.json`
- `.pytest_tmp/f023-golden/cases/leo_llm_unsupported_payload_001.answer.json`
- `.pytest_tmp/f023-live-case-c/case-c-answer.json`
- `.pytest_tmp/f023-live-case-c/results.json`
- `.pytest_tmp/f023-live-case-c/summary.md`
- `.pytest_tmp/f023-review-ui-script`
- `.pytest_tmp/f023-live-case-c-review/case-c-answer.json`
- `.pytest_tmp/f023-live-case-c-review/results.json`
- `.pytest_tmp/f023-live-case-c-review/summary.md`
- `.pytest_tmp/f023-live-case-c-qwen37/case-c-answer.json`
- `.pytest_tmp/f023-live-case-c-qwen37/results.json`
- `.pytest_tmp/f023-live-case-c-qwen37/summary.md`

## Notes

- LLM auditor input is bounded to claim text, cited evidence quote/snippet, source identity metadata, and deterministic audit result.
- Auditor rationale remains audit/process trace, not citation evidence.
- No new UI design system or landing page was introduced.
- No commit or push was performed.

## Limitations

- The LLM auditor integration is configurable and testable, but local live behavior depends on model configuration availability.
- Payload cases use deterministic fixtures for stable CI-style verification.
- Historical `.pytest_tmp/f023-live-case-c` and `.pytest_tmp/f023-live-case-c-review` artifacts remain fallback/blocked evidence because their runtime model returned `PermissionDeniedError`.
- The accepted `.pytest_tmp/f023-live-case-c-qwen37` artifact proves live `llm_enhanced` behavior for the Case C clinical-safety overreach/refusal path; broader entailment calibration remains future work.
