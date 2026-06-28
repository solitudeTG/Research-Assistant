# Chat To Library Promotion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep Chat uploads temporary by default, and add one explicit "Add to Research Library" action that promotes an eligible uploaded paper into a selected Research Project.

**Architecture:** Add a session route that accepts a sandbox file path plus target `project_id`, verifies the file belongs to the session workspace, copies it into the Library project workspace, and reuses the existing Library ingestion/indexing path with real trace events. Frontend exposes one action on research-answer messages when eligible uploaded paper metadata is present.

**Tech Stack:** FastAPI route, existing ingestion/indexing helpers, pytest route/frontend contract tests, Vue ChatMessage action, agent API wrapper.

---

## Tasks

- [x] Add backend route tests for explicit promotion and workspace boundary checks.
- [x] Implement promotion request/route using Library ingestion/indexing path.
- [x] Add frontend API contract for `promoteChatPaperToLibrary`.
- [x] Add ChatMessage single action contract and emit handler.
- [x] Wire ChatPage handler to choose the current Project and call promotion.
- [x] Update F012 evidence and run verification.

## Boundaries

- Do not auto-promote Chat uploads.
- Do not add multiple first-version promotion actions.
- Do not implement quality review workflow before promotion.
- Do not alter F009 Library management or F010 Project scoping behavior.
