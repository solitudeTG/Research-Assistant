---
id: F001
doc_kind: feature
status: active
owner: solitudeTG
created: 2026-06-17
updated: 2026-06-21
---

# F001: Project Vision and Scope

## Goal

构建一个 Python-first 的智能科研工作台，帮助用户管理论文、提出有依据的问题、检查证据、运行多 Agent 研究流程、沉淀研究记忆，并生成可追溯的研究报告。

这个项目既要适合展示现代 Agent 工程能力，也要保持产品方向清晰：所有主要能力都必须服务真实科研工作流，而不是堆叠通用聊天或泛工具能力。

## Background

Research Assistant 的背景是科研任务正在从单次问答转向持续、可审查、可沉淀的工作流。研究者、学生和科研型开发者在真实工作中需要反复处理论文、网页、数据库、笔记、结论和输出文档；他们关心的不只是“模型能否回答”，还包括答案是否有来源、来源是否支撑结论、过程是否可追踪、后续是否能复用已经确认的研究知识。

普通聊天机器人适合解释和草拟内容，但不天然区分 citation evidence、context-only memory、process trace 和 model reasoning。缺少这些边界时，系统很容易把摘要、记忆或工具日志包装成证据，导致研究结论不可审查。传统文献管理工具擅长保存资料，却通常缺少 Agent 执行、证据审计、过程 trace 和自动研究产物生成能力。

因此，本项目不是追求“更通用的 AI 助手”，而是围绕智能研究工作台建立一套可验证闭环：资料进入系统后能被解析、索引、检索、引用、审计、沉淀和产出。ScienceClaw 提供了适合承载该闭环的工作台 UI、聊天壳、ActivityPanel、文件/产物面板、沙箱、SSE trace 和 Docker Compose 底座；Research Assistant 在此基础上融合旧版 Research Workbench 的论文 RAG、证据边界、三层记忆、多 Agent 研究流、Evidence Audit 和 Harness 思维。

## Vision Anchor

- 原始请求或来源：项目初始化方向与本地 `AGENTS.md` 军规。
- 用户痛点或工程问题：科研工作分散在论文、笔记、证据、结论和输出文档之间，用户需要一个能收集资料、检索可追溯证据、展示答案生成过程，并将审查后内容转化为产物的工作台。
- 期望结果：以 ScienceClaw 为 baseline application shell，融合旧版 Research Workbench 的论文 RAG、证据边界、三层记忆、多 Agent 研究流、Evidence Audit 和 Harness/AgentMentor 思维。
- 非目标或边界：不做通用个人聊天机器人；不默认暴露大规模工具集合；不把 memory 当作 citation evidence；不在 UI 中展示虚假的 Agent、并行、工具调用、证据或 workflow state；不在缺少明确编排需求时提前引入 LangGraph。
- Exit Gate 对照来源：本 Feature、linked Feature Map spec、`docs/baseline-import-notes.md`、以及后续每个 Research Assistant 功能的 AgentMentor closeout evidence。

## Current Status

In Progress。

当前仓库已经导入 ScienceClaw baseline application shell，并通过基础 backend/frontend 验证。Research Assistant 专属能力尚未完成，后续应按可验证能力增量继续开发。

## Links

- Spec: [F001-feature-map-and-rules-spec.md](../specs/F001-feature-map-and-rules-spec.md)
- Decision: [ADR-001 P0 Research Data and Retrieval Stack](../decisions/ADR-001-p0-research-data-and-retrieval-stack.md)
- Baseline import notes: [baseline-import-notes.md](../baseline-import-notes.md)
- Third-party notices: [THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md)

## Acceptance Criteria

- [x] 项目公开说明以 ScienceClaw 为二次开发 baseline，并保留 attribution / notice。
- [x] 当前仓库包含 ScienceClaw baseline application shell，且不包含参考副本的 `.git` 历史。
- [x] `AGENTS.md` 保持本地 Agent 规则文件，不进入 Git 管理。
- [x] 至少完成一组 baseline 验证命令，并记录命令、结果和已知警告。
- [ ] 支持论文上传与解析，并能把解析结果纳入研究工作流。
- [ ] 支持论文 RAG，并能返回可追溯 citation evidence。
- [ ] 明确区分 citation evidence 与 context-only memory。
- [ ] ActivityPanel / trace panel 只展示真实后端事件。
- [x] 支持 Evidence Audit 对结论和来源关系进行检查。
- [ ] 支持报告生成，且报告只基于已审查证据和明确上下文。
- [ ] 支持三层记忆，并保证 memory 不伪装为 citation evidence。

## Feature Intake

- Original problem: Researchers need a ScienceClaw-based workbench that can turn uploaded papers into traceable research evidence, answers, and Markdown artifacts.
- User pain point: Existing chat tools and generic file assistants do not reliably preserve paper structure, citation boundaries, evidence auditability, or process trace.
- Capability promise: Build the first verified loop inside the ScienceClaw shell: upload paper-like documents, parse to a canonical paper model, index evidence in PostgreSQL/pgvector, answer with citation evidence, expose real trace, and generate Markdown research outputs.
- Non-goals: P0 does not include web search, DOCX/PDF export, full multi-agent research orchestration, full three-layer memory productization, MongoDB migration, or ToolUniverse as the main selling point.
- Acceptance source: User-approved P0 objective, local AGENTS.md rules, ADR-001, and this F001 feature page.
- Open questions: Docling runtime packaging, embedding provider/model, final hybrid scoring formula, browser-level UI E2E, and the exact UI affordance for evidence inspection remain implementation follow-ups.

## Capability Contract

- Inputs: Uploaded paper or research document files from the existing ScienceClaw file upload path.
- Processing: Parse into a canonical paper model with title, authors, abstract, sections, pages/chunks, and source identity.
- Storage: Store Research Assistant papers, chunks, embeddings, FTS data, evidence records, citations, and report evidence maps in PostgreSQL + pgvector; keep MongoDB for ScienceClaw operational data.
- Outputs: Citation-grounded answers, inspectable evidence chunks, real ActivityPanel trace events, and Markdown research artifacts.
- Evidence boundary: Only paper/web/database evidence can become citation evidence; memory, model reasoning, and tool logs are context or trace only.

## Acceptance Map

| Claim | Acceptance | Evidence | Status |
| --- | --- | --- | --- |
| ScienceClaw shell is the baseline for P0 work. | Current work happens inside the imported `ScienceClaw/` application shell and keeps UI/workbench inheritance as a rule. | `ScienceClaw/` exists in the current repository; AGENTS.md and docs state ScienceClaw UI/workbench inheritance. | In progress |
| Uploaded text/Markdown research documents can be parsed into canonical paper artifacts. | Upload ingestion creates a canonical manifest, source-linked chunks, and an evidence preview artifact. | `python -m pytest ScienceClaw\backend\tests\test_research_ingestion.py ...` passed on 2026-06-19. | Partial |
| Uploaded PDF research documents have a GROBID-first parser path. | PDF ingestion uses GROBID TEI as the primary parser and falls back through optional Docling and PyMuPDF, preserving title, authors, abstract, section, page, chunk, and source identity where available. | `ScienceClaw\backend\tests\test_research_parsers.py` and `ScienceClaw\backend\tests\test_research_ingestion.py` passed on 2026-06-19; default `research_smoke.py` passed against healthy Docker GROBID and PostgreSQL with `parser=grobid-tei`. | Partial |
| Research evidence storage is bounded to PostgreSQL + pgvector. | Research schema defines papers, chunks, embeddings, FTS, evidence records, citations, and report evidence maps outside MongoDB. | `ScienceClaw/backend/research_assistant/storage/schema.sql`, repository tests, embedding tests, retrieval tests, and `docker compose config` passed on 2026-06-19. | Partial |
| Hybrid retrieval returns citation evidence records. | Retrieval must combine PostgreSQL FTS and pgvector candidates and return paper evidence with paper/section/page/quote identity. | `ScienceClaw\backend\tests\test_research_retrieval.py` passed on 2026-06-19. | Partial |
| Uploaded chunks receive vector embeddings during indexing. | Upload indexing generates deterministic P0 embeddings and persists them to `research_embeddings` under an explicit model name. | `ScienceClaw\backend\tests\test_research_embeddings.py` and `ScienceClaw\backend\tests\test_research_indexing.py` passed on 2026-06-19. | Partial |
| Research answers are citation-grounded. | Research answer generation must use paper evidence hits only and return inspectable citations with chunk identity. | `ScienceClaw\backend\tests\test_research_answering.py` passed on 2026-06-19; `sessions.py` compiles with `/research/answer` route. | Partial |
| ScienceClaw Chat renders inspectable paper citations. | Research answers returned through the ScienceClaw workbench show citation evidence with paper, section/page, quote, and chunk id. | `npm.cmd run build` passed on 2026-06-19 after `ChatMessage.vue`, `ChatPage.vue`, and `agent.ts` research-answer wiring. | Partial |
| Follow-up questions can stay in the uploaded-paper research context. | The frontend can detect session-level indexed paper evidence through `/research/status`; after a session has indexed papers, plain text follow-up questions route to `/research/answer` instead of falling back to the generic agent path. | `ScienceClaw\backend\tests\test_research_database.py` covers the session status DB query; `npm.cmd run build` passed on 2026-06-19 after ChatPage research mode wiring. | Partial |
| Users can leave the research answer path when needed. | When indexed paper evidence exists, the ScienceClaw chat header exposes a compact Research/General toggle so follow-up prompts can use either citation-evidence answers or the generic agent path. | `npm.cmd run build` passed on 2026-06-19 after the ChatPage Research/General toggle wiring. | Partial |
| Upload trace exposes real upload, parse, and index steps. | Research document upload emits separate ActivityPanel step events for file upload, parsing, and PostgreSQL indexing; parser and index failures are represented by the actual failed/deferred step rather than a fake completed workflow. | `ScienceClaw\backend\route\sessions.py` compiles after splitting upload trace; focused backend tests and frontend build passed on 2026-06-19. | Partial |
| Markdown research artifacts can be generated from uploaded paper evidence. | A research report route writes Markdown and an evidence map into the session workspace, persists report-to-evidence rows in PostgreSQL, emits real step/done events, and exposes files through existing round file/file panel mechanics. | `ScienceClaw\backend\tests\test_research_reports.py`, repository/database tests, `py_compile`, and frontend build passed on 2026-06-19. | Partial |
| P0 answers and reports expose a basic Evidence Audit. | Citation-grounded answers audit each extracted claim against attached paper citations, reject context-only sources as citation evidence, mark no-citation answers unsupported, expose audit metadata in the Chat answer card, and write audit status into Markdown reports and sidecar evidence maps. The Chat audit block and Markdown report also expose citation-evidence versus context-only source boundaries. Answer and report audit results are persisted in PostgreSQL under stable `answer` / `report` subjects and can be retrieved through a session-scoped API, so later report/composer gates can recover the audit boundary instead of relying only on chat metadata. | `ScienceClaw\backend\tests\test_research_audit.py`, `ScienceClaw\backend\tests\test_research_answering.py`, `ScienceClaw\backend\tests\test_research_reports.py`, full `test_research_*.py`, `py_compile`, `docker compose config`, `npm.cmd run build`, and Harness strict knowledge check passed on 2026-06-20. Audit persistence follow-up: focused audit/storage/report/route tests passed at `17 passed`; research test suite passed at `32 passed` on 2026-06-21. Audit retrieval follow-up: repository/database/session-route tests passed at `18 passed`; research test suite passed at `37 passed` on 2026-06-21. | Partial |
| The uploaded-paper loop has a repeatable real-service smoke check. | A smoke script can run ingestion, PostgreSQL/pgvector indexing, hybrid answer, and Markdown report generation against real services, with GROBID required by default and fallback mode explicitly labeled. | Default `python ScienceClaw\backend\scripts\research_smoke.py` passed on 2026-06-19 against healthy Docker GROBID and PostgreSQL/pgvector; output showed `parser=grobid-tei`, `grobid_available=True`, `citations=2`. | Partial |
| GROBID smoke cannot be satisfied by fallback parsing. | The default smoke path must require GROBID availability and assert the final parser is `grobid-tei`; fallback smoke requires the explicit `--allow-grobid-unavailable` flag. | `research_smoke.py` default path passed with `parser=grobid-tei`; `ScienceClaw\backend\tests\test_research_parsers.py` also asserts GROBID requests ignore environment proxies via `trust_env=False`. | Partial |
| Full P0 uploaded-paper UI loop works inside ScienceClaw shell. | A browser-level run must use the ScienceClaw UI file input to upload a PDF, wait for GROBID parsing and PostgreSQL/pgvector indexing, ask a paper-grounded question, inspect citation evidence and ActivityPanel steps, generate a Markdown report, and see Markdown plus evidence map files in the file panel. | Browser Playwright E2E for session `MS7Vvi7aSGh8XKEYXLARsv` used `input[type=file]` with `ui-file-picker-evidence-boundaries.pdf`; final status `completed`, error events `[]`, visible citation card and paper chunk, ActivityPanel showed upload/parse/index/retrieval/report steps, and file panel showed `research-report-j3PppgionQCydYPjKGEJ6v.md` plus `.evidence.json`. | Verified |
| Full P0 uploaded-paper UI loop has a durable checked-in E2E runner. | The repository must include a repeatable browser E2E script that exercises the ScienceClaw UI file input, verifies indexed uploaded-paper evidence, confirms visible citation evidence in Chat, generates a Markdown research report, and asserts real trace/file evidence from the session APIs. | `$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python ScienceClaw\backend\scripts\research_ui_e2e.py --timeout-ms 60000` passed on 2026-06-20 for session `Zuo72SRkrzMnKFc4DF7LsP`, with `citations=1`, `activity_steps=9`, and report files `research-report-8xy8WYgbf6ztbw6uBoVUA6.md` plus `.evidence.json`. | Verified |

## State Timeline

| Date | State | Evidence |
| --- | --- | --- |
| 2026-06-17 | ScienceClaw baseline imported. | Baseline import notes and existing commit references. |
| 2026-06-19 | P0 data/retrieval choices accepted. | ADR-001. |
| 2026-06-19 | First ingestion/storage implementation slice started. | Research ingestion tests, schema test, upload route integration, compose config verification. |
| 2026-06-19 | First hybrid retrieval backend contract added. | Retrieval test verifies FTS + pgvector candidate SQL and paper evidence return model. |
| 2026-06-19 | P0 local embedding provider and upload indexing service added. | Embedding and indexing tests verify chunk identity, vector dimensions, and embedding metadata. |
| 2026-06-19 | Backend research-answer path added. | Answering tests verify citation-only answer composition; route compiles with real session events. |
| 2026-06-19 | Frontend research answer and citation evidence rendering added. | Chat workbench calls `/research/answer` for indexed research attachments and renders citation cards. |
| 2026-06-19 | Session-level research context added. | `/research/status` reports indexed paper/chunk counts and ChatPage keeps follow-up questions on the citation-evidence answer path. |
| 2026-06-19 | Research/General chat toggle added. | ChatPage exposes a compact header toggle whenever indexed paper evidence exists, allowing users to leave the research answer path without removing papers. |
| 2026-06-19 | Upload trace split into real workflow steps. | Research uploads now emit upload, parse, and index step events with failure/deferred states attached to the actual step. |
| 2026-06-19 | Research answer/report failure trace hardened. | `/research/answer` and `/research/report` now publish and persist failed step events when citation retrieval or Markdown artifact generation fails after the step starts; route-level tests assert both failure paths. |
| 2026-06-19 | Markdown research artifact path added. | `/research/report` writes Markdown and evidence map files, persists report evidence rows, emits real step/done events, and frontend offers a report button on citation-grounded answers. |
| 2026-06-19 | GROBID-first PDF parser path added. | PDF ingestion now calls GROBID TEI first, then optional Docling, then PyMuPDF fallback; compose includes a `grobid` service. |
| 2026-06-19 | Real PostgreSQL fallback smoke passed. | `research_smoke.py --allow-grobid-unavailable` proved PDF fallback ingestion, indexing, citation answer, and Markdown report generation against Docker PostgreSQL/pgvector. |
| 2026-06-19 | GROBID E2E acceptance tightened. | Default `research_smoke.py` requires `parser=grobid-tei`; compose exposes `GROBID_IMAGE` so environments can use a reachable mirror or preloaded tag without editing project files. |
| 2026-06-19 | GROBID-backed smoke passed. | `docker pull grobid/grobid:0.8.0`, `docker compose up -d postgres grobid`, and default `research_smoke.py` passed with `parser=grobid-tei`, proving the PDF primary parser path against real services. |
| 2026-06-19 | Full UI file-input P0 loop verified. | Browser Playwright drove ScienceClaw login, session page, `input[type=file]` upload, research question, citation rendering, ActivityPanel step inspection, Markdown report generation, and round file panel inspection for session `MS7Vvi7aSGh8XKEYXLARsv`. |
| 2026-06-20 | Durable browser UI E2E runner added. | `ScienceClaw\backend\scripts\research_ui_e2e.py` passed against the running Docker stack and verifies UI upload, citation rendering, report generation, trace steps, and report/evidence files. |
| 2026-06-20 | Basic Evidence Audit slice added. | Research answers now carry audit metadata; Chat renders a compact Evidence Audit status; Markdown reports and sidecar evidence maps include audit status and counts. |
| 2026-06-20 | Evidence boundary inspection added to audit surfaces. | Chat audit details and Markdown reports now show which source classes are citation evidence and which are context-only. |
| 2026-06-21 | Evidence Audit results persisted. | PostgreSQL research storage now includes answer/report audit results with status, counts, boundaries, and claim JSON; answer/report paths persist audit subjects after generation. |
| 2026-06-21 | Persisted Evidence Audit results made recoverable. | Repository/database read paths and a session-scoped `/research/audit/{subject_type}/{subject_id}` route return stored audit records for answer/report subjects. |

## Recovery Snapshot

- Current state: ScienceClaw baseline is present; P0 docs/ADR define the intended loop; a Research Assistant ingestion module, GROBID-first PDF parser path with Docling/PyMuPDF fallback, PostgreSQL/pgvector schema, repository writes, local embedding provider, embedding persistence, upload indexing service, hybrid evidence retrieval contract, backend research-answer route, basic Evidence Audit, frontend citation/audit rendering, ActivityPanel step mapping, and Markdown research artifact route now exist and have been exercised through the ScienceClaw UI.
- Verified evidence: focused backend tests, frontend build, Python compile checks, `docker compose config`, Harness strict validation, fallback PostgreSQL smoke, GROBID-backed smoke, API-level uploaded-paper E2E, browser UI recovery checks, and browser-level UI file-input E2E passed on 2026-06-19.
- Known gaps: P0 uploaded-paper research loop is verified and now has a durable checked-in browser E2E runner. The first Evidence Audit slice is deterministic and claim-to-citation based; audit results are now durable and recoverable through PostgreSQL-backed API paths, but richer audit heuristics, multi-source audit, UI-level audit lookup, and composer gating remain follow-up work. Markdown reports are still extractive evidence notes rather than polished composed reports.
- Next safe action: Move to richer evidence inspection, stronger Evidence Audit, report quality, or the next scoped research workflow.

## Patch History

| Patch | Date | Commit | Symptom | Root Cause | Protection | Status |
| --- | --- | --- | --- | --- | --- | --- |
| F001.1 | 2026-06-19 | uncommitted | Research step events were visible as compact process markers, but ActivityPanel did not show concrete research steps for restored sessions. | ActivityPanel renders `plan.steps`, while the research loop emits real `step` events without a separate `plan` event. | `ChatPage.vue` now syncs `step` events into a lightweight local activity plan; browser UI check showed upload, parse, index, retrieval, and Markdown generation steps in the panel. | Verified |
| F001.2 | 2026-06-19 | uncommitted | Restoring a session after research-only upload could trigger generic agent reconnect and create unrelated error trace. | Research upload appended step events but left the session in `pending`, so ChatPage treated it as an unfinished generic agent run. | Research upload now marks the session `completed` after the final upload/parse/index step; route test asserts this status, and UI E2E session `MS7Vvi7aSGh8XKEYXLARsv` ended with `error_events=[]`. | Verified |

## Evidence

- `35d660fcc060ed114582be5dfa992bc6f6698113` added public ScienceClaw attribution notices.
- `0d5d2ff0c549ef1a94a3a0f724a7968b9c696c15` imported the ScienceClaw baseline application shell.
- `c781ce23d22f032a966a2602555ed9a6f0e4f47d` recorded baseline import verification and the next Research Assistant development order.
- `ADR-001` records accepted P0 choices: GROBID primary parser, Docling/PyMuPDF fallback, PostgreSQL full-text search + pgvector hybrid retrieval, Markdown reports, deferred web search, and PostgreSQL research domain storage.
- 2026-06-19 implementation slice evidence:
  - `python -m pytest ScienceClaw\backend\tests\test_research_ingestion.py ScienceClaw\backend\tests\test_research_store_schema.py --basetemp .pytest_tmp\run`
  - `python -m pytest ScienceClaw\backend\tests\test_research_ingestion.py ScienceClaw\backend\tests\test_research_store_schema.py ScienceClaw\backend\tests\test_research_repository.py --basetemp .pytest_tmp\run`
  - `python -m pytest ScienceClaw\backend\tests\test_research_ingestion.py ScienceClaw\backend\tests\test_research_store_schema.py ScienceClaw\backend\tests\test_research_repository.py ScienceClaw\backend\tests\test_research_retrieval.py ScienceClaw\backend\tests\test_research_database.py --basetemp .pytest_tmp\run`
  - `python -m pytest ScienceClaw\backend\tests\test_research_ingestion.py ScienceClaw\backend\tests\test_research_store_schema.py ScienceClaw\backend\tests\test_research_repository.py ScienceClaw\backend\tests\test_research_retrieval.py ScienceClaw\backend\tests\test_research_database.py ScienceClaw\backend\tests\test_research_embeddings.py ScienceClaw\backend\tests\test_research_indexing.py --basetemp .pytest_tmp\run`
  - `python -m pytest ScienceClaw\backend\tests\test_research_ingestion.py ScienceClaw\backend\tests\test_research_store_schema.py ScienceClaw\backend\tests\test_research_repository.py ScienceClaw\backend\tests\test_research_retrieval.py ScienceClaw\backend\tests\test_research_database.py ScienceClaw\backend\tests\test_research_embeddings.py ScienceClaw\backend\tests\test_research_indexing.py ScienceClaw\backend\tests\test_research_answering.py --basetemp .pytest_tmp\run`
  - `python -m pytest ScienceClaw\backend\tests\test_research_ingestion.py ScienceClaw\backend\tests\test_research_store_schema.py ScienceClaw\backend\tests\test_research_repository.py ScienceClaw\backend\tests\test_research_retrieval.py ScienceClaw\backend\tests\test_research_database.py ScienceClaw\backend\tests\test_research_embeddings.py ScienceClaw\backend\tests\test_research_indexing.py ScienceClaw\backend\tests\test_research_answering.py ScienceClaw\backend\tests\test_research_reports.py --basetemp .pytest_tmp\run -q` -> `16 passed`
  - `python -m pytest ScienceClaw\backend\tests\test_research_ingestion.py ScienceClaw\backend\tests\test_research_parsers.py ScienceClaw\backend\tests\test_research_store_schema.py ScienceClaw\backend\tests\test_research_repository.py ScienceClaw\backend\tests\test_research_retrieval.py ScienceClaw\backend\tests\test_research_database.py ScienceClaw\backend\tests\test_research_embeddings.py ScienceClaw\backend\tests\test_research_indexing.py ScienceClaw\backend\tests\test_research_answering.py ScienceClaw\backend\tests\test_research_reports.py --basetemp .pytest_tmp\run -q` -> `19 passed`
  - `docker pull grobid/grobid:0.8.0` initially timed out after 604 seconds, then succeeded on retry.
  - `docker compose up -d postgres` -> PostgreSQL/pgvector container reached healthy status.
  - `$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python ScienceClaw\backend\scripts\research_smoke.py --allow-grobid-unavailable` -> `research smoke passed`, `parser=pymupdf-fallback`, `grobid_available=False`, `citations=1`.
  - `research_smoke.py` default path now asserts `parser=grobid-tei`; fallback smoke remains opt-in through `--allow-grobid-unavailable`.
  - `docker compose config` passed after changing the `grobid` service image to `${GROBID_IMAGE:-grobid/grobid:0.8.0}`.
  - Upload trace split verification: focused backend tests (`19 passed`), `py_compile`, `docker compose config`, and frontend build passed after splitting upload/parse/index step events.
  - Research answer/report failure trace hardening: `ScienceClaw\backend\tests\test_research_session_routes.py` asserts failed step persistence for answer retrieval and report generation exceptions; focused backend tests passed at `21 passed` with repo-local `TMP`/`TEMP`.
  - GROBID proxy hardening: `ScienceClaw\backend\tests\test_research_parsers.py` asserts GROBID PDF requests pass `trust_env=False`; focused backend tests now pass at `22 passed`.
  - `docker compose up -d postgres grobid` -> PostgreSQL and GROBID reached healthy status.
  - `$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python ScienceClaw\backend\scripts\research_smoke.py` -> `research smoke passed`, `parser=grobid-tei`, `grobid_available=True`, `citations=2`.
  - `python -m py_compile ScienceClaw\backend\route\sessions.py ScienceClaw\backend\research_assistant\answering.py ScienceClaw\backend\research_assistant\embeddings.py ScienceClaw\backend\research_assistant\indexing.py ScienceClaw\backend\research_assistant\ingestion.py ScienceClaw\backend\research_assistant\models.py ScienceClaw\backend\research_assistant\retrieval.py ScienceClaw\backend\research_assistant\storage\database.py ScienceClaw\backend\research_assistant\storage\repository.py ScienceClaw\backend\config.py`
  - `npm.cmd run build` in `ScienceClaw\frontend` after frontend research report wiring -> passed
  - `docker compose config`
  - API-level uploaded-paper E2E against running services: login, create session, upload generated PDF, parse with `parser=grobid-tei`, index to `status=indexed`, answer with `answer_citations=1`, generate report with `report_citations=1`, and return Markdown plus `.evidence.json` round files for session `H4CWTZzw6k8HvkUariGVQq`.
  - Browser UI check for session `H4CWTZzw6k8HvkUariGVQq`: restored Research mode answer with a visible citation card, opened ActivityPanel with upload/parse/index/retrieval/Markdown generation steps, and opened the round file panel showing `research-report-2hkTTBESBTVuXwoYmMwYCS.md` plus `research-report-2hkTTBESBTVuXwoYmMwYCS.evidence.json`.
  - ActivityPanel step compatibility patch verification: `npm.cmd run build` passed; focused backend tests passed at `22 passed`; browser UI check showed step-derived task progress.
  - Research-upload session status hardening: focused backend tests passed at `23 passed`; `test_research_upload_marks_session_completed_after_indexing` asserts an indexed research upload closes the session instead of leaving it pending for generic reconnect.
  - Full browser UI file-input E2E: Python Playwright logged into ScienceClaw, created session `MS7Vvi7aSGh8XKEYXLARsv`, drove `input[type=file]` with `ui-file-picker-evidence-boundaries.pdf`, observed session status `completed`, asked `What does the paper say about evidence boundaries?`, saw a visible `Citation evidence` card and paper chunk label, clicked `Generate Markdown research report`, inspected ActivityPanel steps via `.process-indicator`, and opened the round file panel. Final event evidence: upload/parse/index/retrieval/report steps present, `round_files=["research-report-j3PppgionQCydYPjKGEJ6v.evidence.json","research-report-j3PppgionQCydYPjKGEJ6v.md"]`, `error_events=[]`.
  - Durable browser UI E2E runner: `$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python ScienceClaw\backend\scripts\research_ui_e2e.py --timeout-ms 60000` -> `research UI E2E passed`, session `Zuo72SRkrzMnKFc4DF7LsP`, `citations=1`, `activity_steps=9`, `round_files=["research-report-8xy8WYgbf6ztbw6uBoVUA6.evidence.json","research-report-8xy8WYgbf6ztbw6uBoVUA6.md"]`.
  - Final verification after UI E2E: `npm.cmd run build`, `docker compose config`, default `research_smoke.py` with `parser=grobid-tei`, and Harness strict knowledge check all passed.
- 2026-06-20 basic Evidence Audit slice evidence:
  - `$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; $env:TMP='E:\Self-Project\Research-Assistant\.pytest_tmp'; $env:TEMP='E:\Self-Project\Research-Assistant\.pytest_tmp'; python -m pytest ScienceClaw\backend\tests\test_research_audit.py ScienceClaw\backend\tests\test_research_answering.py ScienceClaw\backend\tests\test_research_reports.py --basetemp .pytest_tmp\run -q` -> `6 passed`.
  - `python -m py_compile ScienceClaw\backend\research_assistant\audit.py ScienceClaw\backend\research_assistant\answering.py ScienceClaw\backend\research_assistant\reports.py`
  - `npm.cmd run build` in `ScienceClaw\frontend` -> passed with existing Browserslist/CSS/chunk warnings.
  - Boundary inspection follow-up: `python -m pytest ScienceClaw\backend\tests\test_research_reports.py --basetemp .pytest_tmp\run -q` -> `1 passed`; all `ScienceClaw\backend\tests\test_research_*.py` -> `29 passed`; `python -m py_compile ScienceClaw\backend\research_assistant\reports.py`; `npm.cmd run build` in `ScienceClaw\frontend` -> passed with existing Browserslist/CSS/chunk warnings.
- 2026-06-21 Evidence Audit persistence follow-up:
  - `$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; $env:TMP='E:\Self-Project\Research-Assistant\.pytest_tmp'; $env:TEMP='E:\Self-Project\Research-Assistant\.pytest_tmp'; python -m pytest ScienceClaw\backend\tests\test_research_store_schema.py ScienceClaw\backend\tests\test_research_repository.py ScienceClaw\backend\tests\test_research_database.py ScienceClaw\backend\tests\test_research_answering.py ScienceClaw\backend\tests\test_research_reports.py ScienceClaw\backend\tests\test_research_session_routes.py --basetemp .pytest_tmp\run -q` -> `17 passed`.
  - `$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; $env:TMP='E:\Self-Project\Research-Assistant\.pytest_tmp'; $env:TEMP='E:\Self-Project\Research-Assistant\.pytest_tmp'; python -m pytest ScienceClaw\backend\tests -k research --basetemp .pytest_tmp\run -q` -> `32 passed`.
- 2026-06-21 Evidence Audit retrieval follow-up:
  - `$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; $env:TMP='E:\Self-Project\Research-Assistant\.pytest_tmp'; $env:TEMP='E:\Self-Project\Research-Assistant\.pytest_tmp'; python -m pytest ScienceClaw\backend\tests\test_research_repository.py ScienceClaw\backend\tests\test_research_database.py ScienceClaw\backend\tests\test_research_session_routes.py --basetemp .pytest_tmp\run -q` -> `18 passed`.
  - `$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; $env:TMP='E:\Self-Project\Research-Assistant\.pytest_tmp'; $env:TEMP='E:\Self-Project\Research-Assistant\.pytest_tmp'; python -m pytest ScienceClaw\backend\tests -k research --basetemp .pytest_tmp\run -q` -> `37 passed`.
  - `python -m py_compile ScienceClaw\backend\research_assistant\storage\repository.py ScienceClaw\backend\research_assistant\storage\database.py ScienceClaw\backend\route\sessions.py`
  - `docker compose config`
- Baseline verification recorded in [baseline-import-notes.md](../baseline-import-notes.md):
  - `python -m compileall ScienceClaw\backend`
  - `npm.cmd ci` in `ScienceClaw\frontend`
  - `npm.cmd run build` in `ScienceClaw\frontend`

## Next Step

Move to richer evidence inspection, stronger Evidence Audit, report quality, or the next scoped research workflow.
