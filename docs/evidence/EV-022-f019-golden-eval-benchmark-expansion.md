---
id: EV-022
doc_kind: evidence
scope: project
feature_refs:
  - docs/features/F019-research-quality-evaluation-harness.md
created: 2026-07-06
updated: 2026-07-06
---

# EV-022: F019 Golden Eval Benchmark Expansion

## Supports Claim

F019.2 将 golden eval 从 seed/demo 集合扩展为可复现、可演示、可失败归因的 payload benchmark。它仍然基于 ScienceClaw 现有工程底座，不新增工作台 UI，不重写 Research Library / Chat shell。

本次验证支持以下结论：

- `docs/evals/research_golden_cases.json` 覆盖 4 类科研质量场景：`evidence_qa`、`whole_paper_summary`、`multi_paper_synthesis`、`no_evidence_or_insufficient_evidence`。
- payload runner 能继续执行后续 case，不因单个 case 失败中断。
- payload runner 会 preflight case 声明的真实论文 fixture 和 required outputs，避免缺失 `paper_paths` 或 `report_payload_path` 时仍然显示通过。
- runner 输出稳定 artifacts：`results.json`、`summary.md`、case-level `*.answer.json`、case-level `*.quality.json`，失败时还会写 `*.failure.md`。
- 失败 finding 会带稳定 `code`、`message`、`path`、`owner_module_hints` 和可读 `owner_module_hint`，可归因到 F005/F006/F011/F017/F018/F019/F020 等可能 owning module。
- citation evidence 边界保持清晰：citation 仍只允许 `paper` / `web` / `database`；memory、process trace、model reasoning 只能出现在 context boundary 中，不能伪装成 citation evidence。

## Verification Scope

已覆盖：

- 真实论文 fixture：使用 `paper_data/` 下 2 篇真实 PDF。
- Payload golden cases：5 个 payload case 全部通过。
- Live UI case：case 文件中保留 1 个 real-paper `whole_paper_summary` live UI case；本次 F019.2 未复跑 live UI。
- 多论文合成：payload harness 要求至少 2 个 citation 且至少覆盖 2 个 distinct cited papers。
- insufficient evidence：payload harness 要求 admission 为 `rejected` / `insufficient` / `no_evidence` 之一，并且 `max_citation_count=0`，防止无法支持的问题伪造 citation。
- CLI 演示参数：支持 `--payload-dir` 和 `--output-dir`，同时保留旧的 `--output`。
- Review hardening：负测覆盖 `paper_fixture_missing` 和 `required_report_missing`，防止 case schema 只作为描述性字段存在。

未覆盖：

- 未新增第三篇真实论文。
- 未实现 web crawler、PDF/DOCX exporter、LLM entailment judge 或完整多 Agent 综述工作流。
- 未将 live UI 扩展到 evidence QA 或 multi-paper case；live mode 仍是较高成本的部分覆盖路径。

## Case Set

当前 `docs/evals/research_golden_cases.json` 共 6 个 case：

- 1 个 live UI whole-paper summary case：`leo_space_time_summary_live_001`。
- 5 个 payload benchmark case：
  - `leo_space_time_summary_payload_001`
  - `leo_space_time_evidence_qa_payload_001`
  - `leo_integrated_comm_nav_evidence_qa_payload_001`
  - `leo_insufficient_evidence_payload_001`
  - `leo_multi_paper_synthesis_payload_001`

## Checks

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python -m pytest ScienceClaw\backend\tests\test_research_golden_eval.py -q --basetemp .pytest_tmp\f0192-golden
```

Result: Pass, `8 passed, 1 warning`.

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python ScienceClaw\backend\scripts\research_golden_eval.py --cases docs\evals\research_golden_cases.json --payload-dir docs\evals\payloads --output-dir .pytest_tmp\f0192-golden-output
```

Result: Pass, `cases=5 passed=5 failed=0`.

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python -m pytest ScienceClaw\backend\tests\test_research_evaluation.py -q --basetemp .pytest_tmp\f0192-eval
```

Result: Pass, `5 passed`.

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python -m pytest ScienceClaw\backend\tests -k "research_golden_eval or research_evaluation or research_answering or research_audit" -q --basetemp .pytest_tmp\f0192-focused
```

Result: Pass, `47 passed, 220 deselected, 107 warnings`.

Review-hardening checks after external review:

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python -m pytest ScienceClaw\backend\tests\test_research_golden_eval.py -q --basetemp .pytest_tmp\f0192-review-golden
```

Result: Pass, `11 passed, 1 warning`.

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python ScienceClaw\backend\scripts\research_golden_eval.py --cases docs\evals\research_golden_cases.json --payload-dir docs\evals\payloads --output-dir .pytest_tmp\f0192-review-golden-output
```

Result: Pass, `cases=5 passed=5 failed=0`.

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python -m pytest ScienceClaw\backend\tests\test_research_evaluation.py -q --basetemp .pytest_tmp\f0192-review-eval
```

Result: Pass, `5 passed`.

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python -m pytest ScienceClaw\backend\tests -k "research_golden_eval or research_evaluation or research_answering or research_audit" -q --basetemp .pytest_tmp\f0192-review-focused
```

Result: Pass, `50 passed, 220 deselected, 107 warnings`.

```powershell
python C:\Users\HUAWEI\.codex\skills\using-agentmentor\scripts\knowledge_check.py --root E:\Self-Project\Research-Assistant --docs-path docs --strict
```

Result: Pass after this Evidence was updated to include the required standard sections and AgentMentor validation record.

```powershell
python C:\Users\HUAWEI\.codex\skills\using-agentmentor\scripts\knowledge_check.py --root E:\Self-Project\Research-Assistant --docs-path docs --feature-index docs\features\F019-research-quality-evaluation-harness.md
```

Result: Pass, `Errors: 0`, `Warnings: 0`.

After F019.3 review hardening, strict validation initially failed because F019 reached 3 Patch History rows without a `## Patch Churn Review`. The Feature now records that review and both validators pass:

```powershell
python C:\Users\HUAWEI\.codex\skills\using-agentmentor\scripts\knowledge_check.py --root E:\Self-Project\Research-Assistant --docs-path docs --strict
```

Result: Pass, `Errors: 0`, `Warnings: 0`.

```powershell
python C:\Users\HUAWEI\.codex\skills\using-agentmentor\scripts\knowledge_check.py --root E:\Self-Project\Research-Assistant --docs-path docs --feature-index docs\features\F019-research-quality-evaluation-harness.md
```

Result: Pass, `Errors: 0`, `Warnings: 0`.

## Results

Pass.

- Golden eval focused tests: `8 passed, 1 warning`.
- Payload benchmark command: `cases=5 passed=5 failed=0`.
- Research evaluation focused tests: `5 passed`.
- Related focused suite: `47 passed, 220 deselected, 107 warnings`.
- Review-hardening golden eval focused tests: `11 passed, 1 warning`.
- Review-hardening payload benchmark command: `cases=5 passed=5 failed=0`.
- Review-hardening focused suite: `50 passed, 220 deselected, 107 warnings`.
- AgentMentor strict validation: Pass.
- F019 Feature Index validation: Pass.
- F019 Patch Churn Review: Added after F019.3 because Patch History reached 3 rows; strict validation passes afterward.

## Artifacts

- `.pytest_tmp/f0192-golden-output/results.json`
- `.pytest_tmp/f0192-golden-output/summary.md`
- `.pytest_tmp/f0192-review-golden-output/results.json`
- `.pytest_tmp/f0192-review-golden-output/summary.md`
- `.pytest_tmp/f0192-golden-output/cases/leo_space_time_summary_payload_001.answer.json`
- `.pytest_tmp/f0192-golden-output/cases/leo_space_time_summary_payload_001.quality.json`
- `.pytest_tmp/f0192-golden-output/cases/leo_space_time_evidence_qa_payload_001.answer.json`
- `.pytest_tmp/f0192-golden-output/cases/leo_space_time_evidence_qa_payload_001.quality.json`
- `.pytest_tmp/f0192-golden-output/cases/leo_integrated_comm_nav_evidence_qa_payload_001.answer.json`
- `.pytest_tmp/f0192-golden-output/cases/leo_integrated_comm_nav_evidence_qa_payload_001.quality.json`
- `.pytest_tmp/f0192-golden-output/cases/leo_insufficient_evidence_payload_001.answer.json`
- `.pytest_tmp/f0192-golden-output/cases/leo_insufficient_evidence_payload_001.quality.json`
- `.pytest_tmp/f0192-golden-output/cases/leo_multi_paper_synthesis_payload_001.answer.json`
- `.pytest_tmp/f0192-golden-output/cases/leo_multi_paper_synthesis_payload_001.quality.json`

## Notes

Payload benchmark run:

- `case_count=5`
- `passed_count=5`
- `failed_count=0`
- Multi-paper metrics include `distinct_cited_paper_count=2` and `distinct_cited_papers=["paper-comm-nav", "paper-space-time"]`.
- Insufficient evidence metrics include `admission="rejected"` and `citation_count=0`.
- Review feedback P1 was reproduced as a test-level failure mode and fixed with `paper_fixture_missing`.
- Review feedback P2 was reproduced as a test-level failure mode and fixed with `required_report_missing`.

Warnings:

- The focused suite still reports existing Python 3.14 / Pydantic V1 compatibility warnings and FastAPI deprecation warnings. They are not introduced by F019.2.

## Limitations

这份 Evidence 支持“payload benchmark 已经可复现、可演示、可失败归因”。它不支持“live UI 已完整覆盖所有 golden case”。

面试展示建议默认跑 payload benchmark 和 focused tests；如果要展示端到端 UI 能力，再单独跑 EV-018 记录过的 live UI case，并说明 live mode 当前只覆盖 whole-paper summary。
