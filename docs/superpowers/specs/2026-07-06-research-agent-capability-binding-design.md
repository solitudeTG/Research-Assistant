---
title: Research Agent Capability Binding Design
date: 2026-07-06
status: approved
owner: solitudeTG
---

# Research Agent Capability Binding Design

## Goal

Make Research Agents bind concrete Skills and Tools from the existing Skills Library and Tools Library, instead of asking users to type raw `skill_refs` and `allowed_tools` strings.

This is not an MVP or temporary shortcut. It is the long-term architecture: libraries own capability content; the Subagent Registry owns references, governance, validation, and runtime eligibility.

## Vision Anchor

- User request: Subagent Registry subagents can already configure Skill and Tool lists; those Skills and Tools should come from the actual Skills Library and Tools Library and support selection from those libraries.
- User constraint: deliver the complete discussed feature, not a reduced MVP, and verify with a real live UI E2E after development.
- UI rule: follow ScienceClaw's workbench UI style: dense, restrained, operational, no marketplace, no landing page, no decorative capability store.
- Project rule: do not let Skill, Tool, or subagent outputs blur citation boundaries. Skill and Tool configuration is process/governance context, not citation evidence.

## Scope

In scope:

- Research Agents edit panel shows Skill and Tool bindings as searchable multi-select controls.
- Skill choices come from the existing Skills Library API.
- Tool choices come from the existing Tools Library API plus the governed built-in research subagent tools:
  - `audit_evidence_claims`
  - `read_research_evidence`
- Saving a custom agent writes the existing Registry fields:
  - `skill_refs: string[]`
  - `allowed_tools: string[]`
- Existing custom agents remain compatible.
- System built-in agents remain read-only.
- Missing, blocked, or unavailable bindings are visible in the UI.
- Enabling or validating a custom agent fails when required bindings are invalid.
- The page remains a ScienceClaw-style governance console.
- Verification includes backend route tests, frontend contract tests, type-check/build, and live UI E2E through the real browser/dev server.

Non-goals:

- Do not create a new unified Capability Registry.
- Do not duplicate Skill or Tool source content into Subagent Registry rows.
- Do not bind Tool Packs. Subagents bind concrete Tool names only.
- Do not create private per-subagent Skills or Tools inside the Research Agents page.
- Do not change chat routing, Supervisor delegation policy, or citation evidence rules.

## Architecture

### Source Of Truth

Skills Library remains the source of truth for skills. Tools Library remains the source of truth for external tools. Research Assistant's built-in subagent tools are exposed as a small read-only built-in tool source because they are valid `allowed_tools` even though they are not files under `Tools/`.

Subagent Registry stores references only. It does not copy Skill or Tool content into the subagent definition. Later governance can add version/hash snapshots inside `metadata.binding_snapshot`, but the primary runtime model stays reference-based.

### Backend

Add a Research Agent capability catalog route:

```text
GET /sessions/research/agents/capabilities
```

Response:

```json
{
  "skills": [
    {
      "name": "deep-research",
      "description": "Research workflow skill",
      "blocked": false,
      "builtin": false,
      "available": true
    }
  ],
  "tools": [
    {
      "name": "audit_evidence_claims",
      "description": "Audit draft claims against citation evidence.",
      "source": "research_builtin",
      "blocked": false,
      "available": true
    }
  ]
}
```

The route reuses existing discovery logic where possible:

- Skills from `/app/builtin_skills` and `/app/Skills`, applying per-user blocked state.
- External Tools from `/app/Tools`, applying per-user blocked state.
- Built-in research tools from the existing `_RESEARCH_SUBAGENT_TOOLS` mapping.

Validation rules:

- `skill_refs` must reference existing, unblocked skills when a custom agent is validated or enabled.
- `allowed_tools` must reference existing, unblocked tools or built-in research tools when a custom agent is validated or enabled.
- Editing and saving a draft may keep invalid references visible so users can repair them.
- Enabling invalid references must fail with an actionable error.
- System built-in agents are still not editable.

### Frontend

Research Agents page loads the capability catalog with the agent list. In the custom-agent edit panel:

- Replace raw text inputs for `skill_refs_text` and `allowed_tools_text` with compact searchable multi-select pickers.
- Show selected bindings as dense chips with source/status.
- Show missing or blocked bindings as invalid chips.
- Keep the same save, validate, and enable workflow.
- Do not introduce cards, hero areas, decorative marketplace language, or a separate visual system.

The UI should remain a governance console:

- Left rail: registered agents.
- Main panel: selected custom agent details and binding controls.
- Side panel: validation and recent runs.

## Data Flow

1. User opens Research Agents.
2. Frontend calls `listResearchAgents()` and `listResearchAgentCapabilities()`.
3. User selects a custom agent.
4. Edit panel resolves the agent's `skill_refs` and `allowed_tools` against the capability catalog.
5. User selects Skills/Tools from searchable lists.
6. Saving sends `skill_refs` and `allowed_tools` arrays through the existing update route.
7. Validation and enablement re-check references server-side.
8. Chat runtime continues to load enabled custom subagents from Registry and build DeepAgents configs from concrete `allowed_tools`.

## Error Handling

- Catalog load failure does not hide existing agent definitions; it shows binding controls as unavailable and blocks saving edited bindings.
- Missing bindings remain visible with `missing` status.
- Blocked bindings remain visible with `blocked` status.
- Enabling a custom agent with invalid bindings returns HTTP 400 with a specific message.
- Validation returns `failed` with errors that name invalid Skill/Tool refs.

## Acceptance Criteria

- [ ] Custom Research Agents bind Skills via a selector sourced from Skills Library.
- [ ] Custom Research Agents bind concrete Tools via a selector sourced from Tools Library plus built-in research tools.
- [ ] Raw comma-separated Skill/Tool text inputs are removed from the normal custom-agent edit path.
- [ ] Existing `skill_refs` and `allowed_tools` persistence remains compatible.
- [ ] Missing and blocked Skill/Tool references are visible in the UI.
- [ ] Validation fails for invalid Skill/Tool bindings.
- [ ] Enabling fails for invalid Skill/Tool bindings.
- [ ] System built-in agents stay read-only.
- [ ] UI remains ScienceClaw-style dense workbench UI, not a marketplace.
- [ ] Backend route tests cover capability catalog and invalid binding validation.
- [ ] Frontend contract tests cover selector UI and absence of raw binding text inputs.
- [ ] Frontend type-check and build pass.
- [ ] Real live UI E2E verifies loading capabilities, selecting Skill/Tool bindings, saving, validating/enabling, and blocked/missing status visibility.

## Recovery Notes

If future agents need to resume:

- Start from `ScienceClaw/backend/route/sessions.py` for Research Agent routes and capability discovery.
- Start from `ScienceClaw/frontend/src/pages/ResearchAgentsPage.vue` for the binding UI.
- Keep `SubagentDefinition.skill_refs` and `SubagentDefinition.allowed_tools` as arrays of stable references.
- Do not replace this with a capability marketplace unless a separate Feature and ADR justify the scope expansion.
