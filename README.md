# Research Assistant

## 二次开发与致谢

Research Assistant 是在 [ScienceClaw](https://github.com/AgentTeam-TaichuAI/ScienceClaw)
基础上进行的二次开发。项目保留对 ScienceClaw 的公开致谢和 license/attribution
边界，并将 ScienceClaw 作为工作台底座参考：UI 风格、聊天壳、ActivityPanel、
文件/产物面板、沙箱、SSE trace 和 Docker Compose 编排会优先继承其成熟方向。

本仓库的产品目标会进一步收敛到 Python-first 的智能科研工作台，重点融合论文
RAG、证据边界、三层记忆、多 Agent 研究流、Evidence Audit 和 Harness 思维。
第三方归属说明见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

## 项目背景

Research Assistant 面向需要长期处理论文、证据、笔记和研究产物的科研工作流。现实中的研究任务通常不是一次问答，而是一个持续过程：收集资料、阅读论文、提出问题、比较来源、检查结论、沉淀可复用知识，并最终生成报告、综述或研究笔记。

普通聊天机器人可以辅助解释内容，但很容易把模型推理、记忆、工具日志和真实证据混在一起；传统文献管理工具又缺少可执行的 Agent 工作流、过程 trace 和自动产物生成能力。因此，本项目的核心背景不是“做一个更强的聊天助手”，而是构建一个能围绕证据工作的智能研究工作台。

这个工作台需要持续回答三个问题：

- 结论来自哪些可追溯来源？
- 研究过程实际发生了什么？
- 哪些知识可以沉淀复用，但不能伪装成 citation evidence？

因此，Research Assistant 将 ScienceClaw 的工作台 UI、沙箱、trace 和服务编排作为二次开发底座，在其上收敛出论文 RAG、证据边界、Evidence Audit、三层记忆、多 Agent 研究流和报告生成能力。

## 当前工程基线

当前仓库已经导入 ScienceClaw baseline application shell，后续二次开发应以该
baseline 为可运行底座推进，而不是重新发明一套工作台。导入范围、验证命令、
已知构建警告和 Research Assistant 功能接入顺序见
[ScienceClaw Baseline Import Notes](docs/baseline-import-notes.md)。

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
