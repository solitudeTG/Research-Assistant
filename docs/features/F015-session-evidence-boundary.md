---
id: F015
doc_kind: feature
status: completed
owner: solitudeTG
created: 2026-06-29
updated: 2026-06-29
---

# F015: Session Evidence Boundary

## Goal

明确 Chat 上传论文的证据边界：普通 Chat 上传可以为了当前会话进行解析和临时索引，但不能自动成为 Research Project / Research Library 的长期 RAG 资产；只有用户显式点击“加入研究库”后，论文才进入 Project-scoped trusted evidence。

## Vision Anchor

- 原始请求或来源：用户认可业界产品中“Chat 附件可以临时处理，但长期知识资产需要显式加入 Project / Notebook / Library”的边界，并要求按该方案落地。
- 用户痛点或工程问题：当前 Chat 上传不会直接写入 Project RAG，但会自动写入 session evidence index；如果 UI、metadata 和检索范围不清晰，用户会误以为任意上传已经污染了研究库，重复上传失败也难以解释。
- 期望结果：session evidence 与 project evidence 在存储、检索、citation metadata、UI 状态和错误提示中都可区分。
- 非目标或边界：不做 Multi-Agent，不做多论文综合，不做 LLM Router，不重写 Research Library，不改变 F013 的 whole-paper summary 主线。
- Exit Gate 对照来源：本 Feature、F009 Research Library、F010 Project Scoped Chat、F012 Chat To Library Promotion、F013 Research Task Router。

## Feature Intake

- Original problem: Chat upload and Project Library ingestion need a trustworthy boundary that mirrors real research workflow.
- User pain point: Users need quick paper inspection without accidentally turning arbitrary files into trusted Project RAG assets.
- Capability promise: Keep Chat uploads session-scoped until explicit promotion, while preserving current-session PDF QA and whole-paper summary.
- Non-goals: No quality review workflow, no user-facing mode toggle, no multi-agent synthesis, no persistent cross-session use of unpromoted session uploads.
- Acceptance source: User-approved F015 design discussion on 2026-06-29.
- Open questions: Future duplicate-paper identity may need stronger fingerprinting beyond filename/path and parser metadata.

## Capability Contract

- Chat upload creates `session` evidence only.
- Research Library upload and Chat promotion create `project` evidence.
- Unbound Chat sessions can retrieve only their current session evidence.
- Project-bound Chat sessions can retrieve Project evidence plus current session evidence, with source scope visible in returned citations.
- Chat upload UI labels unpromoted PDFs as temporary materials.
- “加入研究库” is shown only when the session has a linked Research Project and an eligible temporary paper exists.
- Duplicate upload or duplicate promotion must return a clear boundary-aware reason instead of a generic upload failure.

## Current Status

Completed for the first boundary-hardening slice. Chat uploads now create session-scoped temporary evidence with scoped paper IDs, Library uploads and promotion create project-scoped evidence with separate project paper IDs, retrieval returns scope metadata, and the UI exposes temporary-material and citation-scope signals.

## Decision Context

### Why

Large PDF chat workflows require temporary parsing or indexing; otherwise current-session QA and summary quality collapse. But trusted research memory must be user-confirmed and Project-owned. The right boundary is not "never index Chat uploads"; it is "session index is temporary, Project index is explicit".

### Why Not

Fully disabling Chat upload indexing was rejected because it would make large-file chat unreliable. Automatically treating Chat uploads as Project evidence was rejected because it pollutes trusted research assets and weakens citation auditability.

### If Modifying This Area, Check

- F009 for Project Library asset visibility.
- F010 for Project-scoped retrieval behavior.
- F012 for promotion UI and backend path.
- F013 for route-specific retrieval and whole-paper summary behavior.

## Links

### Evidence

- [EV-005 Session Evidence Boundary Verification](../evidence/EV-005-session-evidence-boundary-verification.md)

### Decisions / ADRs

- [ADR-001 P0 Research Data and Retrieval Stack](../decisions/ADR-001-p0-research-data-and-retrieval-stack.md)

### Lessons

- None yet.

### Specs / Plans

- None yet.

### Related Features

- [F009 Research Project Library Core](F009-research-project-library-core.md)
- [F010 Project Scoped Chat](F010-project-scoped-chat.md)
- [F012 Chat To Library Promotion](F012-chat-to-library-promotion.md)
- [F013 Research Task Router and Whole Paper Summary](F013-research-task-router-whole-paper-summary.md)

### External Context

- ChatGPT / Gemini style file workflows support temporary file processing for a conversation while keeping durable knowledge assets explicit.

## Acceptance Criteria

- [x] Chat-uploaded PDFs are marked and returned as session-scoped temporary evidence.
- [x] Research Library uploads and promotions are marked and returned as project-scoped trusted evidence.
- [x] Unbound sessions do not show “加入研究库”.
- [x] Bound sessions show exactly one “加入研究库” action for eligible temporary papers.
- [x] Project-bound retrieval can use both Project evidence and current-session evidence without hiding their scopes.
- [x] Citations expose whether evidence came from the current session or the Project Library.
- [x] Duplicate upload/promotion failures surface a clear reason for same-name session or Library papers.

## Acceptance Map

| Claim | Acceptance | Evidence | Status |
| --- | --- | --- | --- |
| Chat uploads are temporary by default. | Upload metadata, answer metadata, and UI label use session-scoped wording. | `test_research_session_routes`, frontend contract test, type-check. | Passed |
| Project assets remain explicit. | Only Library upload or promotion writes project-scoped evidence with Project namespace. | `test_upload_research_project_paper_indexes_into_project`, `test_promote_chat_paper_to_library_reuses_library_indexing_path`. | Passed |
| Retrieval scope is visible. | Answer citations include evidence scope metadata and ActivityPanel displays the scope label. | `test_research_retrieval`, `test_research_answering`, frontend contract test. | Passed |

## State Timeline

| Date | State | Trigger | Evidence | Note |
| --- | --- | --- | --- | --- |
| 2026-06-29 | active | User approved F015 recommended design | This Feature | Created to harden the boundary between Chat temporary evidence and Project trusted evidence. |
| 2026-06-29 | completed | First F015 implementation slice | Backend tests, frontend type-check/build, AgentMentor checks | Session and Project evidence scopes are separated and visible. |

## Patch History

| Patch | Date | Commit | Symptom | Root Cause | Protection | Status |
| --- | --- | --- | --- | --- | --- | --- |
| F015.1 | 2026-06-29 | 14972f4 | Chat temporary evidence and Project evidence shared implicit identity/scope behavior. | `paper_id` was not namespaced by session/project scope, and retrieval/citation metadata did not expose the scope. | Scoped paper IDs, retrieval scope SQL, citation metadata, UI labels, and focused/full tests. | verified |

## Evidence

- `$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; $env:TMP='E:\Self-Project\Research-Assistant\.pytest_tmp'; $env:TEMP='E:\Self-Project\Research-Assistant\.pytest_tmp'; pytest ScienceClaw/backend/tests/test_research_ingestion.py ScienceClaw/backend/tests/test_research_retrieval.py ScienceClaw/backend/tests/test_research_answering.py ScienceClaw/backend/tests/test_research_database.py ScienceClaw/backend/tests/test_research_session_routes.py ScienceClaw/backend/tests/test_research_frontend_contracts.py -q --basetemp=.pytest_tmp\f015-focused` -> `123 passed`.
- `$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw;E:\Self-Project\Research-Assistant'; $env:TMP='E:\Self-Project\Research-Assistant\.pytest_tmp'; $env:TEMP='E:\Self-Project\Research-Assistant\.pytest_tmp'; pytest ScienceClaw/backend/tests -q --basetemp=.pytest_tmp\f015-full` -> `188 passed`.
- `npm.cmd run type-check` from `ScienceClaw/frontend` -> passed.
- `npm.cmd run build` from `ScienceClaw/frontend` -> passed with existing Browserslist/CSS/chunk-size warnings.
- `knowledge_check.py --root E:\Self-Project\Research-Assistant --docs-path docs --feature-index F015-session-evidence-boundary` -> errors 0, warnings 0.
- `knowledge_check.py --root E:\Self-Project\Research-Assistant --docs-path docs --strict` -> errors 0, warnings 0.

## Recovery Snapshot

- Read first: this Feature, F009, F010, F012, F013.
- Current capability state: current-session PDF QA remains usable; durable Project RAG remains opt-in through Library upload or explicit promotion.
- Known risks: duplicate detection currently covers same-name session/Library papers; stronger content fingerprint duplicate handling remains future work.
- Next safe action: run a real UI upload/promotion E2E after service restart if visual confirmation is needed.

## Next Step

Optionally run a real UI upload/promotion E2E, then continue to richer summary quality or LLM Router follow-up work.
