---
id: EV-019
doc_kind: evidence
feature: F020
status: valid
scope: feature
feature_refs:
  - docs/features/F020-multi-agent-subagent-registry.md
created: 2026-07-06
owner: solitudeTG
---

# EV-019: F020 Research Agents Online Update UI E2E

## Supports Claim

Research Agents now supports a governed online custom-subagent update flow in the ScienceClaw workbench style:

- Custom agents can be edited as drafts.
- Content edits reset validation to `draft` and cannot stay implicitly enabled.
- Passed custom agents can be published/enabled.
- Enabled custom agents can be disabled and republished.
- System built-in agents remain visible but read-only.
- The page avoids the ambiguous `启停` action and uses explicit `发布启用` / `停用`.

## Verification Scope

- Backend route/repository contract for enabling custom agents only after passed validation.
- Frontend contract for explicit publish/disable controls and no hardcoded `enabled: false` save payload.
- Type-check and production build for the Vue app.
- Real live UI E2E against a running backend, MongoDB, Vite dev server, and Chrome.

## Checks

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'
python -m pytest ScienceClaw\backend\tests\test_research_session_routes.py -k "research_agent_route" -q
python -m pytest ScienceClaw\backend\tests\test_research_agents_frontend_contract.py -q
python -m pytest ScienceClaw\backend\tests\test_research_repository.py -k "subagent_definition or validation_status" -q
cd ScienceClaw\frontend
npm.cmd run type-check
npm.cmd run build
```

Live UI:

- Backend: `http://127.0.0.1:12003/api/v1`, current code via `uvicorn backend.main:app`.
- Frontend: `http://127.0.0.1:5179/index.html`, current frontend via Vite with `BACKEND_URL=http://127.0.0.1:12003`.
- Browser: Playwright with system Chrome at `C:\Program Files\Google\Chrome\Application\chrome.exe`.

## Results

- `test_research_session_routes.py -k "research_agent_route"`: 7 passed.
- `test_research_agents_frontend_contract.py`: 1 passed.
- `test_research_repository.py -k "subagent_definition or validation_status"`: 7 passed.
- `npm.cmd run type-check`: passed.
- `npm.cmd run build`: passed; existing Browserslist/CSS minify/chunk-size warnings remained.
- Live UI E2E: passed.

Live UI E2E exercised:

1. Register a real user through the running backend.
2. Open the live Research Agents page in Chrome.
3. Select `research_auditor`.
4. Edit description and save draft.
5. Assert validation state becomes `草稿`.
6. Run validation and assert `已通过` plus `已启用`.
7. Click exact `停用` and assert `已停用`.
8. Click exact `发布启用` and assert `已启用`.
9. Select `general-purpose` and assert system built-in read-only text and disabled edit action.
10. Assert page includes `citation_evidence=false`, includes `发布启用`, and does not include ambiguous `启停`.

## Artifacts

- Backend route: `ScienceClaw/backend/route/sessions.py`
- Registry repository: `ScienceClaw/backend/research_assistant/storage/repository.py`
- Frontend page: `ScienceClaw/frontend/src/pages/ResearchAgentsPage.vue`
- Backend route tests: `ScienceClaw/backend/tests/test_research_session_routes.py`
- Frontend contract test: `ScienceClaw/backend/tests/test_research_agents_frontend_contract.py`
- This Evidence record: `docs/evidence/EV-019-f020-research-agents-online-update-ui-e2e.md`

## 2026-07-06 UI Simplification Refinement

User-reviewed design consensus after the first EV-019 run:

- Research Agents should be a governed authoring console, not a raw Registry row editor.
- The page should have two user-facing layers: base information and behavior/permission controls.
- Unified input/output schema is a system protocol and should not be edited in the page.
- `output_boundary` should not be user-selected; subagent output becomes final answer or artifact only when Supervisor accepts it.
- Recent runs can stay in the right column but should be collapsed by default.

Additional checks after the refinement:

- Frontend contract test requires `BaseInfo`, `CapabilityAccess`, and `RecentRunsCollapsed` markers.
- Frontend contract test rejects visible/raw editor fields: `input_boundaries_text`, `metadata_text`, `formattedGovernance`, `editDraft.output_boundary`, `Input boundaries JSON`, `Metadata JSON`, and `输出边界`.
- Live UI E2E verified the simplified page renders `基础信息`, `行为与权限`, `统一输入输出协议`, hides raw schema fields, keeps `最近运行` collapsed by default, and preserves system built-in read-only behavior.
- Live UI E2E also verified the governed update flow still works: save draft, run validation, disable, republish.

Additional results:

- `test_research_agents_frontend_contract.py`: 1 passed.
- `npm.cmd run type-check`: passed.
- Live UI smoke/E2E against `http://127.0.0.1:5179/index.html` and backend `http://127.0.0.1:12003/api/v1`: passed.

## 2026-07-06 Control Surface Refinement

User review of the simplified UI found another layer of unnecessary visibility:

- The protocol summary line did not help users configure an Agent.
- Separate `运行验证`, `发布启用`, and `停用` actions made the workflow feel like internal state management.
- `回滚` was misleading without a real version picker and K-version history UI.
- The right validation/run column should start hidden so the default page is the left registry list plus the main editor.

Changes verified in live UI:

- Removed the protocol summary row from the visible editor.
- Removed the standalone validation action.
- Merged publish/enable and pause into one `启动` / `暂停` toggle.
- `启动` now runs validation automatically when the Agent is not already `passed`.
- Removed the rollback action from the page.
- Kept `重置` only as local form reset for unsaved draft changes.
- Collapsed the entire validation/recent-run side panel by default behind `查看验证与运行`.

Additional live UI E2E assertions:

- Initial page did not contain protocol summary text, standalone validation action, separate publish/disable labels, or rollback.
- Initial page hid `验证结果` and `最近运行`.
- Saving a draft set the publish state to `草稿`.
- Clicking `启动` from draft ran validation and enabled the Agent.
- Clicking `暂停` used the same toggle path and moved the Agent to paused state.
- Clicking `查看验证与运行` opened the right panel on demand.

## Limitations

- The Vite dev server used in this environment returns 404 for `/` and `/chat/research-agents`; the E2E opens `/index.html` first and then navigates into the router. This causes a Vue Router warning for `/index.html`, but the governed subagent workflow itself passes.
- The live UI run observed a page-level `Cannot use 'import.meta' outside a module` warning in the test environment. It did not block route rendering, API calls, draft save, validation, disable, republish, or read-only assertions.

## Notes

This evidence covers the July 6, 2026 follow-up that the earlier page still did not feel like ScienceClaw UI and did not provide a clear online update path for custom subagents.
