# Research Assistant Backlog

本文件记录已经确认有价值、但不属于当前主线交付的未来增强项。Backlog 项不等于 active Feature；开始实现前需要重新经过 AgentMentor Start Gate，并创建或激活对应 Feature。

## Future Enhancements

### F014: Multi-paper Research Synthesis + Multi-Agent Workflow

- Status: deferred
- Priority: later
- Trigger: 当单篇论文可信工作流、Research Library、Project-scoped RAG、Chat 上传边界、whole-paper summary、citation audit 和 trace 体验稳定后再启动。
- Goal: 支持多论文对比、研究综述、跨文献观点综合和报告生成，并在确实受益的复杂研究任务中启用真实多 Agent 协作。
- Intended agents: Planner, Retriever, Reader, Synthesizer, Auditor, Reporter.
- Non-goals for now: 不在当前阶段实现多 Agent；不为了展示效果伪造并行、协作、证据或状态；不替代当前 F013 单篇论文路由与摘要主线。
- Rationale: Multi-Agent Research Synthesis 是后期亮点和放大器，不是当前可信科研工作台的地基。当前优先级仍是稳定论文摄取、Project 边界、RAG 路由、整篇总结、证据审计和真实 trace。
- Start condition: F013 至少完成 LLM structured router 或整篇摘要质量增强后，再评估是否创建 active `F014` Feature。
