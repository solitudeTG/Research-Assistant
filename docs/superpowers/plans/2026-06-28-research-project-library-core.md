# Research Project Library Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first F009 vertical slice: Research Projects and a ScienceClaw-styled Research Library page that can list project paper assets and upload papers into a selected Project.

**Architecture:** Add a Project table and optional paper `project_id` association to the existing PostgreSQL research-domain schema. Keep repository/database helpers focused on project and project-paper list operations, expose small `/sessions/research/projects` endpoints through the existing sessions router, and add a dense workbench page under the existing MainLayout route.

**Tech Stack:** Python/FastAPI/asyncpg for backend APIs, PostgreSQL schema SQL for research storage, pytest for backend tests, Vue 3/TypeScript/Tailwind-style existing CSS utilities for frontend.

---

## File Structure

- Modify `ScienceClaw/backend/research_assistant/storage/schema.sql`
  - Add `research_projects`.
  - Add nullable `project_id` to `research_papers` with an index.
- Modify `ScienceClaw/backend/research_assistant/storage/repository.py`
  - Add `ResearchProject` and `ResearchProjectPaperAsset` dataclasses.
  - Add `create_research_project`, `list_research_projects`, `list_project_paper_assets`.
  - Add optional `project_id` support to ingestion persistence.
- Modify `ScienceClaw/backend/research_assistant/storage/database.py`
  - Add asyncpg wrapper functions for the repository helpers.
- Modify `ScienceClaw/backend/route/sessions.py`
  - Add request models for project creation.
  - Add routes for creating/listing projects and listing project paper assets.
  - Keep session chat/RAG behavior unchanged in F009.
- Modify `ScienceClaw/frontend/src/api/agent.ts`
  - Add Research Project and Project Paper API types/functions.
- Modify `ScienceClaw/frontend/src/main.ts`
  - Add `/chat/research-library` route inside `MainLayout`.
- Create `ScienceClaw/frontend/src/pages/ResearchLibraryPage.vue`
  - Dense two-column layout: project list and current Project paper table/upload action.
- Test files:
  - Modify `ScienceClaw/backend/tests/test_research_store_schema.py`.
  - Modify `ScienceClaw/backend/tests/test_research_repository.py`.
  - Modify `ScienceClaw/backend/tests/test_research_session_routes.py`.
  - Add/extend frontend contract test if current pattern supports static API checks.

## Task 1: Backend Project Schema And Repository Contract

**Files:**
- Modify: `ScienceClaw/backend/research_assistant/storage/schema.sql`
- Modify: `ScienceClaw/backend/research_assistant/storage/repository.py`
- Test: `ScienceClaw/backend/tests/test_research_store_schema.py`
- Test: `ScienceClaw/backend/tests/test_research_repository.py`

- [ ] **Step 1: Write failing schema test**

Add assertions that the schema contains `research_projects`, `project_id` on `research_papers`, and a `research_papers_project_id_idx`.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ScienceClaw/backend; pytest tests/test_research_store_schema.py -q`
Expected: FAIL because `research_projects` and `project_id` are missing.

- [ ] **Step 3: Write failing repository tests**

Add tests using `RecordingConnection` for:
- `create_research_project` inserts/returns a project.
- `list_research_projects` reads projects by user.
- `list_project_paper_assets` reads only papers for one project and returns chunk/evidence counts.

- [ ] **Step 4: Run repository tests to verify they fail**

Run: `cd ScienceClaw/backend; pytest tests/test_research_repository.py -q`
Expected: FAIL with missing repository functions/classes.

- [ ] **Step 5: Implement schema and repository helpers**

Add minimal schema and repository code to satisfy the tests. Do not alter retrieval behavior yet.

- [ ] **Step 6: Run focused tests**

Run:
`cd ScienceClaw/backend; pytest tests/test_research_store_schema.py tests/test_research_repository.py -q`
Expected: PASS.

## Task 2: Backend Database Wrappers And Routes

**Files:**
- Modify: `ScienceClaw/backend/research_assistant/storage/database.py`
- Modify: `ScienceClaw/backend/route/sessions.py`
- Test: `ScienceClaw/backend/tests/test_research_session_routes.py`

- [ ] **Step 1: Write failing route tests**

Add tests that load the sessions module and monkeypatch database wrappers to verify:
- `create_research_project_for_user` calls `create_research_project_in_database`.
- `list_research_projects_for_user` returns project dicts.
- `list_research_project_papers_for_user` returns Project-scoped paper rows.

- [ ] **Step 2: Run route tests to verify they fail**

Run: `cd ScienceClaw/backend; pytest tests/test_research_session_routes.py -q`
Expected: FAIL because route functions/wrappers are missing.

- [ ] **Step 3: Implement wrappers and route functions**

Add wrappers in `database.py`, imports in `sessions.py`, request model, and route handlers. Keep upload/index route changes minimal; use Project paper listing first.

- [ ] **Step 4: Run focused route tests**

Run: `cd ScienceClaw/backend; pytest tests/test_research_session_routes.py -q`
Expected: PASS.

## Task 3: Frontend API And Library Page Shell

**Files:**
- Modify: `ScienceClaw/frontend/src/api/agent.ts`
- Modify: `ScienceClaw/frontend/src/main.ts`
- Create: `ScienceClaw/frontend/src/pages/ResearchLibraryPage.vue`

- [ ] **Step 1: Add TypeScript API types/functions**

Add project and project-paper interfaces plus `createResearchProject`, `listResearchProjects`, and `listResearchProjectPapers`.

- [ ] **Step 2: Add Research Library route**

Import `ResearchLibraryPage` and add `/chat/research-library` under `MainLayout`.

- [ ] **Step 3: Build page shell**

Create a dense workbench page with:
- Project list.
- New project form.
- Selected Project metadata.
- Paper asset table with indexing/citation readiness columns.
- Upload control placeholder wired to the selected Project only if backend upload endpoint is available in this slice.

- [ ] **Step 4: Run frontend type check**

Run: `cd ScienceClaw/frontend; npm run type-check`
Expected: PASS. If the project uses `vue-tsc` directly instead, run the existing script shown by `npm pkg get scripts`.

## Task 4: F009 Documentation, Verification, Commit, Push

**Files:**
- Modify: `docs/features/F009-research-project-library-core.md`

- [ ] **Step 1: Update F009 Acceptance Map**

Mark implemented claims with verification commands and limitations.

- [ ] **Step 2: Run verification**

Run focused backend tests, frontend type check/build if UI changed, and AgentMentor knowledge check:
`python C:\Users\HUAWEI\.codex\skills\using-agentmentor\scripts\knowledge_check.py --root E:\Self-Project\Research-Assistant --docs-path docs --feature-index docs/features/F009-research-project-library-core.md`

- [ ] **Step 3: Commit and push**

Confirm git identity is `solitudeTG`, stage only relevant files, commit one F009 implementation batch, and push `master`.

## Self-Review

- Spec coverage: F009 covers Project/Library data model, Library UI, Project paper visibility, and upload boundary. F010-F012 are explicitly excluded.
- Placeholder scan: The plan avoids TODO/TBD placeholders. Upload wiring is conditional only because existing upload path must be inspected during implementation; if not implemented in F009 batch, F009 Acceptance Map must mark that limitation.
- Type consistency: Project types should use `project_id`, `name`, `description`, `paper_count`, `chunk_count`, `created_at`, and `updated_at` consistently across backend/frontend.
