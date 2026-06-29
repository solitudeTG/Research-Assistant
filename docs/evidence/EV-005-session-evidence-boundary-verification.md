---
id: EV-005
doc_kind: evidence
scope: project
feature_refs:
  - docs/features/F015-session-evidence-boundary.md
created: 2026-06-29
---

# EV-005: Session Evidence Boundary Verification

## Supports Claim

This Evidence supports F015 completion: Chat-uploaded papers remain session-scoped temporary evidence, Research Library uploads and explicit promotion create project-scoped trusted evidence, citations expose their evidence scope, and the UI reflects the boundary without introducing a mode toggle.

## Verification Scope

Covered:

- Scoped paper IDs for the same document across session and Project contexts.
- Session upload metadata: `evidence_scope=session`, `temporary=true`, and no Project ownership.
- Research Library upload and Chat promotion metadata: `evidence_scope=project`, `temporary=false`, and Project namespace.
- Project-bound retrieval includes both current-session temporary evidence and current Project evidence.
- Whole-paper summary evidence carries scope metadata.
- Frontend contracts for citation scope display, temporary upload labels, duplicate/error details, and promotion eligibility.
- Frontend type-check and production build.
- AgentMentor Feature Index and strict knowledge validation.

Not covered:

- Browser screenshot verification after service restart.
- Strong content-fingerprint duplicate detection for same paper under different filenames.
- Multi-paper synthesis or LLM Router behavior.

## Commands

```text
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; $env:TMP='E:\Self-Project\Research-Assistant\.pytest_tmp'; $env:TEMP='E:\Self-Project\Research-Assistant\.pytest_tmp'; pytest ScienceClaw/backend/tests/test_research_ingestion.py ScienceClaw/backend/tests/test_research_retrieval.py ScienceClaw/backend/tests/test_research_answering.py ScienceClaw/backend/tests/test_research_database.py ScienceClaw/backend/tests/test_research_session_routes.py ScienceClaw/backend/tests/test_research_frontend_contracts.py -q --basetemp=.pytest_tmp\f015-focused

$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw;E:\Self-Project\Research-Assistant'; $env:TMP='E:\Self-Project\Research-Assistant\.pytest_tmp'; $env:TEMP='E:\Self-Project\Research-Assistant\.pytest_tmp'; pytest ScienceClaw/backend/tests -q --basetemp=.pytest_tmp\f015-full

npm.cmd run type-check

npm.cmd run build

python C:\Users\HUAWEI\.codex\skills\using-agentmentor\scripts\knowledge_check.py --root E:\Self-Project\Research-Assistant --docs-path docs --feature-index F015-session-evidence-boundary

python C:\Users\HUAWEI\.codex\skills\using-agentmentor\scripts\knowledge_check.py --root E:\Self-Project\Research-Assistant --docs-path docs --strict
```

## Checks

- Ingestion creates different paper IDs for the same file when the namespace is `session:<session_id>` versus `project:<project_id>`.
- Hybrid retrieval SQL keeps current session evidence available when a Project is bound.
- Answer citations serialize `evidence_scope`.
- Session upload, Library upload, and promotion routes expose scope metadata and use the correct namespace.
- ActivityPanel displays scope labels for citation evidence.
- Chat upload cards show temporary material labels and backend error details.
- ChatMessage only exposes “加入研究库” for eligible temporary session evidence and hides already-promoted paths.

## Results

Pass.

- Focused backend/frontend contract suite: 123 passed, 2257 warnings.
- Full backend suite: 188 passed, 2304 warnings.
- Frontend type-check: passed.
- Frontend build: passed with existing Browserslist, CSS minify, and chunk-size warnings.
- AgentMentor F015 feature-index check: passed.
- AgentMentor strict knowledge check: passed.

## Artifacts

- Feature: `docs/features/F015-session-evidence-boundary.md`
- Backend:
  - `ScienceClaw/backend/research_assistant/ingestion.py`
  - `ScienceClaw/backend/research_assistant/retrieval.py`
  - `ScienceClaw/backend/research_assistant/answering.py`
  - `ScienceClaw/backend/research_assistant/storage/database.py`
  - `ScienceClaw/backend/research_assistant/storage/repository.py`
  - `ScienceClaw/backend/route/sessions.py`
- Frontend:
  - `ScienceClaw/frontend/src/components/ActivityPanel.vue`
  - `ScienceClaw/frontend/src/components/ChatBoxFiles.vue`
  - `ScienceClaw/frontend/src/components/ChatMessage.vue`
  - `ScienceClaw/frontend/src/pages/ChatPage.vue`
  - `ScienceClaw/frontend/src/api/agent.ts`
  - `ScienceClaw/frontend/src/api/file.ts`
  - `ScienceClaw/frontend/src/types/message.ts`
- Tests:
  - `ScienceClaw/backend/tests/test_research_ingestion.py`
  - `ScienceClaw/backend/tests/test_research_retrieval.py`
  - `ScienceClaw/backend/tests/test_research_answering.py`
  - `ScienceClaw/backend/tests/test_research_database.py`
  - `ScienceClaw/backend/tests/test_research_session_routes.py`
  - `ScienceClaw/backend/tests/test_research_frontend_contracts.py`

## Limitations

Duplicate handling is intentionally conservative in this slice. Same-name duplicates in a session or Library are rejected with a clear reason; same-content/different-filename detection remains future work because it requires a stronger document fingerprint contract and migration plan.

## Notes

F015 preserves the product insight from ChatGPT/Gemini/Notebook-style workflows: temporary file processing is useful for current-session work, but durable research knowledge must be explicit, Project-owned, and auditable.
