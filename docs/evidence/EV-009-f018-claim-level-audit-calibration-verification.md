---
id: EV-009
doc_kind: evidence
scope: project
feature_refs:
  - docs/features/F018-claim-level-citation-audit-calibration.md
created: 2026-06-30
updated: 2026-06-30
---

# EV-009: F018 Claim-Level Audit Calibration Verification

## Supports Claim

F018 已完成：Evidence Audit 可以过滤结构性 Markdown 行，将有明确合法 citation 但仅部分支持的综合 claim 标记为 `partial`，并在 ScienceClaw 风格的右侧 ActivityPanel 中展示 `approved / partial / unsupported / invalid` 摘要；真实 UI 上传论文、索引、整篇总结和审计展示链路可运行。

## Verification Scope

- Backend audit extraction and classification.
- Report/evidence-map compatibility with `partial` audit claims.
- Frontend type contract and ActivityPanel audit sidecar.
- Research long-running API timeout for whole-paper LLM synthesis.
- Live UI E2E with a real PDF from `paper_data`.

Not covered:

- Full semantic entailment or contradiction detection.
- Multi-paper synthesis or Multi-Agent workflow.
- Source-quality scoring beyond F004/F006 identity and audit boundaries.

## Checks

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant;E:\Self-Project\Research-Assistant\ScienceClaw'; pytest ScienceClaw/backend/tests/test_research_audit.py ScienceClaw/backend/tests/test_research_reports.py ScienceClaw/backend/tests/test_research_frontend_contracts.py ScienceClaw/backend/tests/test_research_repository.py ScienceClaw/backend/tests/test_research_database.py -q --basetemp=.pytest_tmp\f018-focused2
```

```powershell
npm.cmd run type-check
```

```powershell
docker compose restart frontend
```

```powershell
python -X utf8 .pytest_tmp\f018_live_ui_e2e.py
```

```powershell
python C:\Users\HUAWEI\.codex\plugins\cache\personal\agentmentor\0.2.0+codex.20260604093000\skills\using-agentmentor\scripts\knowledge_check.py --root E:\Self-Project\Research-Assistant --docs-path docs --strict
```

## Results

Pass.

- Focused backend/frontend-contract tests: `98 passed`.
- Frontend type-check: passed.
- Live UI E2E session: `VF4dznundABJFzgify5M9B`.
- Real PDF: `paper_data\Beamforming_Design_and_Satellite_Selection_for_Realizing_the_Integrated_Communication_and_Navigation_in_LEO_Satellite_Networks.pdf`.
- Upload route: `POST /api/v1/sessions/VF4dznundABJFzgify5M9B/upload`.
- Research answer route: `POST /api/v1/sessions/VF4dznundABJFzgify5M9B/research/answer` with `model_config_id=system-default`.
- Indexed status: `paper_count=1`, `chunk_count=24`, `has_indexed_papers=true`.
- Research route: `whole_paper_summary`.
- Summary mode: `llm_section_global`.
- Citation count: `24`.
- Audit result: `status=partial`, `claim_count=30`, `approved=13`, `partial=2`, `unsupported=15`, `invalid=0`.
- Structural `Global synthesis` heading audited as claim: `false`.
- Right panel had audit summary and partial counter: `true`.
- Right panel showed `推理完成`, not `推理失败`: `panel_has_reasoning_failed=false`.
- AgentMentor validation: `knowledge_check.py --strict` scanned 36 Markdown files with 0 errors and 1 pre-existing warning for `docs/features/INDEX.md` feature id `F000` not reflected in the file name.

## Artifacts

- Live UI result JSON: `.pytest_tmp\f018-live-ui-result.json`
- Live UI screenshot: `.pytest_tmp\f018-live-ui.png`

## Limitations

F018 calibrates the audit heuristic; it does not prove every synthesis sentence is semantically entailed. The live run still had unsupported claims because some generated synthesis claims were broader than the cited quote overlap or lacked enough direct support. That is a valid audit signal and should be addressed by a later output-shaping or entailment-evaluation slice, not hidden in UI.

## Notes

`partial` is a warning state. It does not make generated summaries citation evidence and does not relax the F004 rule that only paper, web, or database evidence can be cited.
