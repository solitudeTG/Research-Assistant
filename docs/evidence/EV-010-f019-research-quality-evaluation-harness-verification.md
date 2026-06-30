---
id: EV-010
doc_kind: evidence
scope: project
feature_refs:
  - docs/features/F019-research-quality-evaluation-harness.md
created: 2026-06-30
updated: 2026-06-30
---

# EV-010: F019 Research Quality Evaluation Harness Verification

## Supports Claim

F019 第一版已经完成：系统具备可复用的研究回答质量评测模块，可以对 `ResearchAnswer.to_dict()` payload 做 route、admission、citation boundary、summary synthesis、context boundary 和 audit 指标断言，并提供 CLI 对保存的 answer JSON 做独立校验。

## Verification Scope

- `backend.research_assistant.evaluation` quality gate data model and pass/fail behavior.
- Default gates for `whole_paper_summary`, `evidence_qa`, and `non_evidence_turn`.
- CLI `backend.scripts.research_quality_eval`.
- Regression tests for citation boundary, route mismatch, summary mode mismatch, unsupported ratio, and skipped retrieval.

Not covered:

- Real LLM semantic entailment.
- A curated golden dataset across multiple real papers.
- Live UI answer JSON export integration.
- Automatic threshold tuning.

## Commands

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw;E:\Self-Project\Research-Assistant'; pytest ScienceClaw/backend/tests/test_research_evaluation.py -q --basetemp=.pytest_tmp\f019-eval
```

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw;E:\Self-Project\Research-Assistant'; pytest ScienceClaw/backend/tests -k research -q --basetemp=.pytest_tmp\f019-research-all
```

```powershell
python C:\Users\HUAWEI\.codex\plugins\cache\personal\agentmentor\0.2.0+codex.20260604093000\skills\using-agentmentor\scripts\knowledge_check.py --root E:\Self-Project\Research-Assistant --docs-path docs --strict
```

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw;E:\Self-Project\Research-Assistant'; python -m py_compile ScienceClaw\backend\research_assistant\evaluation.py ScienceClaw\backend\scripts\research_quality_eval.py
```

## Results

Pass.

- `test_research_evaluation.py`: `5 passed`.
- Research backend suite: `206 passed`.
- Verified a valid whole-paper summary gate with `route=whole_paper_summary`, `admission=accepted`, `summary_mode=llm_section_global`, original paper citations, and acceptable unsupported ratio.
- Verified failure when whole-paper summary payload uses `route=evidence_qa`, `summary_mode=deterministic_extractive`, and excessive unsupported claims.
- Verified `source_type=memory` fails the citation boundary gate.
- Verified `general_chat` + `skipped` + zero citations passes the non-evidence turn gate.
- Verified CLI returns exit code `1` and structured findings when a saved answer JSON fails the selected gate.
- AgentMentor validation: `knowledge_check.py --strict` scanned 38 Markdown files with 0 errors and 1 pre-existing warning for `docs/features/INDEX.md` feature id `F000` not reflected in the file name.
- Python compile check for the new evaluation module and CLI: passed.

## Artifacts

- `ScienceClaw/backend/research_assistant/evaluation.py`
- `ScienceClaw/backend/scripts/research_quality_eval.py`
- `ScienceClaw/backend/tests/test_research_evaluation.py`

## Limitations

The harness currently validates observable answer contracts and audit metrics; it does not decide whether a scientific claim is semantically true. Future work should add real-paper golden cases, answer JSON export from live UI/API runs, and possibly an entailment judge once structural quality gates are stable.

## Notes

The first slice intentionally avoids new UI. This keeps the next quality-improvement work grounded in repeatable evidence rather than another ScienceClaw surface.
