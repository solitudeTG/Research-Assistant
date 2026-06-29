---
id: EV-001
doc_kind: evidence
scope: project
feature_refs:
  - docs/features/F001-project-vision-and-scope.md
  - docs/features/F002-scienceclaw-baseline-workbench-shell.md
  - docs/features/F003-research-document-ingestion.md
  - docs/features/F004-citation-evidence-boundary.md
  - docs/features/F005-hybrid-retrieval-grounded-answering.md
  - docs/features/F006-evidence-audit.md
  - docs/features/F007-research-artifact-generation.md
  - docs/features/F008-trace-honesty-activity-panel.md
created: 2026-06-28
---

# EV-001: Feature Governance Split Validation

## Supports Claim

本 Evidence 支撑以下治理完成声明：当前项目的 AgentMentor Feature 资产已经从单一大型 `F001` 入口，拆分为一个 Feature Index、一个 umbrella Feature 和第一批 P0 子能力 Feature，并通过 AgentMentor 结构校验与局部 Feature Index 校验。

## Verification Scope

本次验证覆盖 `docs/features` 下的 AgentMentor Feature 治理结构：

- 新增 `docs/features/INDEX.md` 作为默认 Feature 召回入口。
- 保留 `F001` 作为项目级 Vision / Scope / umbrella Feature。
- 新增 `F002` 到 `F008` 作为 P0 子能力恢复入口。
- 验证 AgentMentor Markdown artifact 结构。
- 验证每个新增 Feature 在 Feature Index 中可被局部召回。

本次验证不覆盖业务代码行为、Research Assistant 运行时功能、浏览器 E2E、LLM provider、数据库迁移或报告生成正确性。

## Commands

```text
python C:\Users\HUAWEI\.codex\skills\using-agentmentor\scripts\knowledge_check.py --root E:\Self-Project\Research-Assistant --docs-path docs --strict

foreach ($file in 'docs/features/F002-scienceclaw-baseline-workbench-shell.md','docs/features/F003-research-document-ingestion.md','docs/features/F004-citation-evidence-boundary.md','docs/features/F005-hybrid-retrieval-grounded-answering.md','docs/features/F006-evidence-audit.md','docs/features/F007-research-artifact-generation.md','docs/features/F008-trace-honesty-activity-panel.md') {
  python C:\Users\HUAWEI\.codex\skills\using-agentmentor\scripts\knowledge_check.py --root E:\Self-Project\Research-Assistant --docs-path docs --feature-index $file
}
```

## Checks

## Results

Pass.

- Strict knowledge check: scanned 13 markdown files, checked 9 knowledge artifacts, errors 0, warnings 0.
- Feature Index local checks for `F002` through `F008`: each scanned 13 markdown files, checked 9 knowledge artifacts, errors 0, warnings 0.

## Artifacts

- [Feature Index](../features/INDEX.md)
- [F001 Project Vision and Scope](../features/F001-project-vision-and-scope.md)
- [F002 ScienceClaw Baseline Workbench Shell](../features/F002-scienceclaw-baseline-workbench-shell.md)
- [F003 Research Document Ingestion](../features/F003-research-document-ingestion.md)
- [F004 Citation Evidence Boundary](../features/F004-citation-evidence-boundary.md)
- [F005 Hybrid Retrieval and Grounded Answering](../features/F005-hybrid-retrieval-grounded-answering.md)
- [F006 Evidence Audit](../features/F006-evidence-audit.md)
- [F007 Research Artifact Generation](../features/F007-research-artifact-generation.md)
- [F008 Trace Honesty and Activity Panel](../features/F008-trace-honesty-activity-panel.md)

## Limitations

本 Evidence 只证明文档资产治理结构可被 AgentMentor 校验和召回。它不能证明 F002-F008 对应的业务能力全部完成，也不能替代后续每个 Feature 的 focused verification evidence。

当前 `F001` 仍保留大量历史 Acceptance Map 和 Evidence 聚合。后续治理应按能力边界逐步把具体业务验证证据迁移到 owning Feature，而不是一次性移动造成溯源断裂。

## Notes

本次治理采用 `updates` 关系：F002-F008 细化并更新 F001 的能力边界，但不 supersede F001。`docs/specs/F001-feature-map-and-rules-spec.md` 继续作为 linked spec 保留。
