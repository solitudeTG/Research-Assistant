---
id: EV-020
doc_kind: evidence
feature: F021
feature_refs:
  - docs/features/F021-research-agent-capability-binding.md
scope: Research Agent capability binding live UI E2E
created: 2026-07-06
updated: 2026-07-06
---

# EV-020: Research Agent Capability Binding Live UI E2E

## Supports Claim

验证 F021 的完整能力闭环：

- Research Agents 页面从真实后端读取 Subagent Registry。
- 页面从真实后端读取 Skills Library / Tools Library capability catalog。
- Custom Research Agent 通过 UI 选择具体 Skill 和具体 Tool。
- 保存动作发出真实 `PATCH /api/v1/sessions/research/agents/{agent_name}`。
- UI 保持 ScienceClaw 高密度工作台风格。

## Verification Scope

Scope includes the Research Agents management page, backend capability catalog route, custom-agent binding validation path, and live browser workflow against the running backend.

Out of scope: changing Supervisor delegation policy, changing `active_tool_packs`, or proving runtime invocation of a newly bound custom agent inside chat.

## Live Environment

- Frontend: production `dist` served through a temporary same-origin static proxy at `http://127.0.0.1:4176`.
- Backend: running Docker service `research-assistant-backend-1`, exposed at `http://127.0.0.1:12001`.
- Auth: local admin login through the real login page.
- Test helper: `.pytest_tmp/f021_static_proxy.py` only served static files and proxied `/api` to the real backend to avoid CORS mismatch on an ad-hoc preview port.

## Checks

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'
python -m pytest ScienceClaw\backend\tests\test_research_session_routes.py -k "research_agent" -q --basetemp .pytest_tmp\f021-research-agent-route-2
python -m pytest ScienceClaw\backend\tests\test_research_agents_frontend_contract.py -q --basetemp .pytest_tmp\f021-frontend-contract-2

cd ScienceClaw\frontend
npm.cmd run type-check
npm.cmd run build

cd E:\Self-Project\Research-Assistant
python .pytest_tmp\f021_live_ui_e2e.py
```

## Results

- Backend focused route tests: `12 passed, 52 deselected`.
- Frontend contract test: `1 passed`.
- TypeScript check: passed.
- Frontend production build: passed, with existing CSS/chunk warnings.
- Live UI E2E: passed.

## Artifacts

The E2E summary recorded:

- `GET /api/v1/sessions/research/agents` returned `200`.
- `GET /api/v1/sessions/research/agents/capabilities` returned `200`.
- `SkillBindingSelector` was present.
- `ToolBindingSelector` was present.
- `research-paper-reading` was visible from the skill catalog.
- `read_research_evidence` was visible from the concrete tool catalog.
- `PATCH /api/v1/sessions/research/agents/f021_methods_mapper_live` returned `200`.
- Browser console contained no errors from the tested page flow.

Artifacts:

- Screenshot: `docs/evidence/EV-020-research-agent-capability-binding-live-ui-e2e.png`
- Request summary: `docs/evidence/EV-020-research-agent-capability-binding-live-ui-e2e-summary.json`

## Limitations

- The live E2E used an existing F021 test agent (`f021_methods_mapper_live`) rather than creating a brand-new agent through UI, because this feature changes binding of existing custom agents.
- The test proxy was a same-origin harness helper for serving production `dist` against the real backend; it did not mock `/api` responses.
- Runtime use of bound subagent capabilities during Supervisor chat delegation was out of scope for EV-020 and is covered by EV-021.

## Notes

The E2E used an existing F021 test agent (`f021_methods_mapper_live`) and saved a real binding update through the UI. The screenshot intentionally shows a missing legacy binding (`research-method-mapping`) as a UI warning, proving the page surfaces unresolved references instead of silently accepting them.
