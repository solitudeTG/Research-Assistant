---
id: EV-012
doc_kind: evidence
scope: feature
feature_refs:
  - docs/features/F020-multi-agent-subagent-registry.md
status: accepted
owner: solitudeTG
created: 2026-07-03
updated: 2026-07-03
---

# EV-012: F020 Research Agents Live UI Verification

## Supports Claim

F020 now has a visible `Research Agents` workbench page for the first governed subagent registry surface.

The page:

- is reachable from the existing ScienceClaw left navigation rail at `/chat/research-agents`;
- lists enabled governed subagents from `/sessions/research/agents`;
- displays `research_auditor` and `paper_reader_worker` with version, enabled state, validation state, descriptions, skills, allowed tools, system prompt, input boundaries, and output boundary;
- shows `citation_evidence=false` and the allowed output boundaries `context_only` and `process_trace`;
- follows the dense ScienceClaw workbench pattern instead of a marketplace or role-store layout.

## Verification Scope

Verified:

- frontend route, API client, navigation entry, and page contract;
- frontend type compatibility;
- F020 focused backend/runtime/trace tests still pass after adding the page;
- live browser desktop interaction from the left navigation rail to the `Research Agents` page;
- live browser Reader row selection and boundary/tool visibility;
- mobile-width render does not introduce horizontal document overflow.

Not verified here:

- editable Registry operations;
- validation example runner;
- recent-run trace previews inside the Registry page;
- full live chat invocation of `task(subagent_type=...)`.

## Checks

Contract test was written before implementation and first failed because `ResearchAgentsPage.vue` did not exist.

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python -m pytest ScienceClaw\backend\tests\test_research_agents_frontend_contract.py -q --basetemp=E:\Self-Project\Research-Assistant\.pytest_tmp
```

Initial result: `1 failed`, expected missing page failure.

Final result: `1 passed`.

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python -m pytest ScienceClaw\backend\tests\test_research_store_schema.py ScienceClaw\backend\tests\test_research_subagents.py ScienceClaw\backend\tests\test_research_repository.py::test_ensure_subagent_definitions_upserts_governed_defaults ScienceClaw\backend\tests\test_research_repository.py::test_list_subagent_definitions_returns_enabled_registry_rows ScienceClaw\backend\tests\test_research_repository.py::test_persist_subagent_run_records_context_only_boundary ScienceClaw\backend\tests\test_research_database.py::test_subagent_registry_database_wrappers_close_asyncpg_connection ScienceClaw\backend\tests\test_research_tool_runtime.py::test_task_tool_trace_carries_real_subagent_lifecycle_metadata ScienceClaw\backend\tests\test_research_tool_runtime.py::test_deep_agent_registers_governed_research_subagents ScienceClaw\backend\tests\test_research_session_routes.py::test_tool_call_mapping_preserves_subagent_lifecycle_metadata ScienceClaw\backend\tests\test_research_session_routes.py::test_list_research_agents_route_returns_governed_registry ScienceClaw\backend\tests\test_research_agents_frontend_contract.py -q --basetemp=E:\Self-Project\Research-Assistant\.pytest_tmp
```

Result: `15 passed, 97 warnings`.

```powershell
npm.cmd run type-check
```

Result: `vue-tsc` completed successfully.

Live UI e2e:

- Vite dev server started on `http://127.0.0.1:5176/`.
- A local read-only mock API served `auth/status`, `sessions`, and `sessions/research/agents`.
- Browser clicked the left rail `Research Agents` button.
- Browser verified URL `http://127.0.0.1:5176/chat/research-agents`.
- Browser verified visible Auditor details: `research_auditor`, `process_trace`, `citation_evidence=false`, `audit_evidence_claims`.
- Browser selected Reader and verified: `paper_reader_worker`, `context_only`, `citation_evidence=false`, `read_research_evidence`, `Can answer user=false`.
- Desktop document overflow check: `documentScrollWidth=1280`, `innerWidth=1280`, `overflowing=false`.
- Mobile document overflow check: `documentScrollWidth=390`, `innerWidth=390`, `overflowing=false`.

## Results

Pass.

The `Research Agents` page is now available as a real governed registry surface. It exposes the current default subagents without inventing a marketplace, fake collaboration, or citation evidence.

## Artifacts

- `ScienceClaw/frontend/src/pages/ResearchAgentsPage.vue`
- `ScienceClaw/frontend/src/api/agent.ts`
- `ScienceClaw/frontend/src/main.ts`
- `ScienceClaw/frontend/src/components/LeftPanel.vue`
- `ScienceClaw/backend/tests/test_research_agents_frontend_contract.py`
- `docs/evidence/EV-012-f020-research-agents-live-ui.png`
- `docs/evidence/EV-012-f020-research-agents-live-ui-mobile.png`

## Limitations

This is a read-only Registry page. Editing, enable/disable persistence, validation examples, version rollback, and recent run previews remain future F020 work. The page intentionally avoids exposing unavailable actions as active controls.

## Notes

The live UI test used a local read-only mock API only to avoid coupling the browser verification to local authentication and PostgreSQL state. Backend route behavior remains covered by focused route and repository tests.
