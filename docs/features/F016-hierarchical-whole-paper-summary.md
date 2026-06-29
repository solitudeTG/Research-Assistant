---
id: F016
doc_kind: feature
status: completed
owner: solitudeTG
created: 2026-06-29
updated: 2026-06-30
---

# F016: Hierarchical Whole Paper Summary

## Goal

Upgrade whole-paper summary from an extractive first slice into a section-summary to global-synthesis workflow for one paper at a time.

## Vision Anchor

- Source: User approved the next slice after F013 to replace extractive first-slice whole-paper summary with section summary -> global synthesis.
- User pain point: A long paper summary that only sees early or arbitrary chunks can miss experiments, limitations, and conclusions.
- Desired outcome: Whole-paper summary requests cover the available paper sections, produce section-level summaries first, and then synthesize a paper-level view.
- Non-goals: No multi-paper synthesis, no multi-agent workflow, no long-form report generation, no citation to generated summaries, and no LLM router expansion in this slice.
- Exit Gate source: This Feature, F013 task router, F004 citation evidence boundary, F015 session evidence boundary.

## Feature Intake

- Original problem: Whole-paper summary needs broad paper coverage, not a few retrieved chunks.
- User pain point: Users ask "summarize this paper" expecting full-paper understanding and evidence traceability.
- Capability promise: Use a hierarchical summarization shape: group accepted paper evidence by section, create bounded section summaries, then compose global synthesis from those section summaries.
- Non-goals: Do not cite section summaries as evidence; do not force every chunk into the model context; do not implement multi-paper comparison or research synthesis.
- Acceptance source: User request on 2026-06-29 after F015 completion.
- Open questions: Later slices can replace deterministic section compression with LLM section summarization when answer generation has a stable LLM contract.

## Capability Contract

- Whole-paper summary keeps using the F013 `whole_paper_summary` route.
- Evidence collection remains scoped by F015: current session evidence plus associated Project evidence when present.
- Section summaries are context-only intermediate artifacts derived from accepted paper evidence.
- Final citations remain original paper evidence records, never generated summaries.
- The answer content exposes a clear hierarchy: coverage basis, section summaries, and global synthesis.
- The workflow avoids letting one dense section consume the whole summary budget when other sections are available.

## Decision Context

### Why

Whole-paper summary is a compression problem over the paper's structure. Ordinary top-k retrieval answers local questions well, but a summary request needs broader section coverage and a bounded intermediate representation before synthesis.

### Why Not

This slice does not add LLM-authored section summaries yet because the current Research Assistant answer path is deterministic and testable. Adding LLM compression should come after the LLM answer-generation contract defines prompts, trace, cost boundaries, failure handling, and citation audit behavior.

### If Modifying This Area, Check

- F004 for citation evidence boundaries.
- F013 for task routing into `whole_paper_summary`.
- F015 for session versus Project evidence scope.
- EV-006 for the verification shape that protects section-balanced collection.

## Current Status

Completed for the first deterministic hierarchy slice. Whole-paper summary now uses a section-balanced evidence sweep, renders section summaries first, and composes a global synthesis from original paper evidence citations.

## Links

### Evidence

- [EV-006 F016 Hierarchical Whole Paper Summary Verification](../evidence/EV-006-hierarchical-whole-paper-summary-verification.md)
- [EV-007 Live UI Research Workflow Verification](../evidence/EV-007-live-ui-research-workflow-verification.md)

### Decisions / ADRs

- [ADR-001 P0 Research Data and Retrieval Stack](../decisions/ADR-001-p0-research-data-and-retrieval-stack.md)

### Lessons

- None yet.

### Specs / Plans

- None yet.

### Related Features

- [F004 Citation Evidence Boundary](F004-citation-evidence-boundary.md)
- [F013 Research Task Router and Whole Paper Summary](F013-research-task-router-whole-paper-summary.md)
- [F015 Session Evidence Boundary](F015-session-evidence-boundary.md)

### External Context

- Common long-document RAG patterns separate local semantic search from map-reduce or hierarchical summarization for document-level requests.

## Acceptance Criteria

- [x] Whole-paper summary output contains section summaries and a global synthesis.
- [x] Section coverage is balanced so repeated chunks from one section do not hide other available sections.
- [x] Citation evidence still points to original paper evidence records.
- [x] The whole-paper summary path remains separate from ordinary top-k hybrid search.
- [x] Verification evidence is recorded after focused tests and relevant build/type checks.

## Acceptance Map

| Claim | Acceptance | Evidence | Status |
| --- | --- | --- | --- |
| Whole-paper summary is hierarchical. | Output includes section summaries before global synthesis. | `test_answer_research_question_routes_whole_paper_summary_to_full_paper_evidence`. | Passed |
| Summary citations remain original paper evidence. | Returned citations are `ResearchCitation` objects from accepted `EvidenceHit` rows. | `test_whole_paper_summary_balances_dense_sections_before_global_synthesis`. | Passed |
| Dense sections do not crowd out coverage. | Repeated chunks per section are bounded before synthesis. | `test_list_whole_paper_evidence_in_database_handles_json_source_identity`; SQL partition contract. | Passed |

## State Timeline

| Date | State | Trigger | Evidence | Note |
| --- | --- | --- | --- | --- |
| 2026-06-29 | active | User approved F016 | This Feature | Created to own the hierarchical whole-paper summary slice. |
| 2026-06-29 | completed | F016 implementation verified | EV-006 | Section-balanced sweep and hierarchical composition landed. |
| 2026-06-30 | patched | Live UI verification found output quality issues | EV-007 | Chinese labels and bounded extractive summaries landed. |

## Patch History

| Patch | Date | Commit | Symptom | Root Cause | Protection | Status |
| --- | --- | --- | --- | --- | --- | --- |
| F016.2 | 2026-06-30 | pending | Live UI showed English whole-paper summary labels for a Chinese prompt and long raw chunk text in summaries. | Whole-paper composition did not receive the question for language selection and used full citation quotes in section/global lines. | Added Chinese label selection, bounded summary excerpts, focused regression tests, live UI verification, frontend build/type-check, and full backend suite. | verified |
| F016.1 | 2026-06-29 | 3f5c425 | Whole-paper summary could still behave like an extractive section list and early-page sweep. | F013 created the route but did not yet implement section-level compression or section-balanced evidence collection. | Focused answering/database tests, route tests, py_compile, and full backend suite. | verified |

## Evidence

- Focused answering/database tests: `29 passed`.
- Route/session focused tests: `8 passed`.
- Full backend suite: `189 passed`.
- 2026-06-30 live UI patch verification: latest Project-bound whole-paper summary response used Chinese labels, `citation_count=15`, `evidence_scope=project`, and bounded excerpts; `pytest ScienceClaw/backend/tests -q` -> `192 passed`.
- Python compile check for touched backend modules: passed.
- AgentMentor F016 feature-index and strict structural checks: passed.

## Recovery Snapshot

- Read first: this Feature, F013, F004, F015.
- Current capability state: F013 routes whole-paper summary separately; F016 adds section-balanced evidence collection and hierarchical composition.
- Known risks: This slice is deterministic compression, not LLM-authored section synthesis. Later work can add model-based section compression once Research Assistant answer generation has an explicit LLM contract.
- Next safe action: Live UI verification with a long paper, then consider an LLM section summarizer as a follow-up.

## Next Step

Validate with a long real paper in the running app.
