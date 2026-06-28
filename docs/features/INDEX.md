---
doc_kind: feature_index
status: active
owner: solitudeTG
created: 2026-06-28
updated: 2026-06-28
---

# Feature Index

本索引是 AgentMentor Feature 的默认召回入口。新会话或新 Agent 不应先通读超大的 `F001`，而应先从这里判断当前任务属于哪个能力边界。

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

## Planned Feature Candidates

这些候选项来自 `F001` 和 linked spec，但尚不应在没有具体实现入口时全部扩写成 active Feature。

- Multi-agent research workflow: 开始实现 Supervisor、Deep Research Agent、Evidence Audit Agent、Document Composer Agent 的真实生命周期时创建正式 Feature。
- Three-layer research memory: 开始扩展 L1/L2/L3 memory productization、promotion/revocation/conflict/recall policy 时创建正式 Feature。
- Tools and Skills governance: 开始扩展 domain tool packs、custom tool sandbox validation、skill registry 或持久化治理时创建正式 Feature。

## Lifecycle Notes

- 当前拆分是 `updates` 关系：子 Feature 更新并细化 `F001` 的能力边界，不使 `F001` 失效。
- `docs/specs/F001-feature-map-and-rules-spec.md` 暂时作为 linked spec 保留；只有当 Feature Index 和子 Feature 完整替代它的主动召回作用时，才考虑标记 `superseded`。
