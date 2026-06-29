---
id: EV-007
doc_kind: evidence
scope: project
feature_refs:
  - docs/features/F010-project-scoped-chat.md
  - docs/features/F016-hierarchical-whole-paper-summary.md
created: 2026-06-30
updated: 2026-06-30
---

# EV-007: Live UI Research Workflow Verification

## Supports Claim

This Evidence supports the 2026-06-30 patches to F010 and F016: the running UI can create and use a Project-backed research workflow, Project-bound follow-up research prompts route through Research Answer, and whole-paper summary output uses Project citation evidence with Chinese structure labels and bounded extractive excerpts.

## Verification Scope

Covered:

- Research Library page loads without the Chat session drawer.
- A Project can be created in the running UI.
- A real PDF can be indexed into the Project through the authenticated backend upload API and then observed in the live Research Library UI.
- Chat session `mMKV5kKCEEcPKbxYQeUH7k` can bind to Project `research-project-NctWA3A5DdfjzNY9YEnRtw`.
- Project-bound whole-paper summary prompts reach `/research/answer` instead of generic `/chat`.
- ActivityPanel shows real trace events for citation evidence preparation.
- The latest Research Answer metadata reports Project-scoped citation evidence.
- Backend tests, frontend type-check, frontend build, and AgentMentor document validation run after the patches.

Not covered:

- Native browser file chooser automation; the browser control surface did not expose file upload APIs, so the real file upload used the same authenticated backend endpoint and was verified through the UI.
- LLM-authored section summaries; F016 remains deterministic extractive compression.
- Multi-paper synthesis or multi-agent workflow.
- Fixing weak fallback PDF metadata extraction for the observed title `9500`.

## Commands

```text
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; $env:TMP='E:\Self-Project\Research-Assistant\.pytest_tmp'; $env:TEMP='E:\Self-Project\Research-Assistant\.pytest_tmp'; pytest ScienceClaw/backend/tests/test_research_answering.py ScienceClaw/backend/tests/test_research_frontend_contracts.py -q --basetemp=.pytest_tmp\live-ui-routing

cd E:\Self-Project\Research-Assistant\ScienceClaw\frontend
npm.cmd run type-check
npm.cmd run build

$env:PYTHONPATH='E:\Self-Project\Research-Assistant;E:\Self-Project\Research-Assistant\ScienceClaw'; $env:TMP='E:\Self-Project\Research-Assistant\.pytest_tmp'; $env:TEMP='E:\Self-Project\Research-Assistant\.pytest_tmp'; pytest ScienceClaw/backend/tests -q --basetemp=.pytest_tmp\live-ui-full-final

python C:\Users\HUAWEI\.codex\skills\using-agentmentor\scripts\knowledge_check.py --root E:\Self-Project\Research-Assistant --docs-path docs --strict --feature-index F010-project-scoped-chat --feature-index F016-hierarchical-whole-paper-summary
```

## Checks

- `test_whole_paper_summary_uses_chinese_structure_for_chinese_questions` verifies Chinese whole-paper summary prompts use Chinese hierarchy labels.
- `test_whole_paper_summary_bounds_long_section_quotes` verifies long section evidence is bounded in answer text while original citation quotes are preserved.
- `test_project_bound_chat_routes_research_questions_without_mode_toggle` verifies the Chat frontend routes Project-bound non-chitchat prompts through Research Answer without relying on a visible mode toggle.
- Live UI verification checked the Research Library, Project binding, Chat answer, ActivityPanel trace, and latest assistant metadata.

## Results

Pass.

- Focused answering/frontend contract tests: 58 passed.
- Frontend type-check: passed.
- Frontend production build: passed with pre-existing Browserslist/CSS/chunk-size warnings.
- Full backend suite: 192 passed, 2304 warnings.
- Live backend log for the final UI prompt: `POST /api/v1/sessions/mMKV5kKCEEcPKbxYQeUH7k/research/answer`.
- Latest assistant metadata: `citation_count=15`, first citation `evidence_scope=project`.
- Latest assistant content: Chinese hierarchy label present, English hierarchy label absent, bounded excerpts present.
- AgentMentor validation: `knowledge_check.py --root E:\Self-Project\Research-Assistant --docs-path docs --strict --feature-index F010-project-scoped-chat --feature-index F016-hierarchical-whole-paper-summary` passed after Evidence and Feature docs were updated.

## Artifacts

- Feature docs:
  - `docs/features/F010-project-scoped-chat.md`
  - `docs/features/F016-hierarchical-whole-paper-summary.md`
- Evidence:
  - `docs/evidence/EV-007-live-ui-research-workflow-verification.md`
- Backend:
  - `ScienceClaw/backend/research_assistant/answering.py`
- Frontend:
  - `ScienceClaw/frontend/src/pages/ChatPage.vue`
- Tests:
  - `ScienceClaw/backend/tests/test_research_answering.py`
  - `ScienceClaw/backend/tests/test_research_frontend_contracts.py`

## Limitations

The current whole-paper summary is bounded deterministic extraction, not a full LLM map-reduce synthesis. It is suitable for the current F016 boundary because citations remain original evidence records and the behavior is testable, but later work can add an auditable LLM section-summary stage.

## Notes

Project binding is the durable research context boundary. The UI should not require users to remember a technical Research/General mode switch before a Project-scoped research question can use Project evidence.
