# Evidence Admission Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic, testable admission layer between retrieval candidates and citation answer context.

**Architecture:** Introduce a small `research_assistant.admission` policy module with centralized thresholds, skip rules, and serializable telemetry. `answer_research_question` will short-circuit obvious non-evidence turns before retrieval, and filter low-score retrieval candidates before composing citations. Session route trace metadata will surface the admission decision.

**Tech Stack:** Python dataclasses, pytest unit/route tests, existing FastAPI answer route and Vue citation metadata path.

---

## Tasks

- [x] Add admission policy tests for skip, accept, and insufficient decisions.
- [x] Implement centralized admission policy module.
- [x] Add answering tests proving skip avoids retrieval and weak hits are not cited.
- [x] Thread admission metadata through answer payload and route trace metadata.
- [x] Update F011 evidence and run verification.

## Boundaries

- Do not implement AI/LLM routing in F011.
- Do not implement a reranker or threshold tuning dashboard.
- Do not change Project scoping from F010.
- Do not add Chat upload promotion; that belongs to F012.
