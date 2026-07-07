---
id: F000
doc_kind: feature
status: active
owner: solitudeTG
created: 2026-06-28
updated: 2026-06-29
---

# Feature Index

## Goal

本索引是 AgentMentor Feature 的默认召回入口。新会话或新 Agent 不应先通读超大的 `F001`，而应先从这里判断当前任务属于哪个能力边界。

## Vision Anchor

- Source: AgentMentor retrieval needs a compact default entry point before opening large Feature files.
- User value: Future agents can find the owning Feature for Research Library, Project chat, evidence admission, and promotion work without relying on chat history.
- Non-goal: This index does not own implementation acceptance for the listed capabilities; each linked Feature remains the source of truth.

## Governance Rule

- `F001` 是项目级 Vision / Scope / umbrella Feature，不再承载所有子能力的详细验收和证据。
- 新 Feature 只为非平凡、可验收、未来需要恢复上下文的能力增量创建。
- 小修复归属已有 Feature 的 `Patch History`，不默认新建 Feature。
- ADR、Evidence、Lesson、spec 和 plan 应从 owning Feature 链接，不把全文复制进 Feature。

## Active Features

| Feature | Domain | Trigger Terms | Owned Paths | Read When |
| --- | --- | --- | --- | --- |
| [F001 Project Vision and Scope](F001-project-vision-and-scope.md) | project vision, product scope, umbrella governance | vision, scope, project direction, ScienceClaw, umbrella, non-goals | `AGENTS.md`; `docs/features/F001-project-vision-and-scope.md`; `docs/specs/F001-feature-map-and-rules-spec.md` | 需要判断项目方向、Feature 是否越界、或某能力是否服务科研工作流时。 |
| [F002 ScienceClaw Baseline Workbench Shell](F002-scienceclaw-baseline-workbench-shell.md) | application shell, UI workbench, service orchestration | ScienceClaw, workbench shell, ActivityPanel, Docker, baseline, chat shell, file panel | `ScienceClaw/`; `docker-compose.yml`; `docker-compose-china.yml`; `docker-compose-release.yml`; `docs/baseline-import-notes.md` | 改 UI 壳、应用编排、工作台基础设施、聊天壳、文件/产物面板前。 |
| [F003 Research Document Ingestion](F003-research-document-ingestion.md) | document ingestion, parsing, canonical paper model | ingestion, upload, paper, parser, GROBID, Docling, PyMuPDF, chunk, source identity | `ScienceClaw/backend/research_assistant/`; `ScienceClaw/backend/tests/test_research_ingestion.py`; `ScienceClaw/backend/tests/test_research_parsers.py` | 改文档摄取、解析、切分、canonical paper model、source identity 前。 |
| [F004 Citation Evidence Boundary](F004-citation-evidence-boundary.md) | evidence eligibility, source identity, context-only boundary | citation evidence, web evidence, database evidence, source identity, context-only, memory boundary | `ScienceClaw/backend/research_assistant/`; `ScienceClaw/frontend/src/`; `AGENTS.md` | 改 citation、source type、memory、证据资格、UI/report 证据措辞前。 |
| [F005 Hybrid Retrieval and Grounded Answering](F005-hybrid-retrieval-grounded-answering.md) | retrieval, answer generation, citation-grounded response | retrieval, pgvector, FTS, answer, citations, no-citation, research answer | `ScienceClaw/backend/research_assistant/`; `ScienceClaw/backend/route/sessions.py`; `ScienceClaw/backend/tests/test_research_retrieval.py`; `ScienceClaw/backend/tests/test_research_answering.py` | 改检索、答案生成、answer API、citation 返回结构或 no-citation 行为前。 |
| [F006 Evidence Audit](F006-evidence-audit.md) | claim checking, audit persistence, trust display | evidence audit, claim checks, support score, unsupported, approved, invalid-source, trust summary | `ScienceClaw/backend/research_assistant/`; `ScienceClaw/frontend/src/`; `ScienceClaw/backend/tests/test_research_reports.py` | 改审计逻辑、Claim Checks、Trust Summary、support score、audit API 或展示前。 |
| [F007 Research Artifact Generation](F007-research-artifact-generation.md) | Markdown report, evidence map, research artifacts | report, markdown artifact, evidence map, sidecar, trust summary, limitations, file panel | `ScienceClaw/backend/research_assistant/`; `ScienceClaw/backend/route/sessions.py`; `workspace/`; `ScienceClaw/backend/tests/test_research_reports.py` | 改报告生成、研究产物、sidecar JSON、文件面板产物或 report wording 前。 |
| [F008 Trace Honesty and Activity Panel](F008-trace-honesty-activity-panel.md) | trace events, ActivityPanel, workflow observability | trace, ActivityPanel, SSE, step events, workflow honesty, failed step, tool validation | `ScienceClaw/backend/route/sessions.py`; `ScienceClaw/frontend/src/`; `ScienceClaw/backend/research_assistant/`; `Tools/` | 改过程事件、UI trace、后端步骤事件、工具验证事件或多 Agent 状态展示前。 |
| [F009 Research Project Library Core](F009-research-project-library-core.md) | project library, research assets, paper upload | Research Library, Research Project, project asset, paper library, upload paper, indexed asset | `ScienceClaw/backend/research_assistant/`; `ScienceClaw/backend/route/`; `ScienceClaw/frontend/src/` | 新增或修改 Research Project、Research Library 页面、Project 下论文资产、Library 上传和资产状态前。 |
| [F010 Project Scoped Chat](F010-project-scoped-chat.md) | project-bound chat, scoped retrieval | project chat, session project, scoped RAG, current project, evidence scope | `ScienceClaw/backend/route/sessions.py`; `ScienceClaw/backend/research_assistant/`; `ScienceClaw/frontend/src/pages/ChatPage.vue` | 修改会话关联 Project、Project-scoped retrieval、Chat 当前 Project 状态或跨 Project 隔离前。 |
| [F011 Evidence Admission Gate](F011-evidence-admission-gate.md) | RAG routing, retrieval threshold, citation admission | evidence gate, top-k threshold, low confidence, abstain, skip RAG, accepted evidence | `ScienceClaw/backend/research_assistant/`; `ScienceClaw/backend/route/sessions.py`; `ScienceClaw/frontend/src/` | 修改 RAG 跳过规则、低相关 evidence 拒绝注入、阈值、检索决策 trace 或 citation admission 前。 |
| [F012 Chat To Library Promotion](F012-chat-to-library-promotion.md) | temporary upload promotion, trusted library ingestion | 加入研究库, promote to library, temporary PDF, chat upload, library action | `ScienceClaw/backend/route/sessions.py`; `ScienceClaw/backend/research_assistant/`; `ScienceClaw/frontend/src/pages/ChatPage.vue` | 修改普通 Chat 上传论文入库边界、回答底部“加入研究库”动作或 promotion trace 前。 |

| [F013 Research Task Router and Whole Paper Summary](F013-research-task-router-whole-paper-summary.md) | task-aware research routing, whole-paper summary | research task router, whole paper summary, summarize this paper, evidence QA, route metadata | `ScienceClaw/backend/research_assistant/`; `ScienceClaw/backend/route/sessions.py`; `ScienceClaw/frontend/src/` | 修改研究问题路由、整篇论文总结、RAG 与 summary workflow 分流、route trace 或回答 metadata 前。 |
| [F015 Session Evidence Boundary](F015-session-evidence-boundary.md) | session evidence, project evidence, temporary upload boundary | session evidence, temporary PDF, project evidence, evidence scope, 加入研究库, chat upload boundary | `ScienceClaw/backend/route/sessions.py`; `ScienceClaw/backend/research_assistant/`; `ScienceClaw/frontend/src/` | 修改 Chat 上传临时材料、Project evidence 边界、promotion eligibility、citation scope metadata 或重复上传反馈前。 |
| [F016 Hierarchical Whole Paper Summary](F016-hierarchical-whole-paper-summary.md) | hierarchical summary, section summary, global synthesis | section summary, global synthesis, whole paper summary, long paper summary, balanced section evidence | `ScienceClaw/backend/research_assistant/answering.py`; `ScienceClaw/backend/research_assistant/storage/database.py`; `ScienceClaw/backend/tests/test_research_answering.py` | 修改整篇论文总结、section-balanced evidence collection、global synthesis 或 summary citation boundary 前。 |
| [F017 LLM Section Summary to Global Synthesis](F017-llm-section-summary-global-synthesis.md) | long-document RAG, LLM section summary, evidence-preserving synthesis | LLM section summary, global synthesis, evidence-preserving synthesis, hierarchical long-document RAG | `ScienceClaw/backend/research_assistant/answering.py`; `ScienceClaw/backend/tests/test_research_answering.py` | 修改单篇整篇论文 LLM synthesis、section summary 中间态、deterministic fallback 或 evidence-preserving summary 逻辑前。 |
| [F018 Claim-Level Citation Audit Calibration](F018-claim-level-citation-audit-calibration.md) | evidence audit calibration, claim-level citation contract | partial claim, structural markdown, audit calibration, claim-level evidence, ActivityPanel audit | `ScienceClaw/backend/research_assistant/audit.py`; `ScienceClaw/backend/research_assistant/reports.py`; `ScienceClaw/frontend/src/components/ActivityPanel.vue`; `ScienceClaw/frontend/src/api/agent.ts` | 修改 Evidence Audit claim 提取、partial/unsupported 状态、报告 audit map、研究证据右侧面板或长耗时 research answer API 前。 |
| [F019 Research Quality Evaluation Harness](F019-research-quality-evaluation-harness.md) | research quality evaluation, citation discipline, answer quality gate | quality gate, eval harness, citation discipline, unsupported ratio, golden eval, answer JSON, results.json, summary.md | `ScienceClaw/backend/research_assistant/evaluation.py`; `ScienceClaw/backend/research_assistant/golden_eval.py`; `ScienceClaw/backend/scripts/research_quality_eval.py`; `ScienceClaw/backend/scripts/research_golden_eval.py`; `ScienceClaw/backend/tests/test_research_evaluation.py`; `ScienceClaw/backend/tests/test_research_golden_eval.py`; `docs/evals/research_golden_cases.json` | 修改研究回答质量断言、真实论文 eval、citation discipline gate、unsupported ratio 阈值、golden case fixture、failure attribution 或 answer JSON 评测 CLI 前。 |
| [F020 Multi-Agent Research Workflow and Subagent Registry](F020-multi-agent-subagent-registry.md) | multi-agent workflow, subagent registry, auditor, reader workers | multi-agent, subagent, auditor agent, reader worker, research agents, agent registry, lifecycle trace | `ScienceClaw/backend/deepagent/`; `ScienceClaw/backend/research_assistant/`; `ScienceClaw/backend/route/sessions.py`; `ScienceClaw/frontend/src/`; `docs/specs/F020-multi-agent-subagent-registry-spec.md` | 修改 Supervisor 委派、多 Agent 决策、Subagent Registry、Auditor Agent、批量 Reader Worker、subagent lifecycle 或 Research Agents 页面前。 |
| [F021 Research Agent Capability Binding](F021-research-agent-capability-binding.md) | research agent capability binding, skill/tool governance | skill binding, tool binding, capability catalog, Research Agents selector, allowed tools, skill refs, chat runtime tool binding | `ScienceClaw/backend/route/sessions.py`; `ScienceClaw/backend/deepagent/agent.py`; `ScienceClaw/backend/deepagent/runner.py`; `ScienceClaw/frontend/src/pages/ResearchAgentsPage.vue`; `ScienceClaw/frontend/src/api/agent.ts`; `ScienceClaw/backend/tests/test_research_session_routes.py`; `ScienceClaw/backend/tests/test_research_tool_runtime.py`; `ScienceClaw/backend/tests/test_research_agents_frontend_contract.py` | 修改 Research Agents 中 custom subagent 的 Skill/Tool 绑定、chat runtime subagent 工具装配、capability catalog、invalid binding 验证或 live UI E2E 前。 |
| [F022 Semantic Evidence Audit and Multi-paper Synthesis](F022-semantic-evidence-audit-and-multi-paper-synthesis.md) | semantic evidence audit, multi-paper synthesis, refusal, golden eval | semantic audit, support_status, finding_code, multi-paper synthesis, insufficient evidence, clinical safety refusal, golden eval A/B | `ScienceClaw/backend/research_assistant/audit.py`; `ScienceClaw/backend/research_assistant/answering.py`; `ScienceClaw/backend/research_assistant/evaluation.py`; `ScienceClaw/backend/research_assistant/golden_eval.py`; `ScienceClaw/backend/scripts/research_ui_e2e.py`; `docs/evals/research_golden_cases.json` | 修改 claim-level semantic audit、多论文综合、insufficient evidence refusal、golden eval semantic cases 或 live UI A/B 验收前。 |

## Planned Feature Candidates

这些候选项来自 `F001` 和 linked spec，但尚不应在没有具体实现入口时全部扩写成 active Feature。

- Three-layer research memory: 开始扩展 L1/L2/L3 memory productization、promotion/revocation/conflict/recall policy 时创建正式 Feature。
- Tools and Skills governance: 开始扩展 domain tool packs、custom tool sandbox validation、skill registry 或持久化治理时创建正式 Feature。

## Lifecycle Notes

- 当前拆分是 `updates` 关系：子 Feature 更新并细化 `F001` 的能力边界，不使 `F001` 失效。
- `docs/specs/F001-feature-map-and-rules-spec.md` 暂时作为 linked spec 保留；只有当 Feature Index 和子 Feature 完整替代它的主动召回作用时，才考虑标记 `superseded`。
## Current Status

Active. This index is the retrieval entry point for active Research Assistant Features.

## Links

- [F001 Project Vision and Scope](F001-project-vision-and-scope.md)
- [EV-001 Feature Governance Split Validation](../evidence/EV-001-feature-governance-split-validation.md)

## Acceptance Criteria

- [x] Active Feature ownership is visible in one compact index.
- [x] New work can be routed to an owning Feature before implementation.
- [x] The index remains compatible with AgentMentor strict validation.

## Patch History

| Patch | Date | Commit | Symptom | Root Cause | Protection | Status |
| --- | --- | --- | --- | --- | --- | --- |
| F000.1 | 2026-06-29 | `515bd25` | Feature Index needed to remain compatible with the current AgentMentor strict validator. | The validator only accepts the canonical artifact kinds and section set. | Strict knowledge validation. | verified |

## Evidence

- `knowledge_check.py --root E:\Self-Project\Research-Assistant --docs-path docs --strict` is the structural validation gate for this index.

## Next Step

Keep this index updated when adding or retiring active Feature ownership.
