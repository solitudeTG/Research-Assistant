---
id: ADR-001
doc_kind: adr
status: accepted
scope: project
owner: solitudeTG
feature_refs: [docs/features/F001-project-vision-and-scope.md]
decision_area: p0-research-data-and-retrieval-stack
created: 2026-06-19
updated: 2026-06-28
feature_ids: [F001]
---

# ADR-001: P0 Research Data and Retrieval Stack

## Context

Research Assistant 的 P0 目标是完成一条可验证的论文研究闭环：上传论文，解析并索引，基于论文提出问题，返回可追溯 citation evidence，展示真实 trace，并生成 Markdown 研究产物。

该场景的核心输入主要是论文和研究文档，而不是任意文件聊天。论文文献需要保留标题、作者、摘要、章节、页码、段落、参考文献、图表说明和 citation 上下文等结构信息。系统不能只抽取纯文本后直接进入向量库，否则后续 citation、Evidence Audit 和报告 evidence map 会缺少可靠的来源边界。

ScienceClaw baseline 当前包含 MongoDB 等既有应用壳存储能力；Research Assistant 目标栈包含 PostgreSQL + pgvector。需要明确研究领域数据的长期主存储，避免把 paper / evidence / citation / audit / memory 分散在不一致的数据系统中。

## Decision

P0 采用以下长期技术方向：

- 文档解析：GROBID 作为论文 PDF 主解析栈，Docling 和 PyMuPDF 作为 fallback。
- 文档模型：建立 Research Assistant 自有 canonical paper model，不把业务逻辑绑定到任何单一 parser 的原始输出。
- 检索：P0 从第一版开始做 hybrid retrieval，而不是先做 vector-only。
- 检索实现：PostgreSQL full-text search + pgvector，使用 RRF 或简单加权融合；reranker 留作 P1/P2 增强。
- 报告产物：P0 只要求 Markdown，必要时用 frontmatter 或 sidecar JSON 保存 evidence map。
- Web search：P0 延后，先聚焦 uploaded papers，后续作为第二类 evidence source 接入同一套 evidence contract。
- 存储边界：PostgreSQL + pgvector 是 Research Assistant 研究领域主存储；MongoDB 暂保留给 ScienceClaw baseline 壳的既有用户、会话、配置和任务等 operational data。

## Rationale

GROBID 面向 scholarly documents，适合提取论文元数据、参考文献和章节结构。Docling/PyMuPDF 适合作为通用文档、OCR、表格或异常 PDF 的降级路径。主解析栈应服务论文研究场景，而不是只满足“能读 PDF”的 demo 需求。

Hybrid retrieval 对科研场景是基础能力。研究问题经常依赖方法名、术语、数据集名、作者、年份、编号和 citation marker；这些信号不能只依赖 embedding。P0 直接建立 PostgreSQL full-text search + pgvector 的组合，可以在不引入额外搜索基础设施的情况下，同时保留 lexical 和 semantic evidence recall。

Markdown 是 P0 报告产物的合适边界。它足以表达结构化研究结果，并且便于附带 evidence map。DOCX/PDF 应作为后续 exporter，而不是阻塞 P0 的核心证据闭环。

Web search 会引入网页可信度、快照、版本、爬取失败、搜索污染和跨来源证据治理。P0 延后 web search 可以保持 evidence boundary 清晰，先把 uploaded papers 的闭环做实。

PostgreSQL + pgvector 更适合作为 paper/chunk/evidence/citation/audit/report/memory 的关系化研究领域存储。MongoDB 不应继续扩展为研究证据系统，但为了继承 ScienceClaw application shell，不需要在 P0 迁移既有 shell 数据。

## Consequences

- P0 ingestion 需要包含 parser adapter 层和 canonical paper model。
- P0 数据库设计必须同时支持 chunks、embedding、full-text index、source identity、page/section 定位和 evidence records。
- Citation evidence 必须从 canonical paper model 和 chunk/evidence records 中产生，而不是从 LLM 摘要或 tool logs 中产生。
- MongoDB 相关既有功能可以继续运行，但新增 Research Assistant 核心领域数据不得默认写入 MongoDB。
- 未来接入 web/database evidence 时，必须复用同一套 evidence contract，而不是另建一套 citation 语义。

## Decision Boundary

This ADR governs the P0 research-domain stack: scholarly PDF parsing, canonical paper artifacts, PostgreSQL/pgvector storage, hybrid retrieval, citation evidence contracts, and Markdown report evidence maps. It does not decide later report exporters, full web-search/crawl ingestion, live database connector execution, multi-agent orchestration, or model-provider selection beyond preserving the citation-evidence boundary.

## Alternatives

- Pure lightweight PDF/text extraction as primary path: rejected because it loses scholarly structure and weakens citation/evidence audit.
- Vector-only P0 retrieval: rejected because科研术语、名称、年份、编号和 citation marker 对 lexical retrieval 依赖很强。
- First-version DOCX/PDF reports: rejected because会把 P0 从 evidence闭环拉向格式导出，Markdown 已足够承载可追溯研究产物。
- P0 web search: rejected because会过早扩大来源治理复杂度。
- MongoDB as research evidence store: rejected because paper/chunk/evidence/citation/audit 需要关系化约束、全文检索和向量检索协同。

## Evidence

- Feature anchor: [F001 Project Vision and Scope](../features/F001-project-vision-and-scope.md)。
- Product rules and P0 boundary: [F001 Feature Map and Rules Spec](../specs/F001-feature-map-and-rules-spec.md)。
- User decision on 2026-06-19: accepted GROBID primary parser, Docling/PyMuPDF fallback, PostgreSQL full-text search + pgvector hybrid retrieval, Markdown reports, deferred web search, and PostgreSQL research domain storage.

## Follow-up

- 在 P0 paper ingestion 设计中定义 canonical paper model。
- 在 P0 schema 设计中明确 PostgreSQL 表、pgvector 字段、full-text index 和 evidence record contract。
- 在后续 Feature 中决定是否把 Docling 作为非 PDF/复杂 PDF 的 secondary parser，还是仅作为 degraded fallback。

## Rejected Options

- Pure lightweight PDF/text extraction as the primary path, because it loses scholarly structure and weakens citation/evidence audit.
- Vector-only P0 retrieval, because research terminology, names, years, identifiers, and citation markers need lexical recall.
- First-version DOCX/PDF report export, because it would move P0 away from the evidence loop into formatting/export complexity.
- P0 web search as the first source path, because source reliability, snapshots, crawling failure, search contamination, and provenance governance would expand the initial risk surface.
- MongoDB as the research evidence store, because paper/chunk/evidence/citation/audit data needs relational constraints, full-text search, and vector retrieval in one research-domain store.

## Before Changing This Decision

- Update [F001 Project Vision and Scope](../features/F001-project-vision-and-scope.md) with the changed capability boundary and verification evidence.
- Prove the replacement still keeps citation evidence separate from memory, model reasoning, process trace, and tool logs.
- Provide a migration or rollback path for existing PostgreSQL research-domain data before changing the storage boundary.
- Run focused research storage/retrieval/report tests plus the AgentMentor strict knowledge check.
