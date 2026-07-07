---
id: EV-023
doc_kind: evidence
scope: project
feature_refs:
  - docs/features/F022-semantic-evidence-audit-and-multi-paper-synthesis.md
  - docs/features/F006-evidence-audit.md
  - docs/features/F019-research-quality-evaluation-harness.md
created: 2026-07-07
updated: 2026-07-07
---

# EV-023: Semantic Audit Multi-paper Verification

## Supports Claim

F022 增强 Research Assistant 的可信研究闭环：answer payload 现在包含 claim-level semantic audit 字段和稳定 finding code；multi-paper synthesis 可以要求至少两篇不同 paper citation；insufficient evidence case 会拒绝无证据临床安全结论；golden eval payload 和 live UI E2E runner 能保存可复现 artifacts。

## Verification Scope

已覆盖：

- Semantic audit unit tests。
- Multi-paper synthesis/refusal focused answering tests。
- Research evaluation semantic field gate。
- Golden eval semantic threshold tests。
- Payload golden eval CLI，覆盖 8 个 deterministic payload cases。
- Live UI E2E script contract tests。

已实跑：

- Live UI E2E Case A: 上传 2 篇真实 PDF 后进行 multi-paper synthesis positive。
- Live UI E2E Case B: 同一 session 提问 clinical safety outcomes 并验证 insufficient refusal。

## Case Set

Payload golden cases:

- `leo_space_time_evidence_qa_payload_001`: supported single-paper claim。
- `leo_partial_support_payload_001`: partial support claim，expected `semantic_support_partial`。
- `leo_semantic_mismatch_payload_001`: semantic mismatch claim，expected `semantic_support_mismatch`。
- `leo_context_only_rejection_payload_001`: context-only memory rejection，expected `context_only_source_used_as_citation`。
- `leo_multi_paper_synthesis_payload_001`: multi-paper positive，expected distinct cited papers >= 2。
- `leo_insufficient_evidence_payload_001`: insufficient evidence refusal，expected zero citations and `insufficient_evidence_should_refuse`。
- Existing whole-paper/evidence QA cases remain as regression coverage.

Live UI Case A question:

```text
Compare how these two papers frame beamforming as a LEO satellite research problem. Use evidence from both papers and call out limitations.
```

Live UI Case B question:

```text
Do these papers prove clinical safety outcomes for medical patients? Provide citations.
```

## Checks

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python -m pytest ScienceClaw\backend\tests\test_research_audit.py::test_semantic_audit_claims_expose_support_status_scores_evidence_and_finding_codes ScienceClaw\backend\tests\test_research_audit.py::test_semantic_audit_marks_no_citation_answer_as_insufficient_evidence_refusal -q
```

Result: Pass, `2 passed, 1 warning`.

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python -m pytest ScienceClaw\backend\tests\test_research_answering.py::test_answer_research_question_formats_multi_paper_synthesis_when_two_papers_are_admitted ScienceClaw\backend\tests\test_research_answering.py::test_answer_research_question_refuses_clinical_safety_claim_when_admitted_papers_lack_domain_evidence -q
```

Result: Pass, `2 passed, 1 warning`.

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python -m pytest ScienceClaw\backend\tests\test_research_evaluation.py -q --basetemp .pytest_tmp\semantic-eval
```

Result: Pass, `6 passed`.

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python -m pytest ScienceClaw\backend\tests\test_research_golden_eval.py -q --basetemp .pytest_tmp\semantic-golden-suite
```

Result: Pass, `12 passed, 1 warning`.

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python ScienceClaw\backend\scripts\research_golden_eval.py --cases docs\evals\research_golden_cases.json --payload-dir docs\evals\payloads --output-dir .pytest_tmp\semantic-multipaper-golden
```

Result: Pass, `cases=8 passed=8 failed=0`.

Review hardening focused suite:

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python -m pytest ScienceClaw\backend\tests -k "research_audit or research_answering or research_evaluation or research_golden_eval or retrieval or synthesis or research_ui_e2e_script" -q --basetemp .pytest_tmp\semantic-focused-suite-review-final
```

Result: Pass, `70 passed, 211 deselected, 213 warnings`.

Review hardening rerun:

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python ScienceClaw\backend\scripts\research_golden_eval.py --cases docs\evals\research_golden_cases.json --payload-dir docs\evals\payloads --output-dir .pytest_tmp\semantic-multipaper-golden-review
```

Result: Pass, `cases=8 passed=8 failed=0`.

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python -m pytest ScienceClaw\backend\tests\test_research_ui_e2e_script.py -q --basetemp .pytest_tmp\semantic-ui-script-suite
```

Result: Pass, `4 passed, 1 warning`.

```powershell
python C:\Users\HUAWEI\.codex\skills\using-agentmentor\scripts\knowledge_check.py --root E:\Self-Project\Research-Assistant --docs-path docs --strict
```

Result: Pass, `Errors: 0`, `Warnings: 0`.

```powershell
python C:\Users\HUAWEI\.codex\skills\using-agentmentor\scripts\knowledge_check.py --root E:\Self-Project\Research-Assistant --docs-path docs --feature-index docs\features\F022-semantic-evidence-audit-and-multi-paper-synthesis.md
```

Result: Pass, `Errors: 0`, `Warnings: 0`.

Planned live UI E2E command:

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python ScienceClaw\backend\scripts\research_ui_e2e.py --frontend-url http://127.0.0.1:5173 --api-base-url http://127.0.0.1:12001/api/v1 --paper-path "E:\Self-Project\Research-Assistant\paper_data\Space-Time_Beamforming_for_LEO_Satellite_Communications_Enabling_Extremely_Narrow_Beams(1).pdf" --paper-path "E:\Self-Project\Research-Assistant\paper_data\Beamforming_Design_and_Satellite_Selection_for_Realizing_the_Integrated_Communication_and_Navigation_in_LEO_Satellite_Networks.pdf" --question "Compare how these two papers frame beamforming as a LEO satellite research problem. Use evidence from both papers and call out limitations." --insufficient-question "Do these papers prove clinical safety outcomes for medical patients? Provide citations." --semantic-multipaper --output-dir .pytest_tmp\semantic-multipaper-live-ui
```

Result: Superseded by the actual live UI command below, which uses the Vite proxy API URL required by this local frontend setup.

Actual live UI E2E command:

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python ScienceClaw\backend\scripts\research_ui_e2e.py --frontend-url http://127.0.0.1:5180 --api-base-url http://127.0.0.1:5180/api/v1 --paper-path "E:\Self-Project\Research-Assistant\paper_data\Space-Time_Beamforming_for_LEO_Satellite_Communications_Enabling_Extremely_Narrow_Beams(1).pdf" --paper-path "E:\Self-Project\Research-Assistant\paper_data\Beamforming_Design_and_Satellite_Selection_for_Realizing_the_Integrated_Communication_and_Navigation_in_LEO_Satellite_Networks.pdf" --question "Compare how these two papers frame beamforming as a LEO satellite research problem. Use evidence from both papers and call out limitations." --insufficient-question "Do these papers prove clinical safety outcomes for medical patients? Provide citations." --semantic-multipaper --output-dir .pytest_tmp\semantic-multipaper-live-ui --timeout-ms 240000
```

Review hardening live UI E2E command:

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python ScienceClaw\backend\scripts\research_ui_e2e.py --frontend-url http://127.0.0.1:5180 --api-base-url http://127.0.0.1:5180/api/v1 --paper-path "E:\Self-Project\Research-Assistant\paper_data\Space-Time_Beamforming_for_LEO_Satellite_Communications_Enabling_Extremely_Narrow_Beams(1).pdf" --paper-path "E:\Self-Project\Research-Assistant\paper_data\Beamforming_Design_and_Satellite_Selection_for_Realizing_the_Integrated_Communication_and_Navigation_in_LEO_Satellite_Networks.pdf" --question "Compare how these two papers frame beamforming as a LEO satellite research problem. Use evidence from both papers and call out limitations." --insufficient-question "Do these papers prove clinical safety outcomes for medical patients? Provide citations." --semantic-multipaper --output-dir .pytest_tmp\semantic-multipaper-live-ui-review --timeout-ms 240000
```

Result: Pass. Session `GffNBgsB32ConTFwV77KgK`, `question_delivery=chat_ui`, `report_delivery=chat_ui`, `insufficient_question_delivery=chat_ui`, `citation_count=5`, `activity_steps=16`, no error events. Case A quality gate passed with `claim_count=6`, `partial_claim_count=4`, `unsupported_claim_count=2`, `unsupported_claim_ratio=0.3333`; Case B quality gate passed with `evidence_admission.decision=insufficient` and `citation_count=0`.

## Results

Pass.

- Case A: 2 real PDFs uploaded through the browser UI; the question was submitted through the Chat textarea; the Markdown report was generated by clicking the report action in the assistant message; answer payload returned 5 citations from 2 distinct paper IDs; citations were `source_type=paper`; audit claims included `support_status`, semantic relevance, source quality, cited evidence, and partial/unsupported distinctions.
- Case B: clinical safety question returned `evidence_admission.decision=insufficient`, `citation_count=0`, and audit finding `insufficient_evidence_should_refuse`.
- Activity/trace evidence included upload, parsing, indexing, Reader Worker summary, Auditor Agent boundary review, citation retrieval, and Markdown artifact generation.

## Artifacts

- `.pytest_tmp/semantic-multipaper-golden/results.json`
- `.pytest_tmp/semantic-multipaper-golden/summary.md`
- `.pytest_tmp/semantic-multipaper-golden/cases/`
- `.pytest_tmp/semantic-multipaper-live-ui/results.json`
- `.pytest_tmp/semantic-multipaper-live-ui/summary.md`
- `.pytest_tmp/semantic-multipaper-live-ui/case-a-answer.json`
- `.pytest_tmp/semantic-multipaper-live-ui/case-a-report.json`
- `.pytest_tmp/semantic-multipaper-live-ui/case-b-insufficient-answer.json`
- `.pytest_tmp/semantic-multipaper-golden-review/results.json`
- `.pytest_tmp/semantic-multipaper-golden-review/summary.md`
- `.pytest_tmp/semantic-multipaper-live-ui-review/results.json`
- `.pytest_tmp/semantic-multipaper-live-ui-review/summary.md`
- `.pytest_tmp/semantic-multipaper-live-ui-review/case-a-answer.json`
- `.pytest_tmp/semantic-multipaper-live-ui-review/case-a-report.json`
- `.pytest_tmp/semantic-multipaper-live-ui-review/case-b-insufficient-answer.json`

## Notes

- `paper_data/` currently contains the two required real PDFs for live Case A.
- The review-hardened live script uses the ScienceClaw browser shell and UI file input for upload, submits Case A/B questions through the Chat textarea, waits for the Chat-triggered `/research/answer` response, and clicks the assistant-message report action for `/research/report`.
- The local frontend used `http://127.0.0.1:5180` because Docker-owned `5173` returned 404 for direct history routes in this environment; API calls went through the Vite proxy at `http://127.0.0.1:5180/api/v1`.
- Semantic scoring is heuristic. It is a trustworthy engineering quality gate, not a peer-review-grade entailment model.

## Limitations

- The live run's session status field was `unknown`; the E2E pass is based on concrete answer/report/trace artifacts rather than that status flag.
- No external web/database acquisition is added.
- No PDF/DOCX exporter is added.
- No new UI design system or landing page is introduced.
