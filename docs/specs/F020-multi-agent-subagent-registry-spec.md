# F020 Multi-Agent Subagent Registry Spec

## 1. Product Position

F020 的第一版多 Agent 能力不是开放式 Agent 市场，也不是多个 Agent 自由聊天。它是 Research Assistant 的受治理 subagent 执行层，用于在复杂科研任务中隔离上下文、并行阅读、独立审计，并让过程可被 ActivityPanel 和 AgentMentor 证据验收。

第一版运行形态：

```text
Supervisor
  - 唯一用户入口
  - 判断是否启用多 Agent
  - 调度 subagents
  - 处理后续追问
  - 生成最终回答

System Built-in Agents
  - general-purpose
  - DeepAgents/runtime 自带能力
  - Registry 中只读可见，不可编辑，不可删除
  - 默认 boundary=process_trace, citation_evidence=false

Custom Agents
  - research_auditor
  - paper_reader_worker
  - Research Assistant 应用层注册和维护
  - 可编辑、可启停、可验证、可版本化
```

## 2. Core Principles

- 简单问答仍走单 Agent。
- 多 Agent 由 Supervisor 按任务复杂度和可信度需求决定，不使用硬编码数量阈值作为唯一触发条件。
- Auditor Agent 与 Reader Workers 都是第一版必做能力；区别在于它们不是每次任务必跑，而是由 Supervisor 按任务风险和任务形态按需启用。
- 用户追问仍由 Supervisor 拥有对话状态；当追问需要重新细读论文或提取局部证据时，Supervisor 可以重新调用 Reader Worker。
- Subagent 的差异来自职责、上下文、工具权限、Skill、输入/输出边界和验证状态，而不是角色人设。
- Reader note 是 context-only 中间产物，不能作为 citation evidence。
- Auditor output 是 process trace / audit artifact，不能发明证据，也不能直接写最终答案。
- ActivityPanel 只能显示真实发生的 subagent lifecycle。
- DeepAgents 的 `general-purpose` 不应被堵死；它必须被显性治理，作为系统内置 Agent 在 Registry 中只读展示。
- Result envelope 保持最小化；业务差异优先交给 `content` 和 `metadata` 承载。

## 3. Registry Agent Types

Registry 只分两类：

| Type | Examples | Source | Editing Policy | Runtime Boundary |
| --- | --- | --- | --- | --- |
| `system_builtin` | `general-purpose` | DeepAgents/runtime | visible, read-only, not deletable | `process_trace`, `citation_evidence=false` |
| `custom` | `research_auditor`, `paper_reader_worker`, future user-created agents | Research Assistant registry | editable, enable/disable, validation required | defined by registry boundary |

`system_builtin` 的目标是消除隐藏 worker：系统不屏蔽 DeepAgents 原生能力，但必须让用户和开发者知道它存在、何时运行、产物边界是什么。

`custom` 的目标是支持应用层治理：Auditor、Reader 和未来新增 Agent 都走同一套 description、system prompt、Skill、工具权限、边界、启停、验证和版本机制。

## 4. Subagent Definition

Custom Agent definition should include:

```json
{
  "name": "research_auditor",
  "display_name": "Research Auditor",
  "agent_type": "custom",
  "source": "registry",
  "editable": true,
  "description": "Audits draft research claims against provided citation evidence.",
  "system_prompt": "You are a research audit worker...",
  "skill_refs": ["research-auditor/SKILL.md"],
  "allowed_tools": ["list_citations", "read_evidence_record"],
  "input_boundaries": ["draft_claims", "citation_evidence"],
  "output_boundary": "process_trace",
  "can_answer_user": false,
  "enabled": true,
  "version": 1,
  "validation_status": "pending",
  "metadata": {}
}
```

System Built-in Agent definition should be representable with the same read model, but not the same edit model:

```json
{
  "name": "general-purpose",
  "display_name": "General Purpose",
  "agent_type": "system_builtin",
  "source": "deepagents_builtin",
  "editable": false,
  "description": "DeepAgents built-in general task worker.",
  "output_boundary": "process_trace",
  "citation_evidence": false,
  "enabled": true,
  "validation_status": "system_managed",
  "metadata": {}
}
```

Required stable read fields:

- `name`: stable machine id.
- `display_name`: UI label.
- `agent_type`: `system_builtin` or `custom`.
- `source`: origin such as `deepagents_builtin` or `registry`.
- `editable`: whether the Registry UI can edit the definition.
- `description`: routing and user-facing explanation.
- `output_boundary`: `context_only`, `process_trace`, or `artifact`.
- `citation_evidence`: whether this agent output may ever be treated as citation evidence. For F020 agents this should be `false`.
- `enabled`: whether Supervisor/runtime may dispatch it.
- `validation_status`: `system_managed`, `pending`, `passed`, `failed`, or `disabled`.
- `metadata`: future extension field.

Custom-only governance fields:

- `system_prompt`
- `skill_refs`
- `allowed_tools`
- `input_boundaries`
- `can_answer_user`
- `version`

## 5. Default Custom Agents

### 5.1 Research Auditor

Use when:

- A draft answer, synthesis, or report contains claims that must be checked.
- The task is high-trust, report-bound, or user explicitly asks for evidence audit.

Responsibilities:

- Check whether each claim is supported by supplied citation evidence.
- Preserve evidence ids and citation labels.
- Return audit findings as process trace or audit artifact.

Forbidden:

- Do not retrieve new evidence.
- Do not write final answer text.
- Do not treat Reader notes, memory, tool logs, or LLM summaries as citation evidence.

### 5.2 Paper Reader Worker

Reader Workers provide the parallel reading and context isolation half of the multi-agent value chain. They are runtime optional: Supervisor invokes them only when the task benefits from batch paper reading, structured extraction, or follow-up scoped re-read / focused extraction.

Use when:

- Supervisor needs parallel extraction across multiple papers.
- A task asks for multi-paper comparison, literature review, method table, dataset table, limitation map, or contribution matrix.
- A user follow-up requires scoped re-read or focused extraction while Supervisor keeps ownership of conversation and final answer.

Responsibilities:

- Read only assigned paper scope.
- Produce context-only reading notes.
- Attach original citation evidence refs inside content or metadata when useful.
- Record open questions and evidence gaps.

Forbidden:

- Do not answer the user directly.
- Do not create final synthesis.
- Do not promote notes to citation evidence.
- Do not retain a long-running conversation state.

## 6. Minimal Result Envelope

Subagent-specific output may be shaped by Skill, but every execution result should fit this minimal envelope:

```json
{
  "status": "completed",
  "agent": "research_auditor",
  "boundary": "process_trace",
  "citation_evidence": false,
  "content": "...",
  "metadata": {}
}
```

Stable fields:

- `status`: `queued`, `running`, `completed`, `failed`, `deferred`, or `cancelled`.
- `agent`: agent name or id.
- `boundary`: `context_only`, `process_trace`, or `artifact`.
- `citation_evidence`: boolean evidence-boundary flag.
- `content`: primary natural-language or structured payload.
- `metadata`: extension object for refs, warnings, errors, timing, run ids, agent-specific structures, or future fields.

Promotion rule:

- Keep new fields inside `metadata` by default.
- Promote a field to top-level only when multiple agents, UI components, tests, or storage queries depend on it.
- Do not create per-agent top-level schemas for Reader, Auditor, or future custom agents.

Boundary rules:

- Reader Worker result: `boundary=context_only`, `citation_evidence=false`.
- Auditor Agent result: `boundary=process_trace`, `citation_evidence=false`.
- System built-in `general-purpose` result: `boundary=process_trace`, `citation_evidence=false`.
- Any evidence refs inside `metadata` must point to original paper/web/database evidence ids only.

## 7. Supervisor Decision Metadata

When Supervisor decides whether to invoke subagents, record an inspectable decision:

```json
{
  "multi_agent_decision": {
    "enabled": true,
    "reason": "The task asks for multi-paper comparison and independent claim audit.",
    "selected_agents": ["paper_reader_worker", "research_auditor"],
    "available_agent_types": ["system_builtin", "custom"]
  }
}
```

The decision is model-guided by system prompt and available agent descriptions. It is not primarily rule-triggered, but it must be inspectable.

## 8. Lifecycle Events

Backend should emit real lifecycle events:

- `subagent_decision`
- `subagent_started`
- `subagent_progress`
- `subagent_completed`
- `subagent_failed`
- `subagent_deferred`
- `subagent_cancelled`

Minimum event data should align with the minimal result model:

```json
{
  "workflow_id": "workflow_456",
  "task_id": "subtask_123",
  "agent": "research_auditor",
  "agent_type": "custom",
  "status": "completed",
  "boundary": "process_trace",
  "citation_evidence": false,
  "duration_ms": 5020,
  "metadata": {}
}
```

ActivityPanel may group lifecycle events, but cannot invent un-emitted agents or parallelism.

## 9. Research Agents UI

Product UI name: `Research Agents`.

Engineering name: `Subagent Registry`.

Placement:

- `Research Agents` should be a dedicated tab/page in the existing ScienceClaw workbench navigation or settings/workbench surface.
- It is a governance/configuration surface, not a primary research execution screen.
- Normal users still initiate work from Chat or Research Project context.

UI style constraints:

- Must inherit ScienceClaw's existing visual language, layout density, navigation patterns, panels, controls, and restrained workbench tone.
- Do not create a landing page, marketing-style hero, decorative role marketplace, or card-heavy agent store.
- Prefer compact tables, detail panels, forms, toggles, validation status badges, version history, and recent-run trace previews.

The page should support:

- List `system_builtin` and `custom` agents separately or with a clear type column.
- Show `general-purpose` as system built-in and read-only.
- Edit only `custom` agents.
- Enable/disable custom agents.
- Run validation examples for custom agents.
- View recent lifecycle trace for any visible agent.
- Roll back custom agents to previous versions.

Validation before enabling custom agents:

- `description` must include use and non-use boundaries.
- `system_prompt` must not permit citation-boundary bypass.
- `allowed_tools` must be explicit.
- `output_boundary` must be set.
- `can_answer_user` must be false for first-version custom agents.
- `validation_status` must be `passed`.

## 10. Skill Strategy

Do not encode every processing detail into the system prompt. System prompt defines role and boundary. Skill defines reusable method.

Default Skill candidates:

- `research-auditor/SKILL.md`
- `paper-reader-worker/SKILL.md`

Skill content should specify:

- task procedure
- expected input assumptions
- output guidance
- forbidden sources
- citation boundary
- failure handling

## 11. Implementation Slices

F020 is implemented through scoped slices under the same Feature. These are not separate Feature documents.

### F020.1 Registry Type Split And Custom Agent Governance

Scope:

- Add `system_builtin` and `custom` agent types to the Registry read model.
- Surface `general-purpose` as `system_builtin`, `source=deepagents_builtin`, `editable=false`, `boundary=process_trace`, and `citation_evidence=false`.
- Mark `research_auditor` and `paper_reader_worker` as `custom`.
- Allow custom agents to enter editing, enable/disable, validation, and version-governance flows.
- Keep system built-in agents visible, traceable, and read-only.

Acceptance:

- Backend API returns both agent types with editability and source fields.
- Research Agents UI clearly distinguishes built-in and custom agents.
- Built-in rows do not expose edit/delete actions.
- Custom rows expose governance actions when implemented.
- Tests prove `general-purpose` cannot be treated as citation evidence.

### F020.2 Supervisor Autonomous Selection Verification

Scope:

- Verify model-guided selection without explicitly naming subagents in the user prompt.
- Keep simple Q&A single-agent.
- Invoke Reader/Auditor only when task complexity, source count, or trust requirements justify it.
- Record decision metadata for selected and non-selected subagents.

Acceptance:

- Live or automated chat test proves a complex implicit research task invokes appropriate subagents.
- A simple question does not invoke subagents.
- Decision metadata explains why multi-agent was or was not used.
- No fake lifecycle events are emitted.

### F020.3 Lifecycle Metadata Hardening

Scope:

- Normalize lifecycle metadata across calling/start/running/completed/failed/deferred/cancelled events.
- Ensure each event has stable agent identity, agent type, boundary, citation flag, run id, parent id when available, and status.
- ActivityPanel should use lifecycle metadata, not free-text parsing, to group subagent runs.

Acceptance:

- Calling/start events carry the same normalized identity and boundary fields as completion events.
- Failed/deferred/cancelled states can be attributed to the correct subagent run.
- ActivityPanel renders grouped lifecycle from real emitted events only.

### F020.4 Minimal Envelope Runtime Contract

Scope:

- Map subagent outputs to the minimal envelope: `status`, `agent`, `boundary`, `citation_evidence`, `content`, `metadata`.
- Preserve agent-specific details inside `metadata` or Skill-defined `content`.
- Avoid per-agent top-level schemas unless shared consumers require promotion.

Acceptance:

- Reader output maps to `boundary=context_only`, `citation_evidence=false`.
- Auditor output maps to `boundary=process_trace`, `citation_evidence=false`.
- System built-in output maps to `boundary=process_trace`, `citation_evidence=false`.
- Tests verify extensions survive in `metadata`.

### F020.5 Recent-Run Preview And Validation Examples

Scope:

- Show recent lifecycle trace per visible agent in Research Agents.
- Allow validation examples for custom agents.
- Prevent enabling or publishing invalid custom agents.
- Keep built-in agents read-only and system-managed.

Acceptance:

- UI shows recent run status, time, boundary, and citation flag for visible agents.
- Validation examples can pass/fail custom agents.
- Failed validation prevents enablement.
- Built-in agents display runtime-managed validation status and no edit controls.

## 12. Verification Plan

Backend contract tests:

- Registry exposes `system_builtin` and `custom` agent types.
- `general-purpose` appears as read-only `system_builtin`.
- Custom Agent definitions can persist governance fields.
- Registry rejects missing boundary, empty tool policy, or user-answering first-version custom agents.
- Supervisor decision metadata is attached when multi-agent is enabled.
- Auditor lifecycle events are emitted from a real invocation.
- Reader lifecycle events are emitted for batch paper reading.
- Reader result has `context_only` boundary and `citation_evidence=false`.
- Auditor result has `process_trace` boundary and does not add citation evidence.
- Result envelope accepts minimal top-level fields and preserves extensions in `metadata`.

Frontend contract tests:

- Research Agents page shows agent type and editability.
- System built-in agents are visible but not editable.
- Custom agents expose editing/governance affordances when implemented.
- Research Agents page follows the existing ScienceClaw workbench structure and does not expose a marketplace/role-store layout.
- ActivityPanel renders real subagent lifecycle events.
- ActivityPanel does not require fake agent rows when no subagent ran.

Quality / AgentMentor checks:

- Final answer still carries original citation evidence.
- Reader notes cannot pass as citation evidence.
- Auditor output can be persisted or displayed as audit/process trace.
- `general-purpose` output remains process trace and cannot become citation evidence.

## 13. Open Implementation Questions

- Should `general-purpose` be enable/disable configurable in the future, or always runtime-managed and read-only?
- Which custom-agent fields are editable in the first editable Registry slice?
- Should calling/start lifecycle events carry the same normalized metadata as completion events?
- How should Skill validation run in the sandbox before enabling a custom agent?
- Should recent-run preview be per agent, per session, or both?

## 14. Non-Goals

- No Planner Agent.
- No open Agent role marketplace.
- No group chat.
- No direct user chat with subagents.
- No fake parallel display.
- No Reporter Agent in first version.
- No Memory Curator Agent in first version.
- No LangGraph migration unless lifecycle/checkpoint requirements exceed current runner.
