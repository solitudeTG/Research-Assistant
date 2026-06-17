---
id: F001
doc_kind: feature
status: active
owner: solitudeTG
created: 2026-06-17
updated: 2026-06-17
---
# Project Vision and Scope

## 目标

构建一个 Python-first 的智能科研工作台，帮助用户管理论文、提出有依据的问题、检查证据、运行多 Agent 研究流程、沉淀研究记忆，并生成可追溯的研究报告。

这个项目既要适合面试展示，也要保持产品方向清晰。它应该体现现代 Agent 工程能力，但不能脱离真实科研工作流。

## 原始问题

上一版研究助手已经验证了多项重要能力：多 Agent 协作、三层记忆、RAG、证据边界、SSE trace 和 Docker 化部署。但它有两个战略弱点：

- 技术栈偏 Java，而 Agent 面试更常围绕 Python、LangChain、DeepAgents、RAG、tools、memory 和 tracing 展开。
- 产品 UI 不足以支撑一个有说服力的科研工作台演示。

本项目围绕 Python Agent 技术栈和更成熟的工作台体验重新实现这些核心能力。

## 用户痛点

读研或科研阶段的研究工作经常分散在多个工具中：论文、笔记、证据、结论和输出文档彼此割裂。用户需要一个工作台，能够摄取资料、检索可追溯证据、展示答案生成过程，并把经过审查的研究内容转化为可用产物。

## 能力承诺

系统应支持以下核心闭环：

```text
上传或收集研究资料
-> 解析、切分并索引
-> 提出研究问题
-> 检索论文、网页或数据库证据
-> 审查结论与来源是否匹配
-> 生成带引用的答案
-> 生成报告或论文笔记
-> 在明确边界下沉淀有用记忆
```

## 范围

### P0：可演示研究闭环

- 论文上传与解析。
- 文档切分并写入向量存储。
- 混合检索与引用生成。
- 有依据的答案生成。
- 通过 SSE 展示检索、工具调用和答案生成过程。
- 工作台 UI 包含聊天、活动过程、文件和报告预览。

### P1：多 Agent 可信研究流程

- Supervisor 在轻量直接回答和深度研究流程之间做选择。
- Deep Research Agent 收集并组织证据。
- Evidence Audit Agent 检查结论与来源的对齐关系。
- Document Composer Agent 只基于已审查证据生成 Markdown 或文档型输出。

### P2：记忆与自学习

- L1 session working memory，用于当前任务连续性。
- L2 confirmed project knowledge，用于用户确认过的可复用项目知识。
- L3 candidate knowledge，用于待审核的长期候选沉淀。
- 记忆召回过程必须可观察。
- 记忆来源必须遵守 `contextOnly` 边界。

### P3：工具与 Skills

- 受控的 tool registry。
- 可复用 workflow 的 skill documents。
- 用户自定义工具或技能持久化前必须经过 sandbox 验证。
- 使用领域 tool pack，而不是默认暴露大而全的工具集合。

### P4：产品化增强

- 定时研究任务。
- 周期性研究报告。
- 文件分享。
- 资源与 token 统计。
- 通知集成必须等核心研究流程稳定后再进入。

## 非目标

- 不做通用个人聊天机器人。
- 不默认暴露大规模工具集合。
- 不把 memory 当作 citation evidence。
- 不在 UI 中展示虚假的 Agent、虚假的并行或虚假的工具调用。
- 不在缺少明确编排需求时提前引入 LangGraph。
- 不以代码量衡量进度；进度只看可验证能力增量。

## 验收来源

本 Feature 是项目初始开发的 Vision Anchor。后续 Feature、计划和实现切片都应对照本文档和 linked Feature Map spec 判断是否跑偏。

## 链接

- Spec: [F001-feature-map-and-rules-spec.md](../specs/F001-feature-map-and-rules-spec.md)

