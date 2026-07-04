---
id: EV-011
doc_kind: evidence
scope: feature
feature_refs:
  - docs/features/F020-multi-agent-subagent-registry.md
status: accepted
owner: solitudeTG
created: 2026-07-02
updated: 2026-07-02
---

# EV-011: F020 Subagent Registry and Runtime Trace Verification

## Supports Claim

F020 now has a first executable vertical slice for governed Research subagents:

- default `research_auditor` and `paper_reader_worker` definitions exist with prompts, descriptions, allowed tools, boundaries, and validation rules;
- PostgreSQL research storage can persist registry definitions and subagent run records;
- `deep_agent()` passes the governed Research subagents to DeepAgents;
- DeepAgents `task` tool calls can carry real `subagent_lifecycle` metadata through middleware, runner, route mapping, and ActivityPanel display;
- Reader and Auditor outputs are explicitly not citation evidence.

## Verification Scope

Verified backend contract, schema, repository/database wrappers, route mapping, DeepAgents configuration, middleware lifecycle metadata, and frontend TypeScript compatibility.

Not verified here:

- live browser screenshot of ActivityPanel rendering;
- full end-to-end LLM invocation of `task(subagent_type=...)`;
- editable Research Agents registry UI beyond metadata display support.

## Checks

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python -m pytest ScienceClaw\backend\tests\test_research_store_schema.py ScienceClaw\backend\tests\test_research_subagents.py ScienceClaw\backend\tests\test_research_repository.py::test_ensure_subagent_definitions_upserts_governed_defaults ScienceClaw\backend\tests\test_research_repository.py::test_list_subagent_definitions_returns_enabled_registry_rows ScienceClaw\backend\tests\test_research_repository.py::test_persist_subagent_run_records_context_only_boundary ScienceClaw\backend\tests\test_research_database.py::test_subagent_registry_database_wrappers_close_asyncpg_connection ScienceClaw\backend\tests\test_research_tool_runtime.py::test_task_tool_trace_carries_real_subagent_lifecycle_metadata ScienceClaw\backend\tests\test_research_tool_runtime.py::test_deep_agent_registers_governed_research_subagents ScienceClaw\backend\tests\test_research_session_routes.py::test_tool_call_mapping_preserves_subagent_lifecycle_metadata ScienceClaw\backend\tests\test_research_session_routes.py::test_list_research_agents_route_returns_governed_registry -q --basetemp=E:\Self-Project\Research-Assistant\.pytest_tmp
```

Result: `14 passed, 97 warnings`.

```powershell
npm.cmd run type-check
```

Result: `vue-tsc` completed successfully.

```powershell
git diff --check -- ScienceClaw/backend/research_assistant/subagents.py ScienceClaw/backend/research_assistant/storage/schema.sql ScienceClaw/backend/research_assistant/storage/repository.py ScienceClaw/backend/research_assistant/storage/database.py ScienceClaw/backend/deepagent/agent.py ScienceClaw/backend/deepagent/sse_middleware.py ScienceClaw/backend/deepagent/runner.py ScienceClaw/backend/route/sessions.py ScienceClaw/frontend/src/components/ActivityPanel.vue ScienceClaw/frontend/src/types/message.ts ScienceClaw/backend/tests/test_research_subagents.py ScienceClaw/backend/tests/test_research_store_schema.py ScienceClaw/backend/tests/test_research_repository.py ScienceClaw/backend/tests/test_research_database.py ScienceClaw/backend/tests/test_research_tool_runtime.py ScienceClaw/backend/tests/test_research_session_routes.py
```

Result: no whitespace errors; Git reported Windows LF-to-CRLF warnings only.

## Results

Pass.

- Focused backend tests: `14 passed, 97 warnings`.
- Frontend type check: `vue-tsc` completed successfully.
- Diff whitespace check: no whitespace errors; only LF-to-CRLF warnings.

## Artifacts

- `ScienceClaw/backend/research_assistant/subagents.py`
- `ScienceClaw/backend/research_assistant/storage/schema.sql`
- `ScienceClaw/backend/research_assistant/storage/repository.py`
- `ScienceClaw/backend/research_assistant/storage/database.py`
- `ScienceClaw/backend/deepagent/agent.py`
- `ScienceClaw/backend/deepagent/sse_middleware.py`
- `ScienceClaw/backend/deepagent/runner.py`
- `ScienceClaw/backend/route/sessions.py`
- `ScienceClaw/frontend/src/components/ActivityPanel.vue`
- `ScienceClaw/frontend/src/types/message.ts`
- focused backend tests under `ScienceClaw/backend/tests/`

## Limitations

This evidence proves the registry/runtime/trace contract, not the final product surface. The next increment still needs a full Research Agents registry tab and an end-to-end task invocation trace from a real chat session.

## Notes

The deterministic evidence boundary remains the hard floor for Auditor behavior. LLM-backed audit can be added later as a stricter semantic layer, but cannot upgrade invalid deterministic boundary results.
