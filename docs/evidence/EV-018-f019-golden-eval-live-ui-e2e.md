---
id: EV-018
doc_kind: evidence
scope: project
feature_refs:
  - docs/features/F019-research-quality-evaluation-harness.md
created: 2026-07-04
updated: 2026-07-04
---

# EV-018: F019 Golden Eval Live UI E2E

## Supports Claim

F019 已从第一版的 saved answer JSON quality gate，扩展为可以运行真实论文 golden eval 的验证闭环：同一套 gate 可以覆盖 deterministic payload cases，也可以驱动 live UI 登录、创建 session、通过 UI 上传论文、等待索引、请求真实 answer/report、保存 answer/report/quality artifacts，并把质量失败映射回 F017/F006 等上游缺口。

最终验收结果支持：payload golden eval 通过，真实 live UI golden eval 通过，且 `results.json` 可被机器读取并指向独立 answer/report/quality artifacts。

## Verification Scope

已覆盖：

- Golden eval case loader、case-level thresholds、batch summary、JSON/Markdown 输出。
- Payload mode：5 个 deterministic golden cases，覆盖 whole-paper summary、evidence QA、insufficient evidence、multi-paper synthesis。
- Live UI mode：使用真实 PDF，通过浏览器登录 Research Assistant，创建 chat session，上传论文，等待 indexing，调用真实 answer/report API，收集 trace/files，并保存 answer/report/quality artifacts。
- F019 gate 与既有 `evaluate_research_answer` / `ResearchQualityRequirement` 复用，避免出现另一套不可追溯质量规则。

未覆盖：

- 当前仓库只有 2 个真实 PDF 可用，未达到最初设想的 3 篇真实论文覆盖。
- Live UI harness 当前通过 UI 完成登录、session、文件上传和索引等待，但问题输入与 answer/report 生成走同源浏览器 API，不是人工键入 composer。
- 本次不引入 dashboard、LLM judge、web crawler 或新的评测平台 UI。

## Checks

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python -m pytest ScienceClaw\backend\tests\test_research_golden_eval.py -q --basetemp .pytest_tmp\golden-eval-green1
```

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python -m backend.scripts.research_golden_eval --cases docs\evals\research_golden_cases.json --mode payload --output workspace\research_eval\payload-smoke
```

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python -m pytest ScienceClaw\backend\tests\test_research_golden_eval.py ScienceClaw\backend\tests\test_research_evaluation.py ScienceClaw\backend\tests\test_research_ui_e2e_script.py -q --basetemp .pytest_tmp\golden-eval-focused
```

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python -m backend.scripts.research_golden_eval --cases docs\evals\research_golden_cases.json --mode live-ui --output workspace\research_eval\live-ui --frontend-url http://127.0.0.1:5173 --api-base-url http://127.0.0.1:5173/api/v1 --timeout-ms 240000
```

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python -m backend.scripts.research_golden_eval --cases docs\evals\research_golden_cases.json --mode live-ui --output workspace\research_eval\live-ui-final2 --frontend-url http://127.0.0.1:5173 --api-base-url http://127.0.0.1:5173/api/v1 --timeout-ms 240000
```

```powershell
python - <<'PY'
import json
from pathlib import Path
data = json.loads(Path('workspace/research_eval/live-ui-final2/results.json').read_text(encoding='utf-8'))
case = data['cases'][0]
print(data['run_id'], data['passed_count'], data['failed_count'], data['passed'])
print(case['answer_payload_path'])
print(case['report_payload_path'])
print(case['answer_payload'] is None, case['report_payload'] is None)
print(case['quality']['metrics'])
PY
```

```powershell
python C:\Users\HUAWEI\.codex\skills\using-agentmentor\scripts\knowledge_check.py --root E:\Self-Project\Research-Assistant --docs-path docs --strict
```

## Results

Pass.

- Focused unit tests: Pass，`5 passed`。
- Payload golden eval smoke: Pass，`cases=5 passed=5 failed=0`。
- Focused regression suite after artifact serialization fix: Pass，`14 passed`，保留 1 个既有 LangChain/Python 3.14 warning。
- Final live UI E2E: Pass，session `X9jQZ2sgEnc3P7VE7ZKMun` 成功完成登录、session 创建、PDF 上传、索引等待、answer/report 生成、trace/files 收集和 artifact 保存。
- Final live UI quality gate: Pass，`cases=1 passed=1 failed=0`。
- Final `results.json` parse check: Pass，`answer_payload` / `report_payload` 不再内嵌完整 payload，只保留独立 artifact 路径。
- AgentMentor validation: Pass，final `knowledge_check.py --strict` scanned 50 Markdown files and checked 38 knowledge artifacts with `Errors: 0` and `Warnings: 0`. An earlier strict run exposed stale F018/EV009/EV010 template drift; those structural issues were fixed without changing their technical claims.

最终 live metrics：

- `route=whole_paper_summary`
- `admission=accepted`
- `citation_count=19`
- `summary_mode=llm_section_global`
- `claim_count=9`
- `approved_claim_count=0`
- `partial_claim_count=6`
- `unsupported_claim_count=3`
- `invalid_source_count=0`
- `unsupported_claim_ratio=0.3333`
- `citation_source_types=["paper"]`
- `citation_evidence_scopes=["session"]`

## Artifacts

- `ScienceClaw/backend/research_assistant/golden_eval.py`
- `ScienceClaw/backend/scripts/research_golden_eval.py`
- `ScienceClaw/backend/tests/test_research_golden_eval.py`
- `docs/evals/research_golden_cases.json`
- `docs/evals/payloads/`
- `docs/superpowers/specs/2026-07-04-research-golden-eval-live-ui-design.md`
- `docs/superpowers/plans/2026-07-04-research-golden-eval-live-ui.md`
- `workspace/research_eval/payload-smoke/summary.md`
- `workspace/research_eval/payload-smoke/results.json`
- `workspace/research_eval/live-ui/summary.md`
- `workspace/research_eval/live-ui/results.json`
- `workspace/research_eval/live-ui/cases/leo_space_time_summary_live_001.answer.json`
- `workspace/research_eval/live-ui/cases/leo_space_time_summary_live_001.quality.json`
- `workspace/research_eval/live-ui/cases/leo_space_time_summary_live_001.report.json`
- `workspace/research_eval/live-ui-final2/summary.md`
- `workspace/research_eval/live-ui-final2/results.json`
- `workspace/research_eval/live-ui-final2/cases/leo_space_time_summary_live_001.answer.json`
- `workspace/research_eval/live-ui-final2/cases/leo_space_time_summary_live_001.quality.json`
- `workspace/research_eval/live-ui-final2/cases/leo_space_time_summary_live_001.report.json`

## Limitations

这份 Evidence 支持“golden eval + live UI E2E gate 已接入，并且当前单篇 whole-paper live golden case 通过质量门”。它不支持“所有论文、所有研究任务、所有 LLM 运行都稳定达标”。

当前 golden set 受 `paper_data/` 现有文件限制，只覆盖 2 个真实 PDF。后续若要更接近面试展示或长期回归，需要补第 3 篇真实论文，并把 live case 扩展到更多任务类型。

## Notes

中间一次 live run 曾失败，暴露 `deterministic_extractive` fallback 和 unsupported ratio 过高；最终复跑通过，说明当前 live 质量存在一定运行波动。不要因此放宽 gate。下一步更有价值的是扩大 golden set 和提升稳定性，而不是继续堆 UI。
