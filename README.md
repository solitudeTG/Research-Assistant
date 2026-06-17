# Research Assistant

## 二次开发与致谢

Research Assistant 是在 [ScienceClaw](https://github.com/AgentTeam-TaichuAI/ScienceClaw)
基础上进行的二次开发。项目保留对 ScienceClaw 的公开致谢和 license/attribution
边界，并将 ScienceClaw 作为工作台底座参考：UI 风格、聊天壳、ActivityPanel、
文件/产物面板、沙箱、SSE trace 和 Docker Compose 编排会优先继承其成熟方向。

本仓库的产品目标会进一步收敛到 Python-first 的智能科研工作台，重点融合论文
RAG、证据边界、三层记忆、多 Agent 研究流、Evidence Audit 和 Harness 思维。
第三方归属说明见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

Research Assistant 是一个 Python-first 的智能科研工作台，核心关注文献理解、证据可信、多 Agent 研究流程、记忆沉淀与报告生成。

这个项目不是通用聊天机器人。所有主要能力都应该服务于以下研究工作流：

- 管理和理解论文
- 从论文、网页或可信研究数据库中检索可追溯证据
- 审查结论与来源之间的对应关系
- 保存有价值的研究记忆，但不把记忆伪装成引用证据
- 生成可追溯的研究报告或论文笔记

## 初始方向

第一版优先实现一条窄而完整、可演示的研究闭环：

```text
上传论文 -> 解析并索引 -> 提出有依据的问题 -> 查看引用和过程 trace -> 生成研究产物
```

系统应该像一个研究工作台：信息密度适中、过程可追踪、文件可管理，并且适合反复执行真实研究任务。

## 计划技术栈

- Python
- FastAPI
- DeepAgents
- LangChain
- PostgreSQL + pgvector
- Redis
- Vue 3 + TypeScript
- Server-Sent Events
- Docker Compose

第一版不强制引入 LangGraph。只有当项目确实需要显式状态机编排、可恢复 checkpoint、严格多 Agent 路由或节点级失败恢复时，才引入 LangGraph。

## 项目记忆

项目的长期方向从以下文档开始：

- [F001 Project Vision and Scope](docs/features/F001-project-vision-and-scope.md)
- [F001 Feature Map and Rules Spec](docs/specs/F001-feature-map-and-rules-spec.md)

本地 Agent 规则可以写在 `AGENTS.md`，但该文件有意不进入 Git 管理。
