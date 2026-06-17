---
id: F001
status: active
owner: solitudeTG
created: 2026-06-17
updated: 2026-06-17
feature_ids: [F001]
---
# Feature Map and Rules Spec

## 目的

本文档定义 Research Assistant 的初始 Feature Map 与开发规则，用于防止项目滑向“能力很多但主线很散”的泛 Agent demo。

## 产品边界

Research Assistant 可以拥有较广的科研 Agent 能力，但每个能力都必须服务于至少一个研究工作流：

- 文献摄取与理解
- 证据检索与引用
- 结论与来源审查
- 研究记忆与知识复用
- 报告或研究产物生成
- 研究过程可观察性

不服务于这些工作流的能力默认延后。

## Feature Map

### P0：核心 Demo

P0 是最小完整产品故事。

必须具备：

- 上传论文或研究文档。
- 解析并切分文档。
- 将 chunks 索引到 PostgreSQL + pgvector。
- 提出有依据的问题。
- 在合适时使用混合检索召回证据。
- 生成带 citation 的答案。
- 将过程事件流式推送到 UI。
- 在工作台中展示生成文件和证据产物。

退出标准：

- 用户可以从 UI 完成“论文 -> 问题 -> 答案”的闭环。
- 最终答案包含可追溯 citation。
- 过程 trace 反映真实后端事件。
- 应用可通过 Docker Compose 或明确的本地开发路径启动。

### P1：多 Agent 研究

P1 只在能提升质量或解释性的地方引入角色拆分。

必须具备：

- Supervisor 选择直接回答或深度研究模式。
- Deep Research Agent 生成结构化 research packet。
- Evidence Audit Agent 标记无支持或弱支持结论。
- Document Composer Agent 只基于 approved evidence 和 audit output 写作。

规则：

- 简单问题不得强制进入多 Agent 流程。
- Composer 不得自行检索新证据。
- UI 只能展示真实 Agent 生命周期和工具事件。

### P2：记忆

P2 恢复三层记忆思想，并强化边界。

必须具备：

- L1 session working memory。
- L2 confirmed reusable project knowledge。
- L3 candidate knowledge，等待后续审核。
- 可见的 memory recall reason。
- memory-derived context 必须标记 `contextOnly=true`。

规则：

- memory 可以辅助回答，但不能成为 citation evidence。
- confirmed knowledge 需要明确确认或 promotion 路径。
- candidate knowledge 必须可审查、可撤销。

### P3：工具与 Skills

P3 提供扩展能力，但避免工具膨胀。

必须具备：

- tool registry。
- skill registry。
- custom tools 的 sandbox validation。
- 持久化前的用户确认。
- domain-scoped tool packs。

规则：

- 除非服务当前研究流程，否则工具默认不启用。
- tool result schema 必须可检查。
- custom tools 必须测试后才能持久化。

### P4：产品化增强

P4 提升日常使用价值。

候选能力：

- 定时研究任务。
- 周报或月报生成。
- 可分享输出。
- 资源与 token 统计。
- 通知集成。

规则：

- P4 不得阻塞 P0 或 P1。
- 定时任务必须复用交互任务同一套 evidence 与 trace contracts。

## 架构原则

### DeepAgents First

第一版优先使用 DeepAgents 处理 Agent 执行、工具调用、文件操作、sandbox 工作和长任务行为。

只有出现明确需求时才引入 LangGraph，例如：

- 稳定区分 ReAct 与 Plan-Execute 分支。
- Document composition 前必须经过 Evidence Audit。
- 需要 resumable checkpoints。
- 需要节点级失败恢复。
- UI 需要严格映射到 workflow states。

### Evidence Before Presentation

答案界面不能暗示比后端实际收集到的证据更强的可信度。

允许成为 citation 的来源：

- 论文 chunks。
- 网页。
- 可信外部研究数据库。

不能成为 citation 的来源：

- memory。
- model reasoning。
- tool logs。
- 缺少 source identity 的 summaries。

### Trace Honesty

UI 不能发明工作过程。Trace panel 可以简化或分组事件，但不能展示没有真实发生的 Agent、工具、并行关系或证据。

### Workbench UI

界面应该像研究工具，而不是营销页。优先使用信息密度适中、组织清晰、可检查的界面：

- chat and answer surface。
- activity or trace panel。
- file and artifact panel。
- evidence or citation inspection。
- report preview。

避免任何不推进用户工作流的装饰性页面。

## 开发规则

- 每个非平凡 Feature 都需要 Vision Anchor。
- 每个非平凡 Feature 实现前都需要 acceptance criteria。
- 每个 completion claim 都需要 verification evidence。
- 广泛工具和集成默认延后，除非它们服务当前 Feature。
- 优先做小而可验证的能力增量，避免大重写。
- 不把测试通过当作产品方向正确的证明。
- 不创建后端无法真实支持的 UI 状态。

## 初始提交策略

推荐提交顺序：

1. `docs: define project vision, feature map, and agent rules`
2. `chore: import baseline application shell`
3. `refactor: trim baseline to research workbench scope`
4. `feat: add paper ingestion and grounded rag pipeline`
5. `feat: add agent execution trace`
6. `feat: add multi-agent research workflow`
7. `feat: add memory recall and evidence boundaries`

## 开放问题

- P0 应使用哪套文档解析栈？
- P0 的 BM25-like retrieval 是先用 PostgreSQL full-text search，还是后续引入专门搜索组件？
- 第一版报告生成只支持 Markdown，还是同时支持 DOCX/PDF？
- 第一版是否支持 web search，还是先聚焦 uploaded papers？
