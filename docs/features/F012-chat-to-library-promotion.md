---
id: F012
doc_kind: feature
status: completed
owner: solitudeTG
created: 2026-06-28
updated: 2026-06-29
---

# F012: Chat To Library Promotion

## Goal

Keep ordinary Chat PDF uploads temporary by default, and add one explicit "Add to Research Library" action that promotes an eligible uploaded paper into a selected Research Project.

## Vision Anchor

- Original request or source: The user confirmed that uploading a paper in Chat for quick understanding is reasonable, but arbitrary uploads must not automatically become trusted RAG assets.
- User pain point or engineering problem: Auto-ingesting every temporary paper would pollute the trusted Research Library and blur evidence boundaries.
- Expected outcome: After a research answer over a temporary uploaded PDF, the UI can show one explicit "Add to Research Library" action. Promotion requires a linked Project and reuses the Library ingestion/indexing path.
- Non-goals or boundaries: Do not auto-promote uploads, do not add multiple first-version actions, do not build a quality review workflow, and do not alter F009/F010 boundaries.
- Exit Gate source: This Feature, F009 Library ingestion, F003 ingestion, F008 trace honesty, backend route tests, and frontend contract/type checks.

## Feature Intake

- Original problem: Temporary Chat file understanding and trusted Research Library ingestion need a user-confirmed boundary.
- User pain point: Users want to inspect a paper first, then decide whether it is valuable enough to become trusted RAG material.
- Capability promise: Provide one clear promotion action from Chat to Library.
- Non-goals: Do not auto-promote uploads or expose multiple competing actions in the first version.
- Acceptance source: User-approved Chat upload boundary discussion on 2026-06-28.
- Open questions: Future quality review workflow before promotion is deferred.

## Capability Contract

- Chat-uploaded papers remain temporary unless promoted.
- The only first-version promotion action is "Add to Research Library".
- Promotion requires a target Research Project.
- Promoted files reuse the Library ingestion/indexing path.
- Activity/trace reflects real promotion/indexing events only.

## Current Status

Completed for MVP scope. Chat-uploaded papers remain temporary by default, and eligible answers can expose one explicit "Add to Research Library" action that promotes the temporary file into the currently linked Research Project through the Library ingestion/indexing path.

## Decision Context

### Why

Temporary file understanding is useful for quick inspection, but trusted RAG assets require explicit user confirmation and Project ownership.

### Why Not

Automatic promotion was rejected because arbitrary Chat uploads would pollute trusted research context. Multiple first-version actions were rejected because the intended user decision is singular: add this paper to the research library or leave it temporary.

### If Modifying This Area, Check

- F009 for Library ingestion and Project target selection.
- F003 for document ingestion.
- F008 for real promotion/indexing trace.
- F010 for Chat Project binding.

## Links

### Evidence

- [EV-004 Chat To Library Promotion Verification](../evidence/EV-004-chat-to-library-promotion-verification.md)

### Decisions / ADRs

- [ADR-001 P0 Research Data and Retrieval Stack](../decisions/ADR-001-p0-research-data-and-retrieval-stack.md)

### Lessons

- None yet.

### Specs / Plans

- [F001 Feature Map and Rules Spec](../specs/F001-feature-map-and-rules-spec.md)
- [Chat To Library Promotion Implementation Plan](../superpowers/plans/2026-06-28-chat-to-library-promotion.md)

### Related Features

- [F003 Research Document Ingestion](F003-research-document-ingestion.md)
- [F008 Trace Honesty and Activity Panel](F008-trace-honesty-activity-panel.md)
- [F009 Research Project Library Core](F009-research-project-library-core.md)
- [F010 Project Scoped Chat](F010-project-scoped-chat.md)

### External Context

- None.

## Acceptance Criteria

- [x] Temporary Chat upload does not automatically create Library paper assets.
- [x] Chat answer can show one "Add to Research Library" action for eligible uploaded papers.
- [x] User can choose a Project for promotion.
- [x] Promotion writes and indexes through the Library path.
- [x] Trace shows real promotion/indexing status.

## Acceptance Map

| Claim | Acceptance | Evidence | Status |
| --- | --- | --- | --- |
| Chat uploads remain temporary by default. | Promotion requires a separate `/research/library/promote` call and source file must remain in the session workspace. | `pytest ScienceClaw/backend/tests/test_research_session_routes.py -k "promote_chat_paper_to_library"`. | Passed |
| Promotion is explicit. | Eligible answers expose only one "Add to Research Library" action and emit one promotion event. | `pytest ScienceClaw/backend/tests/test_research_frontend_contracts.py -k "chat_to_library_promotion"`. | Passed |
| Promotion uses Library ingestion. | Confirmed action writes/indexes into a selected Project with `project_id`. | `pytest ScienceClaw/backend/tests/test_research_session_routes.py -k "promote_chat_paper_to_library"`. | Passed |

## State Timeline

| Date | State | Trigger | Evidence | Note |
| --- | --- | --- | --- | --- |
| 2026-06-28 | planned | User approved four-Feature breakdown | This Feature | Created to own temporary-to-trusted asset promotion. |
| 2026-06-28 | completed | F012 implementation and verification | EV-004 | MVP Chat-to-Library promotion landed. |
| 2026-06-29 | patched | Combined E2E review found Chat promotion controls still used English copy and needed live Library result verification | Frontend contract/type checks, API promotion E2E, Library UI/API verification | F012.1 localizes the one promotion action and verifies promoted papers update the target Library Project. |
| 2026-06-29 | patched | User clarified that unbound Chat sessions must not expose the trusted-library promotion action | Frontend contract test, type-check, build | F012.2 gates the `加入研究库` action on an explicitly linked Research Project, so temporary uploads in unbound sessions stay temporary without a misleading Library action. |

## Patch History

| Patch | Date | Commit | Symptom | Root Cause | Protection | Status |
| --- | --- | --- | --- | --- | --- | --- |
| F012.1 | 2026-06-29 | `515bd25` | The explicit Chat promotion action still displayed `Add to Research Library`, inconsistent with the requested Chinese ScienceClaw-style UI. | The first MVP left the promotion button copy hard-coded in English. | Frontend contract test rejects English promotion copy and requires `加入研究库`; live API promotion of a real `paper_data` PDF updated the target Project to `2` papers and `39` evidence records. | verified |

| F012.2 | 2026-06-29 | pending | Unbound Chat sessions could infer a promotion candidate from uploaded-paper metadata and show `加入研究库`, even though there was no selected Research Project boundary. | `ChatMessage` reconstructed promotion candidates from message metadata without knowing whether the parent Chat session had a linked Project. | Added a frontend contract requiring `canPromoteToResearchLibrary`, passed from `ChatPage` as `!!currentResearchProject`; focused contract, full frontend contract suite, type-check, and build passed. | verified |

## Evidence

- `pytest ScienceClaw/backend/tests/test_research_session_routes.py -k "promote_chat_paper_to_library"`: 2 passed.
- `pytest ScienceClaw/backend/tests/test_research_frontend_contracts.py -k "chat_to_library_promotion"`: 1 passed.
- `npm.cmd run type-check` from `ScienceClaw/frontend`: passed.
- 2026-06-29 patch verification: `pytest ScienceClaw/backend/tests/test_research_frontend_contracts.py -k "chinese_user_facing_copy" -q` -> passed; real promotion API returned `promotion_status=indexed`, `parser=grobid-tei`, `chunk_count=24`, `evidence_record_count=24`; Library project summary became `2` papers and `39` evidence records.
- 2026-06-29 project-boundary patch verification: `pytest ScienceClaw/backend/tests/test_research_frontend_contracts.py -k "promotion_requires_bound" -q` -> `1 passed, 37 deselected`; `pytest ScienceClaw/backend/tests/test_research_frontend_contracts.py -q` -> `38 passed`; `npm.cmd run type-check` from `ScienceClaw/frontend` -> passed; `npm.cmd run build` from `ScienceClaw/frontend` -> passed.

## Recovery Snapshot

- Read first: this Feature, F009, F003, F008, F010.
- Current capability state: Chat can read uploaded PDFs temporarily, then promote an eligible uploaded paper into the linked Research Project through one explicit action.
- Known risks: The UI candidate is scoped to the latest eligible temporary upload; future multi-paper turns need a more precise per-answer candidate selector.
- Next safe action: Run final verification, commit, and push F012.

## Next Step

Run final verification, commit, and push F012.
