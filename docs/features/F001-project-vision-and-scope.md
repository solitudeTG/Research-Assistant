---
id: F001
doc_kind: feature
status: active
owner: solitudeTG
created: 2026-06-17
updated: 2026-06-18
---

# F001: Project Vision and Scope

## Goal

构建一个 Python-first 的智能科研工作台，帮助用户管理论文、提出有依据的问题、检查证据、运行多 Agent 研究流程、沉淀研究记忆，并生成可追溯的研究报告。

这个项目既要适合展示现代 Agent 工程能力，也要保持产品方向清晰：所有主要能力都必须服务真实科研工作流，而不是堆叠通用聊天或泛工具能力。

## Vision Anchor

- 原始请求或来源：项目初始化方向与本地 `AGENTS.md` 军规。
- 用户痛点或工程问题：科研工作分散在论文、笔记、证据、结论和输出文档之间，用户需要一个能收集资料、检索可追溯证据、展示答案生成过程，并将审查后内容转化为产物的工作台。
- 期望结果：以 ScienceClaw 为 baseline application shell，融合旧版 Research Workbench 的论文 RAG、证据边界、三层记忆、多 Agent 研究流、Evidence Audit 和 Harness/AgentMentor 思维。
- 非目标或边界：不做通用个人聊天机器人；不默认暴露大规模工具集合；不把 memory 当作 citation evidence；不在 UI 中展示虚假的 Agent、并行、工具调用、证据或 workflow state；不在缺少明确编排需求时提前引入 LangGraph。
- Exit Gate 对照来源：本 Feature、linked Feature Map spec、`docs/baseline-import-notes.md`、以及后续每个 Research Assistant 功能的 AgentMentor closeout evidence。

## Current Status

In Progress。

当前仓库已经导入 ScienceClaw baseline application shell，并通过基础 backend/frontend 验证。Research Assistant 专属能力尚未完成，后续应按可验证能力增量继续开发。

## Links

- Spec: [F001-feature-map-and-rules-spec.md](../specs/F001-feature-map-and-rules-spec.md)
- Baseline import notes: [baseline-import-notes.md](../baseline-import-notes.md)
- Third-party notices: [THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md)

## Acceptance Criteria

- [x] 项目公开说明以 ScienceClaw 为二次开发 baseline，并保留 attribution / notice。
- [x] 当前仓库包含 ScienceClaw baseline application shell，且不包含参考副本的 `.git` 历史。
- [x] `AGENTS.md` 保持本地 Agent 规则文件，不进入 Git 管理。
- [x] 至少完成一组 baseline 验证命令，并记录命令、结果和已知警告。
- [ ] 支持论文上传与解析，并能把解析结果纳入研究工作流。
- [ ] 支持论文 RAG，并能返回可追溯 citation evidence。
- [ ] 明确区分 citation evidence 与 context-only memory。
- [ ] ActivityPanel / trace panel 只展示真实后端事件。
- [ ] 支持 Evidence Audit 对结论和来源关系进行检查。
- [ ] 支持报告生成，且报告只基于已审查证据和明确上下文。
- [ ] 支持三层记忆，并保证 memory 不伪装为 citation evidence。

## Patch History

None yet.

| Patch | Date | Commit | Symptom | Root Cause | Protection | Status |
| --- | --- | --- | --- | --- | --- | --- |

## Evidence

- `35d660fcc060ed114582be5dfa992bc6f6698113` added public ScienceClaw attribution notices.
- `0d5d2ff0c549ef1a94a3a0f724a7968b9c696c15` imported the ScienceClaw baseline application shell.
- `c781ce23d22f032a966a2602555ed9a6f0e4f47d` recorded baseline import verification and the next Research Assistant development order.
- Baseline verification recorded in [baseline-import-notes.md](../baseline-import-notes.md):
  - `python -m compileall ScienceClaw\backend`
  - `npm.cmd ci` in `ScienceClaw\frontend`
  - `npm.cmd run build` in `ScienceClaw\frontend`

## Next Step

Start the first Research Assistant-specific feature slice with AgentMentor gates: paper upload and parsing. The slice should add real backend behavior, a visible workflow entry point in the ScienceClaw workbench shell, and verification evidence before claiming completion.
