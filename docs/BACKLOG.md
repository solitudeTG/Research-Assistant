# Research Assistant Backlog

本文件记录已经确认有价值、但不属于当前主线交付的未来增强项。Backlog 项不等于 active Feature；开始实现前需要重新经过 AgentMentor Start Gate，并创建或激活对应 Feature。

## Future Enhancements

### Future: Automated Literature Discovery and External Evidence Connectors

- Status: deferred
- Trigger: 用户要求记录“自动文献发现、网页/数据库检索接入还没完全产品化”。
- Goal: 将当前 paper/web/database citation boundary 从“可接入、可审计、可手动纳入”推进到产品化检索工作流：自动文献发现、网页证据检索、数据库查询/导入、来源质量提示、去重、候选证据确认、以及进入 Chat / Literature Review 的可见 trace。
- Why it matters: 当前最强 live 主链路是用户提供 PDF 后的论文 RAG、Evidence Matrix 和报告生成；web/database evidence 已有边界与存储/检索能力，但还不是完整的自动发现与检索产品体验。
- Non-goals for first slice: 不把搜索结果自动当成 citation；不绕过 evidence admission gate；不把 memory、tool logs、model reasoning 或 process trace 写成 citation evidence；不重写 ScienceClaw UI shell；不引入不可验收的 crawler 大工程。
- Suggested first Feature: `F026-automated-literature-discovery-and-external-evidence-connectors.md`.
- Suggested acceptance: 至少一个真实网页检索 case、一个数据库 evidence case、一个 paper discovery case 通过 live UI 或 reproducible demo runner；最终答案只引用 paper/web/database evidence，并在 ActivityPanel 展示真实检索、筛选、采纳/拒绝 trace。

### F014: Multi-paper Research Synthesis + Multi-Agent Workflow

- Status: refined into active Feature
- Superseded by: [F020 Multi-Agent Research Workflow and Subagent Registry](features/F020-multi-agent-subagent-registry.md)
- Original goal: 支持多论文对比、研究综述、跨文献观点综合和报告生成，并在确实受益的复杂研究任务中启用真实多 Agent 协作。
- Refined first-version boundary: 第一版不做完整六角色多 Agent 平台，而是落地 `Supervisor + Auditor Agent + Reader Workers`；Auditor 与 Reader 都是第一版必做能力，但运行时由 Supervisor 按需启用。
- Non-goals retained: 不为了展示效果伪造并行、协作、证据或状态；不做 Planner Agent；不做常驻 Reader；不做 group chat；不做开放式 Agent 角色市场。
- Rationale: 多 Agent 的核心难点是边界划分。F020 将 F014 的宽泛方向收敛为可治理 subagent 注册、Supervisor 委派、独立 Auditor、批量 Reader Worker、真实 lifecycle trace 和 AgentMentor 验收。

### Future: Full Multi-Paper Synthesis Report Workflow

- Status: deferred
- Depends on: F020 first-version subagent registry and lifecycle trace.
- Goal: 在 F020 的受治理 subagent 基础上，扩展完整多论文综述、Evidence Matrix、跨论文 synthesis、报告生成和更丰富的 source-quality / evidence-gap 工作流。
- Non-goals for now: 不阻塞 F020 第一版落地；不提前引入大型 graph runtime；不把 Reader notes 变成 citation evidence。
