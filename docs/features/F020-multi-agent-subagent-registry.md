---
id: F020
doc_kind: feature
status: active
owner: solitudeTG
created: 2026-07-02
updated: 2026-07-03
---

# F020: 多 Agent 科研工作流与 Subagent Registry

## Goal

建立 Research Assistant 的第一版真实多 Agent 协作能力：简单问答仍由单一 Supervisor 处理；复杂科研任务才按需启用受治理的 subagent。第一版边界是 `Supervisor + Auditor Agent + Reader Workers`，不做 Planner、不做常驻 Reader、不做 Agent 市场、不做 group chat、不伪造并行。

## Vision Anchor

- Source: 用户在 2026-07-02 至 2026-07-03 的多轮产品讨论中明确收敛到第一版 F020 边界：Auditor Agent 必做，Reader Workers 必做但按任务需要启用，Registry 作为受治理配置而不是开放角色市场。
- User pain point: 单 Agent 在多论文综述、跨来源综合、高可信审计中容易上下文腐化、自证循环、过程不可复核；但随意增加 Agent 又会造成角色边界模糊、trace 造假、证据边界污染和难以验收。
- Desired outcome: Supervisor 作为唯一用户入口，能基于受治理 subagent 定义进行委派；ActivityPanel 只展示真实发生的 subagent lifecycle；Reader/Auditor 输出不得伪装成 citation evidence。
- Non-goals: 不做 Planner Agent；不做常驻 Reader；不做开放 Agent 市场；不做 group chat；不做展示型假并行；不让 Reader note 成为 citation evidence；不让 subagent 直接面对用户。
- Exit Gate source: 本 Feature、F001 项目愿景、F004 citation evidence boundary、F008 trace honesty、F018 claim-level audit、F019 quality evaluation harness、`docs/specs/F020-multi-agent-subagent-registry-spec.md`。

## Feature Intake

- Original problem: Research Assistant 需要从单 Agent 科研助手演进为能处理复杂科研任务的多 Agent 工作台，但必须避免多 Agent 角色边界失控。
- User pain point: 单 Agent 在多论文综述、跨来源综合、高可信审计中容易上下文腐化、自证循环和失败不可定位；随意增加 subagent 又会制造更多状态分叉和证据混乱。
- Capability promise: 提供一个受治理的 subagent 注册与调度边界，让 Supervisor 能按需调用第一版内置 Auditor Agent 和 Reader Workers，并保留真实 lifecycle trace、最小结果外壳和 evidence boundary。
- Non-goals: 不开放任意角色市场；不把所有复杂任务都强制多 Agent；不把 Planner 独立出来；不让 subagent 成为用户追问入口；不让 Reader 拥有独立对话状态。
- Acceptance source: 用户明确确认第一版定义为 `Supervisor + Auditor Agent + Reader Workers`；Reader Workers 与 Auditor Agent 均属于第一版必做能力；运行时触发由主 Agent 结合 system prompt 判断。
- Open questions: 是否要让 calling/start 事件也携带完整 normalized lifecycle metadata；Registry 编辑/启停/回滚与 recent-run preview 的优先级尚未确定；系统内置 Agent 与用户自定义 Agent 的 UI 编辑策略需要在实现时精确落地。

## Capability Contract

- Supervisor 是唯一用户入口，负责理解目标、判断是否启用多 Agent、调度 subagent、处理追问和生成最终回答。
- Auditor Agent 是第一版必做 subagent，负责独立审计 draft claims 与 citation evidence 的匹配关系；它不写最终结论、不补证据、不润色报告。
- Reader Workers 是第一版必做能力，但只在多论文批量阅读、结构化提取、或 Supervisor 拥有追问上下文时的 scoped re-read / focused extraction 中按需启用；它们是一次性 workers，不常驻、不和用户对话、不拥有后续追问入口。
- Reader Worker 输出是 context-only reading note 或中间产物，不能成为 citation evidence；最终回答仍必须回到原始 paper/web/database evidence。
- Subagent Registry 维护可调度 subagent 的 `name`、`description`、`system_prompt`、`skill_refs`、工具权限、输入/输出边界、启用状态、版本和验证记录。
- Registry 按治理来源分为两类：`system_builtin` 与 `custom`。`system_builtin` 代表 DeepAgents/runtime 自带能力，例如 `general-purpose`；它必须在 Registry 中显性可见，但只读、不可编辑、不可删除，并默认标记为 `process_trace` 与 `citation_evidence=false`。
- `custom` 代表 Research Assistant 应用层注册和维护的 Agent，包括 `research_auditor` 与 `paper_reader_worker`，也包括未来用户新增 Agent；它们可以进入编辑、启停、验证和版本治理流程。
- Subagent result envelope 只保留跨 Agent 协作必须理解的最小顶层字段：`status`、`agent`、`boundary`、`citation_evidence`、`content`、`metadata`。其余扩展字段优先进入 `metadata`，只有当多个 Agent、UI 或测试共同依赖时才提升为顶层字段。
- Subagent Registry 的产品入口是独立的 `Research Agents` tab/page，但必须继承 ScienceClaw 工作台风格：高密度、克制、操作台式布局，不引入营销页、角色卡市场或新的视觉语言。
- Supervisor 的多 Agent 决策由模型判断和 system prompt 引导，而不是硬编码规则触发；但决策与真实调用必须进入 trace。
- ActivityPanel 只能展示真实发生的 subagent lifecycle，不得展示未调用的 agent、伪并行、伪协作或伪证据状态。

## Decision Context

### Why

多 Agent 的第一性原理不是“多几个角色”，而是把容易上下文腐化和失控的大任务拆成边界清晰、可并行、可审计、可恢复的认知单元。对 Research Assistant 来说，最值得拆的是批量阅读上下文与独立证据审计；规划本身仍由 Supervisor 承担，所以 Planner Agent 会重复主 Agent 职责并增加系统复杂度。

### Why Not

开放式 Agent 市场被拒绝，因为它会鼓励靠角色人设区分能力，弱化工具权限、数据边界、输出边界和验收机制。Group chat 被拒绝，因为多个 agent 在同一对话空间自由讨论会削弱 citation evidence boundary 和 trace honesty。常驻 Reader 被拒绝，因为用户追问应由 Supervisor 统一拥有对话状态；Supervisor 可以在追问中重新调用 Reader Worker 做 scoped re-read 或 focused extraction。

DeepAgents 的 `general-purpose` 不应被简单禁用。它是 runtime 自带能力，直接屏蔽会削弱 DeepAgents 的通用委派价值。F020 采用“显性治理而非堵死”的原则：系统内置 Agent 必须在 Registry 中可见、可追踪、只读展示；Research Assistant 自己定义的 Auditor / Reader 以及未来用户新增 Agent 走 `custom` 治理模型。

### If Modifying This Area, Check

- F001: 是否仍服务可信科研工作台，而不是通用聊天或角色展示。
- F004: subagent 输出是否错误进入 citation evidence。
- F008: ActivityPanel 是否只展示真实 lifecycle。
- F018: Auditor 是否保持 claim-level citation audit 边界。
- F019: 多 Agent 输出是否能进入质量 gate。
- F002 / ScienceClaw UI 约束: Research Agents 页面是否仍继承现有 application shell、聊天壳、ActivityPanel 和文件/产物面板视觉风格。

## Current Status

Active implementation anchor. 已完成第一条可验证能力增量：默认 Auditor/Reader 定义、Registry 持久化与读取、DeepAgents subagent 配置、真实 lifecycle metadata 透传、ActivityPanel metadata 展示、只读 `Research Agents` 工作台页面，以及真实 chat UI 中触发 `task(subagent_type=...)` 的端到端截图与事件证据。当前产品边界已更新为两类 Registry 模型：系统内置 Agent 显性只读展示，用户自定义 Agent 可编辑治理；result envelope 采用最小顶层字段与 `metadata` 扩展原则。

尚未完成 Registry 编辑/启停/回滚、validation examples、recent-run preview，以及隐式复杂任务下的自主 subagent 选择验证。

## Links

### Evidence

- [EV-011 F020 Subagent Registry and Runtime Trace Verification](../evidence/EV-011-f020-subagent-registry-runtime-verification.md)
- [EV-012 F020 Research Agents Live UI Verification](../evidence/EV-012-f020-research-agents-live-ui-verification.md)
- [EV-013 F020 Live Chat Multi-Agent E2E Verification](../evidence/EV-013-f020-live-chat-multi-agent-e2e-verification.md)
- [EV-014 F020 Agent Governance Verification](../evidence/EV-014-f020-agent-governance-verification.md)

### Decisions / ADRs

- [ADR-001 P0 Research Data and Retrieval Stack](../decisions/ADR-001-p0-research-data-and-retrieval-stack.md)

### Lessons

- None.

### Specs / Plans

- [F020 Multi-Agent Subagent Registry Spec](../specs/F020-multi-agent-subagent-registry-spec.md)

### Related Features

- [F001 Project Vision and Scope](F001-project-vision-and-scope.md)
- [F004 Citation Evidence Boundary](F004-citation-evidence-boundary.md)
- [F008 Trace Honesty and Activity Panel](F008-trace-honesty-activity-panel.md)
- [F018 Claim-Level Citation Audit Calibration](F018-claim-level-citation-audit-calibration.md)
- [F019 Research Quality Evaluation Harness](F019-research-quality-evaluation-harness.md)

### External Context

- None.

## Implementation Slices

F020 的后续落地必须按可验证能力增量推进。以下 slice 是当前 F020 的实施约束，不是独立 Feature，也不新建 F021-F025。

| Slice | Goal | Acceptance | Status |
| --- | --- | --- | --- |
| F020.1 | Registry 类型分层与 Custom Agent 编辑治理 | Registry 能区分 `system_builtin` 和 `custom`；`general-purpose` 作为系统内置 Agent 只读可见；`research_auditor` / `paper_reader_worker` 作为 custom agents 支持编辑、启停、基础验证和版本治理入口。 | next |
| F020.2 | Supervisor 自主决策验收 | 在未显式点名 subagent 的复杂科研任务中，Supervisor 能基于 system prompt、agent descriptions 和任务风险自主决定是否启用 Reader/Auditor，并记录可检查的 decision metadata；简单问答保持单 Agent。 | planned |
| F020.3 | Lifecycle metadata hardening | `task` calling/start/running/completed/failed/deferred/cancelled 事件都携带统一 subagent lifecycle metadata，ActivityPanel 能稳定串联同一个 subagent run，不依赖解析自由文本或 tool args。 | planned |
| F020.4 | Minimal envelope runtime contract | Reader/Auditor/system builtin outputs 都能映射到最小 envelope：`status`、`agent`、`boundary`、`citation_evidence`、`content`、`metadata`；扩展字段默认进入 `metadata`，不得引入 per-agent 顶层 schema。 | planned |
| F020.5 | Recent-run preview 与 validation examples | Research Agents 页面能展示每个 agent 的 recent lifecycle trace，并能对 custom agents 运行 validation examples；验证失败时不能启用或发布 custom agent。 | planned |

## Acceptance Criteria

- [ ] Supervisor can decide whether a task should stay single-agent or invoke registered subagents, and the decision is recorded in trace metadata.
- [x] Subagent Registry can persist and expose enabled subagent definitions with `name`, `description`, `system_prompt`, `skill_refs`, tool policy, boundaries, version, and validation status.
- [ ] Registry distinguishes `system_builtin` agents such as `general-purpose` from `custom` agents such as `research_auditor` and `paper_reader_worker`; built-in agents are visible and traceable but not editable.
- [x] Auditor Agent can be invoked as an independent worker for draft claims and citation evidence, and cannot write final conclusions.
- [x] Reader Workers can be invoked only for batch/focused multi-paper reading tasks or Supervisor-owned follow-up re-read/extraction, and return context-only notes.
- [ ] Subagent results use a minimal extensible envelope with only `status`, `agent`, `boundary`, `citation_evidence`, `content`, and `metadata` as stable top-level fields; optional details remain in `metadata` until shared consumers require promotion.
- [x] ActivityPanel renders only real subagent lifecycle events and preserves failed/deferred states.
- [x] Research Agents tab follows the existing ScienceClaw workbench UI style and does not introduce a marketplace-like visual system.
- [x] Reader notes cannot become citation evidence, and Auditor output cannot invent evidence.
- [ ] Frontend and backend tests cover Supervisor decision metadata, registry contract, lifecycle events, Reader boundary, Auditor boundary, and ActivityPanel display.

## Acceptance Map

| Claim | Acceptance | Evidence | Status |
| --- | --- | --- | --- |
| Multi Agent is opt-in by task complexity. | Supervisor records why subagents were or were not invoked. | EV-013 verifies an explicit complex task path; implicit autonomous selection remains open. | Partial |
| Auditor is independent from answer generation. | Auditor receives claims/evidence and returns audit output without writing final answer content. | EV-013 | Implemented for live explicit complex chat task |
| Reader is a bounded worker, not a chat participant. | Reader can run for multiple papers or scoped follow-up re-read/extraction and returns context-only notes; follow-up conversation ownership stays with Supervisor. | EV-013 | Implemented for live explicit complex chat task |
| Registry is governed configuration, not an open role market. | Registry separates `system_builtin` agents from `custom` agents; built-ins are visible/read-only, custom agents can be edited, enabled, validated, and versioned. | EV-011, EV-012; updated F020 decision context | Partially implemented; type split UI/editing remains open |
| Result envelope stays lightweight and extensible. | Stable top-level fields are limited to status, agent identity, boundary, citation evidence flag, content, and metadata; agent-specific shape belongs in metadata or Skill-defined content. | Updated F020 decision context and spec | Planned |
| ActivityPanel remains honest. | UI shows only emitted subagent lifecycle events. | EV-013 | Implemented with calling-event metadata caveat |
| First executable governed subagent slice exists. | Defaults, schema, repository wrappers, DeepAgents config, lifecycle metadata, route mapping, and ActivityPanel metadata display are covered by focused tests. | EV-011 | Implemented |
| Research Agents page follows ScienceClaw workbench UI. | A dedicated `/chat/research-agents` page lists governed Auditor/Reader definitions, boundaries, tools, skills, and validation state without marketplace/persona layout. | EV-012 | Implemented |

## State Timeline

| Date | State | Trigger | Evidence | Note |
| --- | --- | --- | --- | --- |
| 2026-07-02 | active | User approved multi-agent first-version boundary | This Feature and linked spec | Created from product discussion to replace broad F014 backlog ambiguity. |
| 2026-07-02 | active | Implemented first governed subagent vertical slice | EV-011 | Added default Auditor/Reader definitions, PostgreSQL registry/run tables, DeepAgents config, lifecycle metadata, Research Agents list route, and ActivityPanel metadata display. |
| 2026-07-03 | active | Implemented Research Agents workbench page and live UI e2e | EV-012 | Added route, left rail entry, API client contract, read-only governed registry page, desktop/mobile browser verification, and screenshot evidence. |
| 2026-07-03 | active | Completed live chat multi-agent E2E | EV-013 | Submitted a complex task through the UI, observed two Reader Worker completions and one Auditor Agent completion in real task trace, and captured ActivityPanel screenshot plus structured event evidence. |
| 2026-07-03 | active | Refined Registry and envelope principles | User product discussion and this Feature | Decided not to block DeepAgents `general-purpose`; instead surface it as read-only `system_builtin`, keep Auditor/Reader as editable `custom`, and reduce result envelope to minimal fields plus `metadata`. |
| 2026-07-03 | active | Implemented F020.1-F020.5 governance slices | EV-014 | Added Registry type split, Supervisor delegation prompt, lifecycle metadata hardening, minimal result envelope, recent-run preview, validation examples, and live Research Agents UI verification. |

## Patch History

None yet.

## Evidence

- EV-011 verifies the first executable registry/runtime/trace slice.
- EV-012 verifies the read-only `Research Agents` page and live UI e2e.
- EV-013 verifies the live chat multi-agent E2E trace for an explicit complex task, including Reader Worker, Auditor Agent, ActivityPanel screenshot, and evidence-boundary metadata.
- EV-014 verifies F020.1-F020.5 governance slices, focused backend/frontend checks, and Research Agents live UI validation with recent-run preview and validation example.

Full Research Agents editing UI, strict autonomous trigger policy, and recent-run preview remain future work.

## Recovery Snapshot

- Read first: this Feature, linked F020 spec, F001, F004, F008, F018, F019.
- Current capability state: first registry/runtime/trace slice, read-only Research Agents page, and live chat `task(subagent_type=...)` trace evidence are implemented and verified.
- Known risks: subagent definitions can drift into role-persona prompts if Registry validation does not require tool policy, boundaries, and validation evidence; system built-in agents can become confusing if they are not visibly separated from custom agents.
- Next safe action: update Registry data/UI contract to represent `system_builtin` versus `custom`, show `general-purpose` as read-only, then add edit/enable validation workflow for custom agents.
- Unblock condition: decide whether the next implementation increment prioritizes Registry type split and editing, lifecycle metadata hardening, or autonomous implicit-selection validation.

## Next Step

Choose the next F020 increment: Registry type split plus custom-agent editing governance, validation examples/recent-run previews, lifecycle metadata hardening, or autonomous implicit-selection verification.
