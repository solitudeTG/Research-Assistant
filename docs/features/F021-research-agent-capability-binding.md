---
id: F021
doc_kind: feature
status: verified
owner: solitudeTG
created: 2026-07-06
updated: 2026-07-06
---

# F021: Research Agent Capability Binding

## Goal

让 Research Agents 中的 custom subagent 从现有 Skills Library 和 Tools Library 选择绑定具体 Skill 与具体 Tool，替代手填 `skill_refs` / `allowed_tools` 字符串，并在验证、启用和真实 UI 中保证引用有效。

## Vision Anchor

- Source: 用户在 2026-07-06 明确确认 Subagent Registry 中的 Skill / Tool 来源应是 Skills Library 和 Tools Library，并支持从库中选择绑定。
- User pain point: 当前 Research Agents 编辑面板让用户手填 Skill 和 Tool 引用，容易拼写错误、引用已删除或被禁用的能力，也不能体现能力库是系统真实来源。
- Desired outcome: Subagent Registry 成为编排与治理层，只保存引用和验证状态；Skills Library / Tools Library 成为能力来源；Chat runtime 只装配已启用且引用有效的 custom subagent。
- Non-goals: 不做统一 Capability Marketplace；不复制 Skill/Tool 内容到 subagent；不绑定 Tool Pack；不改变 Supervisor 调度策略；不改变 citation evidence boundary。
- Exit Gate source: 本 Feature、linked design spec、implementation plan、EV-020 live UI E2E Evidence、后端/前端测试。

## Feature Intake

- Original problem: Custom Research Agents already have `skill_refs` and `allowed_tools`, but the authoring UI does not bind them from the actual capability libraries.
- User pain point: 手填引用无法防止无效能力进入 subagent 配置，且让 Subagent Registry 看起来像另一套孤立能力系统。
- Capability promise: 在 Research Agents 页面中使用 ScienceClaw 风格的紧凑选择器，从 Skills Library 和 Tools Library 绑定具体 Skill/Tool，并在验证和启用前检查引用有效性。
- Non-goals: 不新增私有 subagent Skill/Tool；不让 subagent 直接面向用户；不把 Skill/Tool 输出伪装为 citation evidence；不做 card-heavy marketplace。
- Acceptance source: 用户确认“绑定具体 Tool 即可”“方案 A 是长期方案”“UI 遵从 ScienceClaw”“开发完做真实 live UI E2E”。
- Open questions: 外置 Tool 被保存但未启用 Tool Pack 时是否影响 subagent 运行时可见性；第一版采用 subagent `allowed_tools` 直接授权，不通过 chat `active_tool_packs`。

## Capability Contract

- Inputs: Existing custom subagent definitions, Skills Library entries, Tools Library entries, and built-in research subagent tools.
- Processing: Resolve selected Skill/Tool references into stable arrays and validate missing/blocked/unavailable references before validation or enablement.
- Storage: Preserve existing `skill_refs: string[]` and `allowed_tools: string[]` fields in Subagent Registry.
- Outputs: Updated custom subagent definitions, UI-visible binding status, validation errors for invalid bindings, and live UI Evidence.
- Evidence boundary: Skill/Tool bindings are configuration/process context. They are not citation evidence.

## Decision Context

- Accepted model: Subagent Registry stores references only; Skills Library and Tools Library remain the capability source of truth.
- Tool binding granularity: bind concrete tools through `allowed_tools`, not tool packs.
- UI model: keep the Research Agents page as a dense ScienceClaw governance console; do not introduce a marketplace or landing page.
- Validation model: validation and enablement must reject missing, blocked, or unavailable references before a custom agent can be published or enabled.
- Rejected path: copying Skill/Tool content into subagent definitions was rejected because it would fork the source of truth and make library governance ineffective.
- Rejected path: binding only Tool Packs was rejected because the user explicitly chose concrete Tool binding and because packs are chat-turn activation context, not subagent authorization.

## Current Status

Verified. Backend catalog and validation, frontend Skill/Tool selectors, runtime consumption of bound subagent tools, focused tests, production build, live UI E2E, and live chat runtime E2E are complete.

## State Timeline

- 2026-07-06: User confirmed long-term reference-binding model and ScienceClaw UI constraint.
- 2026-07-06: Feature, design spec, and implementation plan created.
- 2026-07-06: Backend catalog and binding validation implemented.
- 2026-07-06: Frontend Skill/Tool selectors implemented and raw comma text inputs removed.
- 2026-07-06: Focused tests, type-check, build, and live UI E2E passed.
- 2026-07-06: Chat runtime Tool-binding consumption verified with associate/cancel live UI E2E.

## Links

### Evidence

- [EV-020 Research Agent Capability Binding Live UI E2E](../evidence/EV-020-research-agent-capability-binding-live-ui-e2e.md)
- [EV-021 Research Agent Tool Binding Chat Runtime E2E](../evidence/EV-021-research-agent-tool-binding-chat-runtime-e2e.md)

### Decisions / ADRs

- None.

### Lessons

- None.

### Specs / Plans

- [Research Agent Capability Binding Design](../superpowers/specs/2026-07-06-research-agent-capability-binding-design.md)
- [Research Agent Capability Binding Implementation Plan](../superpowers/plans/2026-07-06-research-agent-capability-binding.md)

### Related Features

- [F001 Project Vision and Scope](F001-project-vision-and-scope.md)
- [F002 ScienceClaw Baseline Workbench Shell](F002-scienceclaw-baseline-workbench-shell.md)
- [F008 Trace Honesty and Activity Panel](F008-trace-honesty-activity-panel.md)
- [F020 Multi-Agent Research Workflow and Subagent Registry](F020-multi-agent-subagent-registry.md)

### External Context

- None.

## Acceptance Criteria

- [x] Research Agents custom-agent edit UI binds Skills through a selector sourced from Skills Library.
- [x] Research Agents custom-agent edit UI binds concrete Tools through a selector sourced from Tools Library plus built-in research tools.
- [x] Raw comma-separated Skill/Tool text inputs are removed from the normal edit path.
- [x] Existing persisted `skill_refs` and `allowed_tools` remain compatible.
- [x] Missing or blocked Skill/Tool references are visible in the UI.
- [x] Validation fails for invalid Skill/Tool references.
- [x] Enabling fails for invalid Skill/Tool references.
- [x] System built-in agents remain read-only.
- [x] UI follows ScienceClaw's dense workbench style and does not become a marketplace.
- [x] Backend focused tests pass.
- [x] Frontend contract tests, type-check, and build pass.
- [x] Real live UI E2E verifies the binding workflow.
- [x] Real live UI E2E verifies associating and cancelling a Tool binding changes chat runtime subagent tools on the next chat turn.

## Acceptance Map

| Claim | Acceptance | Evidence | Status |
| --- | --- | --- | --- |
| Skill bindings come from the Skills Library. | UI selector and backend catalog expose real skills and save stable `skill_refs`. | EV-020 and focused tests. | Verified |
| Tool bindings come from concrete Tools. | UI selector and backend catalog expose external tools plus built-in research tools and save stable `allowed_tools`. | EV-020 and focused tests. | Verified |
| Invalid bindings cannot be enabled. | Backend validation and enablement reject missing/blocked references. | Focused route tests. | Verified |
| UI inherits ScienceClaw. | Page remains high-density console with existing left rail/main/side panel structure. | Frontend contract and live screenshot evidence. | Verified |
| Tool binding changes affect chat runtime immediately. | A Tool associated with `paper_reader_worker` appears in the next chat runtime subagent snapshot; after cancellation it disappears in the next chat runtime snapshot. | EV-021 and focused runtime tests. | Verified |

## Patch History

| Patch | Date | Commit | Symptom | Root Cause | Protection | Status |
| --- | --- | --- | --- | --- | --- | --- |
| F021.1 | 2026-07-06 | pending | Live UI E2E did not prove chat runtime effect of Tool associate/cancel. | EV-020 verified the Research Agents page save path but explicitly left runtime consumption out of scope. | Added subagent runtime available-tool assembly for explicitly bound external tools, emitted a real chat runtime capability snapshot, and added EV-021 live UI + chat E2E. | verified |

## Evidence

- [EV-020 Research Agent Capability Binding Live UI E2E](../evidence/EV-020-research-agent-capability-binding-live-ui-e2e.md)
- [EV-021 Research Agent Tool Binding Chat Runtime E2E](../evidence/EV-021-research-agent-tool-binding-chat-runtime-e2e.md)

## Recovery Snapshot

- Read first: this Feature, F020, linked design spec, linked implementation plan.
- Current target: maintain library-backed concrete selectors, backend reference validation, and chat runtime consumption of enabled custom-agent `skill_refs` and `allowed_tools` as the long-term binding model.
- Next safe action: keep future changes focused on Supervisor delegation quality or external Tool execution semantics; do not change the concrete Tool binding model without a separate Feature/ADR.
- Do not expand into a marketplace or unified capability registry without a separate Feature and ADR.

## Next Step

Next follow-up should focus on Supervisor delegation quality and external Tool execution semantics, not on changing the binding model.
