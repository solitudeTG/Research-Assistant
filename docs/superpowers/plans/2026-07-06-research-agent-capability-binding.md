# Research Agent Capability Binding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let custom Research Agents bind concrete Skills and Tools from the existing Skills Library and Tools Library through ScienceClaw-style selectors, with backend validation and live UI E2E evidence.

**Architecture:** Add a Research Agent capability catalog route that exposes available Skills and concrete Tools, including built-in research subagent tools. Keep the Registry storage model as references (`skill_refs`, `allowed_tools`) and replace raw comma text inputs with searchable multi-select pickers that display invalid references. Enforce binding validity at validation/enable time so chat runtime only receives valid enabled custom subagents.

**Tech Stack:** FastAPI routes in `ScienceClaw/backend/route/sessions.py`, existing Research Assistant subagent models, Vue 3 + TypeScript in `ResearchAgentsPage.vue`, pytest contract tests, frontend `vue-tsc`/build, and browser-driven live UI E2E.

---

### Task 1: Backend Capability Catalog

**Files:**
- Modify: `ScienceClaw/backend/route/sessions.py`
- Test: `ScienceClaw/backend/tests/test_research_session_routes.py`

- [ ] **Step 1: Add failing route tests**

Add tests asserting `/sessions/research/agents/capabilities` returns skills from the Skills Library, external tools from the Tools Library, and built-in research tools `audit_evidence_claims` and `read_research_evidence`.

- [ ] **Step 2: Implement catalog helpers**

Add helper functions in `sessions.py`:

```python
def _research_agent_skill_capabilities(user_id: str) -> list[dict[str, Any]]:
    ...

def _research_agent_tool_capabilities(user_id: str) -> list[dict[str, Any]]:
    ...
```

Use existing skill/tool directory scanning and blocked collections. Mark each item with `name`, `description`, `source`, `blocked`, and `available`.

- [ ] **Step 3: Add route**

Add:

```python
@router.get("/research/agents/capabilities", response_model=ApiResponse)
async def list_research_agent_capabilities_for_user(
    current_user: User = Depends(require_user),
) -> ApiResponse:
    return ApiResponse(data={
        "skills": _research_agent_skill_capabilities(current_user.id),
        "tools": _research_agent_tool_capabilities(current_user.id),
    })
```

- [ ] **Step 4: Run focused tests**

Run:

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python -m pytest ScienceClaw\backend\tests\test_research_session_routes.py -k "research_agent" -q
```

Expected: all selected tests pass.

### Task 2: Backend Binding Validation

**Files:**
- Modify: `ScienceClaw/backend/route/sessions.py`
- Test: `ScienceClaw/backend/tests/test_research_session_routes.py`

- [ ] **Step 1: Add failing validation tests**

Add tests for:

- validation fails when a custom agent references a missing Skill.
- validation fails when a custom agent references a blocked Skill.
- validation fails when a custom agent references a missing Tool.
- validation fails when a custom agent references a blocked Tool.
- enabling a passed custom agent still re-checks Skill/Tool references.

- [ ] **Step 2: Implement binding validation helper**

Add:

```python
def _validate_research_agent_capability_refs(
    definition: Any,
    *,
    user_id: str,
) -> list[str]:
    ...
```

Return concrete error strings. Treat draft saves as allowed; call this helper from validation and enablement paths.

- [ ] **Step 3: Wire validation route**

In `validate_research_agent_for_user`, before publishing passed validation, fail if binding errors exist and include them in the validation result.

- [ ] **Step 4: Wire enablement route**

In `update_research_agent_for_user`, when payload includes `enabled=True`, reject with HTTP 400 if binding errors exist.

- [ ] **Step 5: Run focused tests**

Run:

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python -m pytest ScienceClaw\backend\tests\test_research_session_routes.py -k "research_agent" -q
```

Expected: all selected tests pass.

### Task 3: Frontend API Types

**Files:**
- Modify: `ScienceClaw/frontend/src/api/agent.ts`
- Modify: `ScienceClaw/frontend/src/types/response.ts` if shared response types are needed
- Test: `ScienceClaw/backend/tests/test_research_agents_frontend_contract.py`

- [ ] **Step 1: Add failing frontend contract assertions**

Assert the API exports capability item/result types and `listResearchAgentCapabilities`.

- [ ] **Step 2: Add TypeScript types**

Add:

```ts
export interface ResearchAgentCapabilityItem {
  name: string;
  description: string;
  source: 'builtin_skill' | 'external_skill' | 'research_builtin' | 'external_tool' | string;
  blocked: boolean;
  available: boolean;
  builtin?: boolean;
  file?: string;
  tool_pack?: { id: string; label: string; research_workflow: string };
}

export interface ResearchAgentCapabilities {
  skills: ResearchAgentCapabilityItem[];
  tools: ResearchAgentCapabilityItem[];
}
```

- [ ] **Step 3: Add API client**

Add:

```ts
export async function listResearchAgentCapabilities(): Promise<ResearchAgentCapabilities> {
  const response = await apiClient.get<ApiResponse<ResearchAgentCapabilities>>(
    `/sessions/research/agents/capabilities`,
  );
  return response.data.data;
}
```

### Task 4: Research Agents Binding UI

**Files:**
- Modify: `ScienceClaw/frontend/src/pages/ResearchAgentsPage.vue`
- Test: `ScienceClaw/backend/tests/test_research_agents_frontend_contract.py`

- [ ] **Step 1: Add failing frontend contract assertions**

Assert:

- `listResearchAgentCapabilities` is imported and called.
- The page contains `SkillBindingSelector` and `ToolBindingSelector` markers.
- `skill_refs_text`, `allowed_tools_text`, and raw binding text inputs are absent.
- Invalid binding status labels are present.

- [ ] **Step 2: Replace draft shape**

Change edit draft from text fields to arrays:

```ts
interface AgentEditDraft {
  display_name: string;
  description: string;
  system_prompt: string;
  skill_refs: string[];
  allowed_tools: string[];
}
```

- [ ] **Step 3: Load capability catalog**

Call `listResearchAgentCapabilities()` in `refreshAgents` or a parallel load function. Keep existing agents visible if the catalog fails and set an `capabilityLoadError` message.

- [ ] **Step 4: Add compact selector controls**

Add two ScienceClaw-style sections in `CapabilityAccess`:

- Skill bindings: searchable multi-select from `capabilities.skills`.
- Tool bindings: searchable multi-select from `capabilities.tools`.

Use small checkboxes/chips, compact rows, and status badges. Do not use card-marketplace layout.

- [ ] **Step 5: Show invalid references**

For each selected binding, resolve it against the catalog. Render `missing` or `blocked` chips when a saved reference cannot be used.

- [ ] **Step 6: Save arrays**

Send:

```ts
skill_refs: editDraft.value.skill_refs,
allowed_tools: editDraft.value.allowed_tools,
```

Do not send comma-joined text.

- [ ] **Step 7: Run frontend contract test**

Run:

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python -m pytest ScienceClaw\backend\tests\test_research_agents_frontend_contract.py -q
```

Expected: pass.

### Task 5: Verification And Live UI E2E

**Files:**
- Modify or create: `docs/evidence/EV-020-research-agent-capability-binding-live-ui-e2e.md`
- Use existing dev server and browser tooling

- [ ] **Step 1: Run backend focused tests**

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python -m pytest ScienceClaw\backend\tests\test_research_session_routes.py -k "research_agent" -q
```

- [ ] **Step 2: Run frontend contract tests**

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python -m pytest ScienceClaw\backend\tests\test_research_agents_frontend_contract.py -q
```

- [ ] **Step 3: Run frontend type-check and build**

```powershell
cd ScienceClaw\frontend
npm.cmd run type-check
npm.cmd run build
```

- [ ] **Step 4: Start real dev server**

Start backend/frontend dev servers if not already running. Use an available frontend port and record the URL.

- [ ] **Step 5: Run real browser E2E**

In the live browser:

- Open `/chat/research-agents`.
- Verify the page follows the existing workbench layout.
- Select a custom agent.
- Open edit mode.
- Select at least one Skill from the library.
- Select at least one concrete Tool from the library or built-in research tools.
- Save the draft.
- Validate or enable the agent.
- Verify invalid binding status appears when a binding is missing or blocked, if test setup can safely stage that case.

- [ ] **Step 6: Record Evidence**

Create `docs/evidence/EV-020-research-agent-capability-binding-live-ui-e2e.md` with:

- exact commands
- server URLs
- test results
- screenshot paths if captured
- observed UI behavior
- limitations or residual risk

- [ ] **Step 7: Run AgentMentor knowledge checks**

Run current-feature validation for the owning Feature after Feature page is created or updated:

```powershell
python C:\Users\HUAWEI\.codex\skills\using-agentmentor\scripts\knowledge_check.py --root E:\Self-Project\Research-Assistant --docs-path docs --feature-index docs/features/F021-research-agent-capability-binding.md
```

Expected: pass.
