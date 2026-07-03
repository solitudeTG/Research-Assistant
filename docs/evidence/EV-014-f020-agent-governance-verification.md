---
id: EV-014
doc_kind: evidence
scope: feature
feature_refs:
  - docs/features/F020-multi-agent-subagent-registry.md
status: accepted
owner: solitudeTG
created: 2026-07-03
updated: 2026-07-03
---

# EV-014: F020 Agent Governance Verification

## Supports Claim

F020.1 到 F020.5 已形成可验证能力增量：

- Registry 区分 `system_builtin` 与 `custom`，并将 `general-purpose` 作为只读系统内置 Agent 显性展示。
- Supervisor prompt 明确按任务复杂度自主委派 Reader/Auditor，但不把简单问答强制多 Agent。
- Subagent lifecycle metadata 包含稳定身份、类型、来源、parent/workflow、boundary 与 citation flag。
- Reader/Auditor 结果收敛到 minimal envelope：`status`、`agent`、`boundary`、`citation_evidence`、`content`、`metadata`。
- Research Agents 页面展示 recent-run preview，并可对 custom agents 运行 validation example。

## Verification Scope

Verified:

- Backend subagent registry contracts.
- Storage schema/repository behavior for definitions and recent runs.
- Route contracts for registry listing, recent-run preview, and validation examples.
- DeepAgents Supervisor prompt contract and runtime subagent registration.
- Lifecycle metadata normalization and persistence helper.
- Minimal result envelope for Reader/Auditor tools.
- Frontend API contract and Research Agents page rendering.
- Live browser Research Agents UI journey with a temporary local API.

Not verified:

- Real backend chat multi-agent E2E in this run, because the local environment could not import the backend app without `motor`.
- Production database migration against a live PostgreSQL instance.

## Checks

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python -m pytest ScienceClaw\backend\tests\test_research_subagents.py ScienceClaw\backend\tests\test_research_repository.py::test_ensure_subagent_definitions_upserts_governed_defaults ScienceClaw\backend\tests\test_research_repository.py::test_list_subagent_definitions_returns_enabled_registry_rows ScienceClaw\backend\tests\test_research_repository.py::test_persist_subagent_run_records_context_only_boundary ScienceClaw\backend\tests\test_research_repository.py::test_list_recent_subagent_runs_returns_preview_rows ScienceClaw\backend\tests\test_research_store_schema.py ScienceClaw\backend\tests\test_research_session_routes.py::test_list_research_agents_route_returns_governed_registry ScienceClaw\backend\tests\test_research_session_routes.py::test_list_research_agent_runs_route_returns_recent_preview ScienceClaw\backend\tests\test_research_session_routes.py::test_validate_research_agent_route_runs_custom_validation_example ScienceClaw\backend\tests\test_research_tool_runtime.py ScienceClaw\backend\tests\test_research_agents_frontend_contract.py -q --basetemp=E:\Self-Project\Research-Assistant\.pytest_tmp_final
```

Result: `31 passed, 201 warnings`.

```powershell
npm.cmd run type-check
```

Result: `vue-tsc` completed successfully.

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python -c "import backend.main as m; print('backend-main-import-ok')"
```

Result: failed with `ModuleNotFoundError: No module named 'motor'`.

## Results

Pass with one environment limitation.

- Focused backend tests: `31 passed, 201 warnings`.
- Frontend type check: `vue-tsc` completed successfully.
- Research Agents live UI E2E completed in the in-app browser.
- Real backend chat E2E was not rerun because backend import is blocked by missing local dependency `motor`.

Live UI validated:

1. Opened `http://127.0.0.1:5189/chat/research-agents`.
2. Confirmed Chinese UI text `研究智能体`.
3. Confirmed Registry type split:
   - `general-purpose`: `系统内置`, `只读`, `system_builtin`, `deepagents_builtin`, `citation_evidence=false`.
   - `research_auditor` and `paper_reader_worker`: `用户自定义`, `可编辑`.
4. Selected `阅读 Worker`.
5. Confirmed recent-run preview: `task-reader-1`, `completed`, `context_only`, `citation_evidence=false`.
6. Clicked `运行验证`.
7. Confirmed validation example: `status=passed`, `definition_contract`, `minimal_envelope`, `citation_evidence_false`, `agent=paper_reader_worker`, `boundary=context_only`, `citation_evidence=false`, `status=completed`.

## Artifacts

- `ScienceClaw/backend/research_assistant/subagents.py`
- `ScienceClaw/backend/research_assistant/storage/schema.sql`
- `ScienceClaw/backend/research_assistant/storage/repository.py`
- `ScienceClaw/backend/research_assistant/storage/database.py`
- `ScienceClaw/backend/deepagent/agent.py`
- `ScienceClaw/backend/deepagent/sse_middleware.py`
- `ScienceClaw/backend/deepagent/runner.py`
- `ScienceClaw/backend/route/sessions.py`
- `ScienceClaw/frontend/src/api/agent.ts`
- `ScienceClaw/frontend/src/pages/ResearchAgentsPage.vue`
- Focused tests under `ScienceClaw/backend/tests/`

## Limitations

The Research Agents UI E2E used a temporary local API because importing the real backend app in this environment fails with missing `motor`. No fake chat multi-agent trace was used. The complex chat multi-agent journey should be rerun against a fully provisioned backend environment with MongoDB dependencies available.

## Notes

- The temporary UI/mock services were stopped after validation.
- Existing untracked `paper_data/` was left untouched.
