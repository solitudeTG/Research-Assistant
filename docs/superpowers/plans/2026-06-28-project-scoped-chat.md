# Project Scoped Chat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bind a Chat session to one Research Project and scope research-answer retrieval to that Project when the binding exists.

**Architecture:** Store session-to-Project binding in PostgreSQL research-domain storage via `research_session_projects`. Add route helpers to set/get a session Project, thread optional `project_id` through answering and retrieval, and expose the selected scope in answer trace metadata. Preserve current session-scoped behavior when no Project is bound.

**Tech Stack:** Python/FastAPI/asyncpg/PostgreSQL schema SQL, pytest route/repository/retrieval/answering tests, Vue/TypeScript API additions if UI binding is added in this slice.

---

## Tasks

- [x] Add schema/repository/database tests for `research_session_projects`.
- [x] Implement session Project persistence helpers.
- [x] Add route tests and routes for `PUT/GET /sessions/{session_id}/research/project`.
- [x] Add retrieval/answering tests proving `project_id` scopes search.
- [x] Pass Project scope through `/research/answer` and trace metadata.
- [x] Update F010 evidence and run focused plus full verification.

## Boundaries

- Do not add a General/Research toggle.
- Do not implement evidence admission thresholds; that belongs to F011.
- Do not implement Chat temporary upload promotion; that belongs to F012.
