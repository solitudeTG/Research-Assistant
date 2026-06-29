---
id: F003
doc_kind: feature
status: active
owner: solitudeTG
created: 2026-06-28
updated: 2026-06-29
---

# F003: Research Document Ingestion

## Goal

让上传的论文或研究文档进入 Research Assistant 的 canonical paper model，并保留后续 citation evidence 所需的 source identity、section、page 和 chunk 边界。

## Vision Anchor

- 原始请求或来源：`F001` P0 目标、`ADR-001`、Feature Map spec。
- 用户痛点或工程问题：科研答案不能只基于无来源纯文本；文档摄取必须保留论文结构和可追溯定位。
- 期望结果：上传文档可以被解析、切分、建模，并进入研究工作流。
- 非目标或边界：本 Feature 不负责 answer 生成、Evidence Audit、报告生成或完整 web search。
- Exit Gate 对照来源：本 Feature、`ADR-001`、相关 ingestion/parser/indexing 测试。

## Feature Intake

- Original problem: Uploaded papers need a reliable path into structured research evidence.
- User pain point: Generic file chat loses paper structure and weakens citations.
- Capability promise: Parse research documents into canonical paper records and source-linked chunks.
- Non-goals: Do not solve retrieval ranking, report composition, or multi-agent orchestration here.
- Acceptance source: `F001`, `ADR-001`, ingestion/parser tests.
- Open questions: Docling packaging and complex PDF/OCR fallback policy remain follow-ups.

## Capability Contract

- Accept uploaded paper-like research documents from the inherited ScienceClaw file path.
- Use GROBID as the primary scholarly PDF parser path where available.
- Use Docling/PyMuPDF as fallback paths where appropriate.
- Persist canonical paper metadata, sections, pages/chunks, and source identity.
- Preserve enough structure for citation evidence and Evidence Audit.

## Decision Context

### Why

Citation-grounded research depends on source identity and document structure. Parser output should be normalized before downstream retrieval or report generation.

### Why Not

Raw text extraction alone was rejected because it loses scholarly structure, page/section identity, and evidence auditability.

### If Modifying This Area, Check

- `ADR-001` parser and storage decision.
- Parser, ingestion, indexing, and smoke tests.
- Source identity and chunk identity fields consumed by retrieval, audit, and reports.

## Current Status

In Progress. Initial ingestion/parser/indexing slices have verification evidence recorded in `F001`.

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
- [F005 Hybrid Retrieval and Grounded Answering](F005-hybrid-retrieval-grounded-answering.md)

### External Context

- None.

## Acceptance Criteria

- [ ] Uploaded research documents produce canonical paper artifacts.
- [ ] PDF ingestion uses GROBID-first behavior with documented fallback.
- [ ] Chunks preserve source identity, section, page, and chunk id.
- [ ] Parser/index failures are visible as real workflow states, not fake success.

## Acceptance Map

| Claim | Acceptance | Evidence | Status |
| --- | --- | --- | --- |
| Uploaded text/Markdown documents can become canonical paper artifacts. | Upload ingestion creates a canonical manifest and source-linked chunks. | Historical test evidence in `F001`; move focused evidence here on next ingestion change. | Partial |
| Uploaded PDFs have a GROBID-first path. | PDF ingestion attempts GROBID TEI before fallback parsers. | Historical parser/smoke evidence in `F001`; `ADR-001`. | Partial |

## State Timeline

| Date | State | Trigger | Evidence | Note |
| --- | --- | --- | --- | --- |
| 2026-06-28 | active | Feature split from F001 | This Feature and `INDEX.md` | Created to own ingestion/parser recovery. |
| 2026-06-29 | patched | Real Research Library PDF upload E2E exposed storage-text failures | API E2E, browser UI verification, focused repository/session tests | F003.1 added PostgreSQL-safe text and bounded citation quote handling at the storage boundary. |

## Patch History

| Patch | Date | Commit | Symptom | Root Cause | Protection | Status |
| --- | --- | --- | --- | --- | --- | --- |
| F003.1 | 2026-06-29 | pending | Uploading a real PDF from `paper_data` into Research Library returned 500 during indexing. | Parsed PDF text contained NUL bytes rejected by PostgreSQL text, and full chunk text used as citation quote exceeded the B-tree unique-index row limit. | Storage-boundary tests for NUL removal and bounded evidence quotes; full chunk text remains in `research_chunks.content`; real PDF E2E verified 19 chunks, 19 evidence records, and 19 embeddings. | verified |

## Evidence

Focused ingestion evidence should be moved here the next time ingestion/parser behavior changes. Current historical evidence remains in `F001`.

Verification evidence from 2026-06-29:

- Real upload source: `E:\Self-Project\Research-Assistant\paper_data\Space-Time_Beamforming_for_LEO_Satellite_Communications_Enabling_Extremely_Narrow_Beams(1).pdf`.
- First failing E2E: `asyncpg.exceptions.CharacterNotInRepertoireError: invalid byte sequence for encoding "UTF8": 0x00` while writing `research_chunks`.
- Second failing E2E after NUL protection: `asyncpg.exceptions.ProgramLimitExceededError: index row size ... exceeds btree ... for index "research_evidence_records_chunk_id_evidence_type_quote_key"`.
- Passing E2E after fix: upload returned `parser=grobid-tei`, `chunk_count=19`, `evidence_record_count=19`, `embedding_count=19`, `status=indexed`, `citation_ready=true`.
- Browser UI verification: Research Library project `E2E 论文上传验证 0629-1034` showed `1 篇论文`, `19 条证据`, paper title `Space-Time Beamforming for LEO Satellite Communications: Enabling Extremely Narrow Beams`, parser `grobid-tei`, and status `已索引`.
- `$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; pytest ScienceClaw/backend/tests/test_research_repository.py ScienceClaw/backend/tests/test_research_database.py ScienceClaw/backend/tests/test_research_session_routes.py -q --basetemp=.pytest_tmp\e2e-upload-related` -> `83 passed`.

## Recovery Snapshot

- Read first: `ADR-001`, this Feature, `F001` historical Acceptance Map.
- Current capability state: Initial ingestion and parser slices exist, with evidence still aggregated in `F001`.
- Known risks: Parser fallback behavior and Docling packaging are not fully productized.
- Next safe action: Before changing parser or chunk identity, add/move focused tests and update this Feature.
- Unblock condition: None.

## Next Step

Move ingestion/parser-specific evidence from `F001` into this Feature when the next ingestion work starts.
