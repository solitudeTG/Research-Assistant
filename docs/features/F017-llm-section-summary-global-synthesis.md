---
id: F017
doc_kind: feature
status: completed
owner: solitudeTG
created: 2026-06-30
updated: 2026-06-30
---

# F017: LLM Section Summary to Global Synthesis

## Goal

Upgrade single-paper whole-paper summary from bounded extractive compression into LLM-authored section summaries followed by a global synthesis, while preserving citations only to original paper evidence.

## Vision Anchor

- Source: User approved the `hierarchical long-document RAG with evidence-preserving synthesis` direction after F016 live UI verification.
- User pain point: Extractive section excerpts are auditable but do not feel like a researcher has understood and synthesized the whole paper.
- Desired outcome: Whole-paper summary requests produce readable section-level understanding and a paper-level synthesis without turning generated summaries into citation evidence.
- Non-goals: No multi-paper synthesis, no multi-agent workflow, no long-form report generation, no LLM router expansion, no citation to generated section summaries.
- Exit Gate source: This Feature, F016, F013, F004, F015, focused tests, and live UI/API verification when model configuration is available.

## Feature Intake

- Original problem: F016 created the hierarchy but still used deterministic extractive snippets.
- User pain point: Users need whole-paper summaries that abstract research problem, method, contribution, results, limitations, and citation basis.
- Capability promise: Add an injectable LLM synthesis stage: evidence sweep -> section summaries as context-only intermediate artifacts -> global synthesis -> original evidence citations.
- Non-goals: Do not make generated summaries persistent evidence; do not broaden retrieval scope; do not add multi-paper comparison; do not require every test to call a real external LLM.
- Acceptance source: User request on 2026-06-30 to start F017.
- Open questions: Later slices can expose section-summary trace detail in ActivityPanel and add stronger JSON repair/evaluation once real-model variability is observed.

## Capability Contract

- F013 `whole_paper_summary` remains the route selector.
- F016 section-balanced evidence sweep remains the evidence collection layer.
- LLM section summaries are `context-only intermediate` and cannot be returned as `citation_evidence`.
- Final citations remain original `ResearchCitation` records from paper/web/database evidence.
- If LLM synthesis is unavailable or fails, the system falls back to the deterministic F016 summary rather than failing the whole answer.
- Tests must be able to inject a fake synthesizer to validate orchestration without external network calls.

## Decision Context

### Why

Long-document summary needs compression before synthesis. A section-summary stage gives the model a bounded representation of the whole paper while the answer still preserves original evidence citations for audit.

### Why Not

Directly sending all chunks to a single LLM call was rejected because it does not scale and hides the compression boundary. Citing generated summaries was rejected because it violates F004. Multi-Agent synthesis remains deferred until single-paper synthesis is stable.

### If Modifying This Area, Check

- F004 for citation evidence eligibility.
- F013 for task routing.
- F015 for session/project evidence scope.
- F016 for section-balanced evidence collection and fallback behavior.

## Current Status

Completed. F017 now uses an injectable/default LLM section-summary to global-synthesis stage for single-paper whole-paper summaries, with deterministic F016 fallback.

## Links

### Evidence

- [EV-008 LLM Section Summary to Global Synthesis Verification](../evidence/EV-008-llm-section-summary-global-synthesis-verification.md)

### External Context

- None.

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
- [F016 Hierarchical Whole Paper Summary](F016-hierarchical-whole-paper-summary.md)

## Acceptance Criteria

- [x] Whole-paper summary can call an LLM section/global synthesizer when available.
- [x] Section summaries and global synthesis are generated from admitted original citation evidence.
- [x] Generated summaries are not returned as citations and do not replace original citation records.
- [x] LLM synthesis failure falls back to deterministic F016 summary.
- [x] Verification covers orchestration, fallback, citation boundary, route behavior, frontend contract, build, and live API.

## Acceptance Map

| Claim | Acceptance | Evidence | Status |
| --- | --- | --- | --- |
| LLM synthesis is orchestrated after evidence admission. | A fake synthesizer receives section-grouped citation evidence and returns section/global content used in the answer. | [EV-008](../evidence/EV-008-llm-section-summary-global-synthesis-verification.md) | Pass |
| Citation boundary is preserved. | Returned `citations` remain original evidence records and generated summaries are not citation objects. | [EV-008](../evidence/EV-008-llm-section-summary-global-synthesis-verification.md) | Pass |
| Failure is recoverable. | Synthesizer exception returns deterministic F016 summary. | [EV-008](../evidence/EV-008-llm-section-summary-global-synthesis-verification.md) | Pass |
| Live route uses LLM synthesis when configured. | Local service response returns `summary_synthesis.mode=llm_section_global` for a whole-paper summary request. | [EV-008](../evidence/EV-008-llm-section-summary-global-synthesis-verification.md) | Pass |

## State Timeline

| Date | State | Trigger | Evidence | Note |
| --- | --- | --- | --- | --- |
| 2026-06-30 | active | User approved F017 | This Feature | Created to own LLM section/global synthesis slice. |
| 2026-06-30 | completed | Implementation and verification finished | [EV-008](../evidence/EV-008-llm-section-summary-global-synthesis-verification.md) | LLM synthesis, fallback, trace metadata, frontend contract, full backend tests, build, and live API passed. |

## Patch History

| Patch | Date | Commit | Symptom | Root Cause | Protection | Status |
| --- | --- | --- | --- | --- | --- | --- |
| F017.1 | 2026-06-30 | `4d1f046` | Live UI E2E could fall back to deterministic mode or accept unusable missing-context LLM prose. | Research answer did not reliably receive the selected model config, and the LLM synthesis path trusted missing-context/refusal output as usable. | Propagated model config into research answer, added missing-context/citation-label guards, deterministic section-context recovery, larger synthesis output budget, focused tests, and live UI trace verification. | completed |

## Evidence

[EV-008 LLM Section Summary to Global Synthesis Verification](../evidence/EV-008-llm-section-summary-global-synthesis-verification.md)

## Recovery Snapshot

- Read first: this Feature, F016, F013, F004, F015.
- Current capability: single-paper whole-paper summary uses an LLM section-summary to global-synthesis stage when available and falls back deterministically when unavailable.
- Known risks: Real LLM outputs may vary; tests must validate boundaries and orchestration rather than exact model prose.
- Next safe action: If output quality needs further improvement, add evaluation examples for real papers before changing prompts or synthesis granularity.

## Next Step

Monitor real-paper output quality and consider F014 multi-paper synthesis later, after core Research Assistant flows are stable.
