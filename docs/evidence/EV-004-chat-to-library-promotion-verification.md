---
id: EV-004
doc_kind: evidence
scope: project
feature_refs:
  - docs/features/F012-chat-to-library-promotion.md
created: 2026-06-28
---

# EV-004: Chat To Library Promotion Verification

## Supports Claim

This Evidence supports F012 completion: Chat-uploaded papers stay temporary unless the user explicitly promotes them, promotion requires a Research Project, the backend reuses the Library ingestion/indexing path, and the frontend exposes one "Add to Research Library" action.

## Verification Scope

Covered:

- Backend promotion route request and behavior.
- Session workspace boundary check for temporary paper paths.
- Reuse of Library workspace, `research-library-{project_id}` session id, and Project-scoped indexing.
- Frontend API contract and ChatMessage/ChatPage promotion wiring.
- Frontend type safety.

Not covered:

- Browser screenshot verification of the button.
- Multi-paper candidate selection in one Chat turn.
- A pre-promotion quality review workflow.

## Checks

```text
$env:PYTHONPATH='ScienceClaw'; $env:TMP=(Resolve-Path .pytest-tmp); $env:TEMP=$env:TMP; pytest ScienceClaw/backend/tests/test_research_session_routes.py -k "promote_chat_paper_to_library"

pytest ScienceClaw/backend/tests/test_research_frontend_contracts.py -k "chat_to_library_promotion"

npm.cmd run type-check

npm.cmd run build

python C:\Users\HUAWEI\.codex\skills\using-agentmentor\scripts\knowledge_check.py --root E:\Self-Project\Research-Assistant --docs-path docs --feature-index docs\features\F012-chat-to-library-promotion.md

python C:\Users\HUAWEI\.codex\skills\using-agentmentor\scripts\knowledge_check.py --root E:\Self-Project\Research-Assistant --docs-path docs --strict
```

## Results

Pass.

- Backend focused route tests: 2 passed, 95 warnings.
- Frontend contract test: 1 passed.
- Full backend tests: 163 passed, 2210 warnings.
- Frontend type-check: passed.
- Frontend build: passed with existing Browserslist, CSS minify, and chunk-size warnings.
- AgentMentor F012 feature-index check: passed.
- AgentMentor strict knowledge check: passed.

## Artifacts

- Feature: `docs/features/F012-chat-to-library-promotion.md`
- Plan: `docs/superpowers/plans/2026-06-28-chat-to-library-promotion.md`
- Backend:
  - `ScienceClaw/backend/route/sessions.py`
  - `ScienceClaw/backend/tests/test_research_session_routes.py`
- Frontend:
  - `ScienceClaw/frontend/src/api/agent.ts`
  - `ScienceClaw/frontend/src/components/ChatMessage.vue`
  - `ScienceClaw/frontend/src/pages/ChatPage.vue`
  - `ScienceClaw/frontend/src/types/message.ts`
  - `ScienceClaw/backend/tests/test_research_frontend_contracts.py`

## Limitations

The first UI slice treats the latest eligible temporary research upload as the promotion candidate for the current answer. This is acceptable for the MVP path where the user uploads one paper and asks a question, but future multi-paper turns should attach promotion candidates per answer or per uploaded paper card.

## Notes

F012 preserves the product boundary discussed with the user: Chat is the place to inspect a paper, while Research Library is the trusted asset store. Promotion is explicit and singular.
