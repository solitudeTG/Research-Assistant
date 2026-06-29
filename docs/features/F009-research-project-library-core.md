---
id: F009
doc_kind: feature
status: active
owner: solitudeTG
created: 2026-06-28
updated: 2026-06-29
---

# F009: Research Project Library Core

## Goal

建立 Research Project 与 Research Library 的最小资产管理闭环，让论文进入可信研究库时必须归属到明确研究项目，并能在 UI 中查看项目下的论文资产、索引状态和基础元数据。

## Vision Anchor

- 原始请求或来源：用户确认 Research Assistant 定位接近 Notebook/Workspace，Project 作为数据隔离边界，Research Library 管理 Project 与资产。
- 用户痛点或工程问题：普通 Chat 上传论文会产生临时理解，但不应该自动污染 RAG；用户需要看得见、管得住已经进入研究库的可信资产。
- 期望结果：Research Library 页面可以创建/选择 Project，上传论文到 Project，展示 Project 下的论文资产和索引状态。
- 非目标或边界：本 Feature 不负责 Chat 会话绑定 Project、不负责 RAG 路由门控、不负责临时 Chat 文件提升入库动作、不改变 citation evidence 合同。
- Exit Gate 对照来源：本 Feature、`F003` 文档摄取、`F004` 证据边界、`ADR-001` 研究域存储决策、Research Library UI/route/backend tests。

## Feature Intake

- Original problem: Trusted research assets need a visible project-scoped home before they are used by RAG.
- User pain point: Without a Research Library, users cannot tell which papers are indexed, trusted, or available for citation.
- Capability promise: Provide a ScienceClaw-styled Library page for project creation, project selection, paper upload, and paper asset visibility.
- Non-goals: Do not implement project-scoped chat retrieval or admission thresholding here.
- Acceptance source: User-approved four-Feature breakdown on 2026-06-28 and existing F003/F004/F005 contracts.
- Open questions: Full paper metadata editing, tags, collections, notes, and collaboration are deferred.

## Capability Contract

- Research Project is the primary data-isolation boundary for trusted research assets.
- A paper added through Research Library must be associated with exactly one Project in the MVP.
- Library upload writes into the research-domain storage path, not the temporary Chat-only file path.
- The UI keeps ScienceClaw's dense, restrained workbench style and does not introduce a marketing or decorative page.
- Asset rows expose enough status for users to distinguish uploaded, parsed, indexed, failed, and citation-ready states.

## Decision Context

### Why

Project ownership is the first-principles boundary for trusted scientific context. Users should not manage a technical RAG toggle; they should manage research projects and the evidence assets available inside each project.

### Why Not

Automatically indexing every Chat upload was rejected because arbitrary files would pollute trusted RAG state. A standalone Project admin center was deferred because Project's first value is asset isolation, so it belongs naturally inside Research Library.

### If Modifying This Area, Check

- `F003` for ingestion and canonical paper model constraints.
- `F004` for citation evidence eligibility.
- `ADR-001` for PostgreSQL/pgvector research-domain storage.
- `F002` for ScienceClaw UI shell/style consistency.

## Current Status

In Progress. The first vertical slice now creates/lists Research Projects, lists Project paper assets, uploads papers directly into a Project Library path, and exposes a ScienceClaw-styled Research Library page.

## Links

### Evidence

- None yet.

### Decisions / ADRs

- [ADR-001 P0 Research Data and Retrieval Stack](../decisions/ADR-001-p0-research-data-and-retrieval-stack.md)

### Lessons

- None yet.

### Specs / Plans

- [F001 Feature Map and Rules Spec](../specs/F001-feature-map-and-rules-spec.md)

### Related Features

- [F003 Research Document Ingestion](F003-research-document-ingestion.md)
- [F004 Citation Evidence Boundary](F004-citation-evidence-boundary.md)
- [F005 Hybrid Retrieval and Grounded Answering](F005-hybrid-retrieval-grounded-answering.md)
- [F010 Project Scoped Chat](F010-project-scoped-chat.md)
- [F011 Evidence Admission Gate](F011-evidence-admission-gate.md)
- [F012 Chat To Library Promotion](F012-chat-to-library-promotion.md)

### External Context

- None.

## Acceptance Criteria

- [x] User can create a Research Project from Research Library.
- [x] User can select a Project and see its paper assets.
- [x] User can upload a paper from Research Library into the selected Project.
- [x] Uploaded paper records expose parsing/indexing/citation-readiness status.
- [x] UI follows ScienceClaw workbench density, spacing, and restrained visual language.

## Acceptance Map

| Claim | Acceptance | Evidence | Status |
| --- | --- | --- | --- |
| Research Project exists as a visible asset boundary. | Library UI and backend API create/list/select projects. | `147 passed` backend suite on 2026-06-28; `npm.cmd run type-check`; `npm.cmd run build`. | Implemented |
| Papers can be uploaded into a Project. | Library upload indexes or records a paper under the selected Project. | `test_upload_research_project_paper_indexes_into_project`; `test_persist_ingestion_result_can_attach_paper_to_project`. | Implemented |
| Project assets are inspectable. | Library table shows Project-scoped paper rows and status. | `test_list_project_paper_assets_reads_only_selected_project`; frontend contract test for `ResearchLibraryPage.vue`. | Implemented |

## State Timeline

| Date | State | Trigger | Evidence | Note |
| --- | --- | --- | --- | --- |
| 2026-06-28 | planned | User approved four-Feature breakdown | This Feature | Created to own Research Library and Project asset management. |
| 2026-06-28 | in_progress | First F009 implementation slice | Focused tests and type-check | Project/Library core is implemented; project-scoped Chat remains F010. |
| 2026-06-29 | patched | User E2E found Research Library create action appeared unresponsive | Browser E2E, backend schema check, focused tests, type-check, build | F009.1 restored static Library routing and startup schema initialization. |
| 2026-06-29 | patched | Real Research Library PDF upload E2E exposed indexing failures | API E2E, browser UI verification, focused repository/session tests | F009.2 verified Library upload with a real `paper_data` PDF after storage text protections. |
| 2026-06-29 | patched | Combined F009-F012 E2E found Library route left the global New Task control effectively unclickable | Browser UI E2E, frontend contract tests, type-check, build | F009.3 keeps the left panel expanded on Research Library so global session controls remain reachable. |

## Patch History

| Patch | Date | Commit | Symptom | Root Cause | Protection | Status |
| --- | --- | --- | --- | --- | --- | --- |
| F009.1 | 2026-06-29 | `5bf49d8` | Real E2E validation showed the Research Library create action did not complete. | Fixed chat child routes were declared after `:sessionId`, and the running backend did not initialize `research_assistant/storage/schema.sql` on startup. | Static route-order contract test, research schema initialization unit test, PostgreSQL table check, and browser E2E project creation. | verified |
| F009.2 | 2026-06-29 | `353307c` | Real PDF upload from Research Library returned 500 before a paper asset became visible. | Ingestion storage accepted parser output that could contain NUL bytes and used full chunk text as citation quote, exceeding PostgreSQL text/index constraints. | Repository regression tests plus real `paper_data` PDF E2E showing one indexed paper with 19 chunks and 19 citation evidence records in the Library UI. | verified |
| F009.3 | 2026-06-29 | pending | In Research Library, the left-panel New Task control appeared visible in DOM but did not navigate when clicked. | The Research Library navigation path could leave the left panel collapsed to 60px while the session-list content remained in the accessibility tree; the main Library content covered the tiny New Task hit area. | Frontend contract test requires Research Library to keep the left panel expanded and New Task to route to `/chat`; browser E2E showed the button width restored to 235px and URL changed to `/chat`. | verified |

## Patch Churn Review

F009 reached three patch rows on 2026-06-29, so this Feature now requires explicit churn review before closeout.

Assessment: the churn does not indicate that the Research Library boundary is wrong. The three fixes cover separate layers of the same Library capability: route/schema startup, ingestion storage constraints, and global shell interaction on the Library route. The common failure mode was that early validation proved focused units but did not repeatedly exercise the full visible Library workflow with a running service and real PDF data.

Decision: keep F009 as the owner for Research Library and Project asset management. No ADR or new Feature split is needed for this patch set. Future F009 changes must include focused regression tests plus a browser or API E2E check for the touched Library route, Project selection, and paper upload/promoted asset visibility before claiming the Library workflow is ready.

## Evidence

Verification evidence from 2026-06-28:

- `PYTHONPATH=E:\Self-Project\Research-Assistant\ScienceClaw;E:\Self-Project\Research-Assistant pytest backend/tests -q` -> `147 passed`.
- Focused backend/frontend contract suite -> `87 passed`.
- `npm.cmd run type-check` from `ScienceClaw/frontend` -> passed.
- `npm.cmd run build` from `ScienceClaw/frontend` -> passed with existing Browserslist/CSS/chunk-size warnings.

Verification evidence from 2026-06-29 Library upload E2E:

- Real upload source: `E:\Self-Project\Research-Assistant\paper_data\Space-Time_Beamforming_for_LEO_Satellite_Communications_Enabling_Extremely_Narrow_Beams(1).pdf`.
- API upload into project `E2E 论文上传验证 0629-1034` returned `parser=grobid-tei`, `chunk_count=19`, `evidence_record_count=19`, `embedding_count=19`, `status=indexed`, `citation_ready=true`.
- Browser UI showed the project with `1 篇论文` and `19 条证据`; selecting it showed the paper title, parser `grobid-tei`, `19` chunks, `19` citation evidence records, and status `已索引`.
- Backend logs after passing upload contained no `upload_research_project_paper_for_user`, `ProgramLimitExceeded`, `CharacterNotInRepertoire`, `Internal Server Error`, or `ERROR` entries for the final run.
- `$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; pytest ScienceClaw/backend/tests/test_research_repository.py ScienceClaw/backend/tests/test_research_database.py ScienceClaw/backend/tests/test_research_session_routes.py -q --basetemp=.pytest_tmp\e2e-upload-related` -> `83 passed`.
- `knowledge_check.py --feature-index docs/features/F009-research-project-library-core.md` -> pending for closeout after this update.

Verification evidence from 2026-06-29 combined F009-F012 E2E patch:

- Browser UI on `http://127.0.0.1:5173/chat/research-library` showed project `E2E UI链路验证 06290349` with `2 篇论文` and `39 条证据`.
- After refreshing the fixed UI, the left-panel New Task button had a 235px hit area and clicking it navigated from `/chat/research-library` to `/chat`.
- `pytest ScienceClaw/backend/tests/test_research_frontend_contracts.py -k "new_task_uses_canonical_chat_route or chinese_user_facing_copy" -q` -> `2 passed`.

Verification evidence from 2026-06-29:

- Browser E2E on `http://localhost:5173/chat/research-library` created `E2E 验证课题 0629-1004` and showed the selected project detail with an empty paper table.
- `docker compose exec -T postgres psql -U research -d research_assistant -c "select to_regclass('public.research_projects') as research_projects, to_regclass('public.research_session_projects') as research_session_projects;"` -> both tables returned.
- `$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; pytest ScienceClaw/backend/tests/test_research_database.py ScienceClaw/backend/tests/test_research_frontend_contracts.py -q` -> `42 passed`.
- `npm.cmd run type-check` from `ScienceClaw/frontend` -> passed.
- `npm.cmd run build` from `ScienceClaw/frontend` -> passed with existing Browserslist/CSS/chunk-size warnings.

## Recovery Snapshot

- Read first: this Feature, `F003`, `F004`, `F005`, `ADR-001`.
- Current capability state: Research Project schema/API, Library upload, Project paper listing, frontend API, route, nav entry, and Research Library page exist.
- Known risks: Project-scoped Chat retrieval is not implemented in this Feature and must be handled by `F010`; admission thresholds remain `F011`; Chat upload promotion remains `F012`.
- Next safe action: Run full research backend suite and frontend build, then start `F010` with tests proving cross-Project retrieval isolation.
- Unblock condition: None.

## Next Step

Close out the first F009 slice with full verification, commit, and push; then start F010 Project Scoped Chat.
