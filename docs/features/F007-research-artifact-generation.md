---
id: F007
doc_kind: feature
status: active
owner: solitudeTG
created: 2026-06-28
updated: 2026-06-29
---

# F007: Research Artifact Generation

## Goal

生成基于已审查证据和明确上下文的 Markdown 研究产物，并保留 evidence map、sidecar JSON、Trust Summary、limitations 和可追溯 citation。

## Vision Anchor

- 原始请求或来源：`F001` P0 研究产物目标、`ADR-001` Markdown report 边界。
- 用户痛点或工程问题：科研输出需要能复查证据、限制和上下文，而不是只得到一段不可审计文本。
- 期望结果：报告产物能进入文件/产物面板，且只把 approved evidence 作为可信 findings。
- 非目标或边界：P0 不负责 DOCX/PDF exporter，也不负责全自动多 Agent 写作流程。
- Exit Gate 对照来源：本 Feature、report tests、artifact/file panel E2E、Evidence Audit 输出。

## Feature Intake

- Original problem: Research answers need durable, inspectable artifacts.
- User pain point: Users need reports that preserve citation evidence, audit status, context-only memory, and limitations.
- Capability promise: Generate Markdown research artifacts with evidence maps and trust metadata.
- Non-goals: Do not implement DOCX/PDF export or autonomous literature-review pipelines here.
- Acceptance source: `F001`, `ADR-001`, report and UI E2E tests.
- Open questions: Future exporter formats and richer document preview behavior remain follow-ups.

## Capability Contract

- Generate Markdown reports from citation-grounded answers and audit output.
- Persist report evidence maps and sidecar JSON where needed.
- Include Trust Summary, Claim Checks, Citation Evidence, Context-Only Memory, Evidence Gaps, limitations, and next steps.
- Keep unsupported claims out of approved findings while preserving them as gaps.
- Surface generated files through the inherited ScienceClaw artifact/file mechanics.

## Decision Context

### Why

Markdown is enough for the first auditable research artifact and keeps P0 centered on evidence rather than export formatting.

### Why Not

DOCX/PDF export was deferred because formatting complexity would not improve the first evidence loop.

### If Modifying This Area, Check

- `ADR-001` report boundary.
- F004 evidence boundary and F006 audit contract.
- Report generation tests, sidecar tests, and UI/file-panel E2E.

## Current Status

Completed for MVP scope.

Markdown report generation now writes auditable research artifacts with evidence maps, sidecar JSON, Trust Summary, Reader Summary, Claim Checks, Citation Evidence, Context-Only Memory, Evidence Gaps, limitations, and file-panel visibility. This does not claim DOCX/PDF export, fully autonomous report composition, or online LLM-backed report E2E.

## Links

### Evidence

- [EV-001 Feature Governance Split Validation](../evidence/EV-001-feature-governance-split-validation.md)
- Historical verification currently recorded in [F001](F001-project-vision-and-scope.md).

### Decisions / ADRs

- [ADR-001 P0 Research Data and Retrieval Stack](../decisions/ADR-001-p0-research-data-and-retrieval-stack.md)

### Lessons

- None yet.

### Specs / Plans

- [F001 Feature Map and Rules Spec](../specs/F001-feature-map-and-rules-spec.md)

### Related Features

- [F004 Citation Evidence Boundary](F004-citation-evidence-boundary.md)
- [F006 Evidence Audit](F006-evidence-audit.md)
- [F008 Trace Honesty and Activity Panel](F008-trace-honesty-activity-panel.md)

### External Context

- None.

## Acceptance Criteria

- [x] Markdown report includes evidence-grounded findings.
- [x] Report sidecar/evidence map preserves citation and audit traceability.
- [x] Unsupported or invalid-source claims appear as gaps, not approved findings.
- [x] Generated report files are visible through existing artifact/file surfaces.

## Acceptance Map

| Claim | Acceptance | Evidence | Status |
| --- | --- | --- | --- |
| Markdown research artifacts can be generated. | `/research/report` creates Markdown files, sidecar/evidence JSON, report-to-evidence map rows, and round file entries. | Historical report tests and UI/file-panel E2E from `F001`; current research backend suite passed on 2026-06-29. | MVP done |
| Reports preserve audit and boundary information. | Reports include Trust Summary, Reader Summary, Claim Checks, Citation Evidence, Context-Only Memory, Evidence Gaps, limitations, and context boundaries. | Historical report follow-up evidence from `F001`; current research backend suite passed on 2026-06-29. | MVP done |
| Unsupported claims remain gaps. | Unsupported/invalid-source claims are excluded from approved findings and surfaced as Evidence Gaps with limitations/next steps. | Historical report gaps and limitations red-green verification from `F001`. | MVP done |
| Report citations expose source identity. | Report Citation Evidence entries render inspectable identity such as URL, database name, query, file path, and retrieval timestamp when present. | Historical report citation-identity and actual-source-scope tests from `F001`. | MVP done |

## State Timeline

| Date | State | Trigger | Evidence | Note |
| --- | --- | --- | --- | --- |
| 2026-06-28 | active | Feature split from F001 | This Feature and `INDEX.md` | Created to own report/artifact recovery. |
| 2026-06-29 | MVP completed | F001 historical evidence migrated to owning Feature | Current research backend suite and AgentMentor strict check | Export formats and online LLM-backed report E2E remain future scope. |

## Patch History

None yet.

## Evidence

Historical report-generation evidence migrated from `F001`:

- `/research/report` writes Markdown artifacts, sidecar/evidence JSON, report-to-evidence rows, and real report step/done events.
- Report tests verified Trust Summary, sidecar Trust Summary, Claim Checks, approved findings gating, clean reader-facing claim text, generic no-citation wording, same-user context-memory recall, Evidence Gaps, limitations, source identity, actual source-scope wording, context-boundary manifests, and Reader Summary.
- Route/frontend tests verified report completion messages, report response metadata, recovered report summaries, and file/artifact surface integration.
- Browser/UI E2E verified Markdown plus evidence-map files appear in the file panel.
- Current document-convergence verification: `$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python -m pytest ScienceClaw\backend\tests -k research -q --basetemp .pytest_tmp\progress-audit` -> `178 passed`; `knowledge_check.py --strict` -> 0 errors, 0 warnings.

## Recovery Snapshot

- Read first: this Feature, F006, F004, `ADR-001`.
- Current capability state: MVP Markdown research artifact path is complete and owned here.
- Known risks: LLM-backed report E2E is not verified without provider configuration.
- Next safe action: Attribute report output, sidecar, or artifact-panel changes here.
- Unblock condition: Provider key/model is needed for online LLM-backed report E2E.

## Next Step

Start a separate exporter or composition-quality Feature before claiming DOCX/PDF export, richer preview workflows, or online LLM-backed report quality.
