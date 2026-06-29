---
id: EV-006
doc_kind: evidence
scope: project
feature_refs:
  - docs/features/F016-hierarchical-whole-paper-summary.md
created: 2026-06-29
---

# EV-006: Hierarchical Whole Paper Summary Verification

## Supports Claim

This Evidence supports F016 completion: whole-paper summary now uses section-balanced paper evidence collection, renders section summaries before global synthesis, and keeps all citations anchored to original paper evidence records rather than generated intermediate summaries.

## Verification Scope

Covered:

- Whole-paper summary route still avoids ordinary top-k hybrid search.
- Whole-paper summary output includes section summaries and global synthesis.
- Dense repeated evidence from one section is bounded so other available sections remain visible.
- Database whole-paper evidence sweep uses section partitioning and `per_section_limit`.
- Citation objects remain original paper `EvidenceHit` derived records.
- AgentMentor Feature Index and strict knowledge validation after F016 documents changed.

Not covered:

- Live browser/UI verification after restarting services.
- LLM-authored section compression.
- Multi-paper synthesis or multi-agent workflow.
- Explicit user selection among multiple papers in the same Project.

## Commands

```text
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; $env:TMP='E:\Self-Project\Research-Assistant\.pytest_tmp'; $env:TEMP='E:\Self-Project\Research-Assistant\.pytest_tmp'; pytest ScienceClaw/backend/tests/test_research_answering.py ScienceClaw/backend/tests/test_research_database.py -q --basetemp=.pytest_tmp\f016-focused

$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; $env:TMP='E:\Self-Project\Research-Assistant\.pytest_tmp'; $env:TEMP='E:\Self-Project\Research-Assistant\.pytest_tmp'; pytest ScienceClaw/backend/tests/test_research_task_router.py ScienceClaw/backend/tests/test_research_session_routes.py -k "research_answer or whole_paper_summary" -q --basetemp=.pytest_tmp\f016-routes

python -m py_compile ScienceClaw/backend/research_assistant/answering.py ScienceClaw/backend/research_assistant/storage/database.py

$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw;E:\Self-Project\Research-Assistant'; $env:TMP='E:\Self-Project\Research-Assistant\.pytest_tmp'; $env:TEMP='E:\Self-Project\Research-Assistant\.pytest_tmp'; pytest ScienceClaw/backend/tests -q --basetemp=.pytest_tmp\f016-full

python C:\Users\HUAWEI\.codex\skills\using-agentmentor\scripts\knowledge_check.py --root E:\Self-Project\Research-Assistant --docs-path docs --feature-index F016-hierarchical-whole-paper-summary

python C:\Users\HUAWEI\.codex\skills\using-agentmentor\scripts\knowledge_check.py --root E:\Self-Project\Research-Assistant --docs-path docs --strict
```

## Checks

- `test_answer_research_question_routes_whole_paper_summary_to_full_paper_evidence` verifies the whole-paper route still avoids ordinary top-k hybrid search and now renders section summaries plus global synthesis.
- `test_whole_paper_summary_balances_dense_sections_before_global_synthesis` verifies dense Introduction evidence does not hide Method, Experiment, and Conclusion section summaries.
- `test_list_whole_paper_evidence_in_database_handles_json_source_identity` verifies the database sweep uses section partitioning and a `per_section_limit`.
- Full backend tests protect existing ingestion, retrieval, audit, report, session, and runtime behavior.

## Results

Pass.

- Focused answering/database tests: 29 passed.
- Route/session focused tests: 8 passed, 45 deselected.
- Python compile check: passed.
- Full backend suite: 189 passed, 2304 warnings.
- AgentMentor F016 feature-index check: passed.
- AgentMentor strict knowledge check: passed.

## Artifacts

- Feature: `docs/features/F016-hierarchical-whole-paper-summary.md`
- Evidence: `docs/evidence/EV-006-hierarchical-whole-paper-summary-verification.md`
- Backend:
  - `ScienceClaw/backend/research_assistant/answering.py`
  - `ScienceClaw/backend/research_assistant/storage/database.py`
- Tests:
  - `ScienceClaw/backend/tests/test_research_answering.py`
  - `ScienceClaw/backend/tests/test_research_database.py`

## Limitations

This is a deterministic hierarchy. It improves coverage and summary shape, but it is not yet LLM-authored section compression. A future slice can add model-based section summaries after Research Assistant has an explicit, auditable LLM answer-generation contract.

## Notes

Section summaries are context-only intermediate artifacts. Final citation evidence remains original paper evidence, consistent with F004 and F015.
