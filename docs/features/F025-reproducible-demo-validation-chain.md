---
id: F025
doc_kind: feature
status: completed
owner: solitudeTG
created: 2026-07-07
updated: 2026-07-07
---

# F025: Reproducible Demo Validation Chain

## Goal

把 F019/F022/F023/F024 已有能力组织成一个可一键复现、可验收、可面试展示的 Demo / Validation 链路。F025 不新增研究业务能力，不重写 ScienceClaw UI，而是提供统一 runner、真实 golden corpus、live UI 调用、机器可读结果和人类可读总结。

## Vision Anchor

- Source: 用户要求第三个 90%+ 完整度缺口：真实 Golden Eval Corpus + 一键复现 Demo/验证链。
- User pain point: 已有能力分散在 focused tests、payload golden eval、live Case C、live Case D 和 Evidence 文档中；面试或验收时缺少一个命令证明“当前核心能力能从环境预检跑到最终报告”。
- Desired outcome: 一个 repo 内脚本输出 `results.json`、`summary.md`、`commands.json`、`environment.json` 和分步骤 artifact，覆盖 quick/live/full 模式，并诚实区分 pass / fail / skipped / blocked。
- Non-goals: 不实现新的研究能力；不做三层记忆产品化；不重写 F024 literature review；不引入新 UI shell；不把 optional/skipped LLM Case C 写成 passed；不放松 demo 断言；不提交 `.pytest_tmp`。
- Exit Gate source: 本 Feature、EV-026、focused pytest、payload golden eval、quick/full validation artifacts、AgentMentor strict 与 F025 feature-index 检查。

## Feature Intake

- Original problem: F019/F022/F023/F024 已分别完成，但验收链条仍散落，无法用一条命令复现环境预检、fixture 检查、测试、payload eval、live UI smoke、Case C、Case D 和最终报告。
- User pain point: 面试展示需要可运行、可断言、可追溯的能力增量，而不是口头说“这些能力都做过”。
- Capability promise: `research_demo_validation.py` 提供 quick/live/full 模式，调用现有脚本和真实 UI E2E，聚合状态和关键指标，保留 optional LLM blocked 状态。
- Non-goals: 不改 ScienceClaw app shell，不发明 ActivityPanel/Agent/tool 事件，不把 memory/tool logs/model reasoning 当 citation，不把 live UI 失败改成 direct API 成功。
- Acceptance source: 用户 2026-07-07 F025 任务说明中的命令接口、输出 shape、golden corpus 扩展、live UI 验收和质量门要求。
- Open questions: F023 live Case C 依赖当前模型额度/权限；本次 full 运行中 `qwen3.7-plus` 返回 `PermissionDeniedError`，因此 Case C 作为 optional blocked 记录。

## Capability Contract

- `ScienceClaw/backend/scripts/research_demo_validation.py` 支持 `--mode quick|live|full`。
- quick 模式执行环境预检、F024 corpus/fixture 检查、focused tests、payload golden eval，不跑 live UI。
- live 模式执行环境预检、F024 corpus/fixture 检查、live health、live UI smoke、F024 Case D，并按 `--llm-case-c` 处理 F023 Case C。
- full 模式执行 quick + live。
- `--llm-case-c required` 要求 Case C 产出 `semantic_auditor.mode=llm_enhanced`，否则 overall 为 blocked/fail。
- `--llm-case-c optional` 允许模型权限/额度失败记录为 blocked，并使 overall 为 partial；不能把 F023 live LLM 写成 passed。
- `--llm-case-c skip` 记录 skipped，并在 summary 中说明未验证 live LLM auditor。
- 输出目录固定包含 `results.json`、`summary.md`、`commands.json`、`environment.json`、`golden-eval/`、`focused-tests/`、`live-ui-smoke/`、`case-d-literature-review-7paper/`、`artifacts/`，required/optional Case C 时包含 `case-c-semantic-auditor/`。
- `results.json` 顶层记录 run id、时间、mode、overall status、steps、golden/focused/live/case_c/case_d/corpus/environment。
- Golden corpus 新增 F025 payload cases，覆盖 method/limitation summary、multi-citation QA、insufficient-evidence refusal、literature-review negative gate。
- Literature-review negative case 使用 `expected_result=fail`，要求底层 quality gate 实际失败；主 golden eval 只有在该失败被观察到时才通过。

## Decision Context

### Why

F025 的价值不在新增回答能力，而在把能力变成可复现验收链。Agent 时代的风险不是代码写不出来，而是状态不可验收、失败不可定位、demo 与真实产品路径脱节。

### Why Not

没有另起 UI/Workbench，因为 ScienceClaw 已经提供 Chat、ActivityPanel、file/artifact panel、SSE trace 和 report path。没有用 direct API 替代 live UI，因为 F024/F023 的验收要求是真实浏览器、Chat textarea 和真实 artifact。没有把 Case C optional blocked 算作 pass，因为 LLM auditor 是 F023 的独立验收面。

### If Modifying This Area, Check

- F004 Citation Evidence Boundary。
- F019 Research Quality Evaluation Harness。
- F022 Semantic Evidence Audit and Multi-paper Synthesis。
- F023 LLM Semantic Auditor。
- F024 Evidence Matrix Literature Review。
- EV-026 verification artifacts。

## Current Status

Completed with an explicit optional LLM limitation. Quick validation passes. Full validation generated complete results/summary and passed live UI smoke plus F024 Case D. Full `overall_status=partial` because optional F023 Case C reached real UI but live model returned `PermissionDeniedError`, yielding `semantic_auditor.mode=llm_failed`; this is recorded as blocked, not passed. Review hardening now guarantees non-Case-C blocked steps such as live health, required live UI smoke, or required Case D produce `overall_status=blocked` instead of `partial`.

## Links

### Evidence

- [EV-026 Reproducible Demo Validation Chain Verification](../evidence/EV-026-reproducible-demo-validation-chain-verification.md)

### Decisions / ADRs

- None.

### Lessons

- None yet.

### Specs / Plans

- None. The user request provided the accepted task boundary and command interface.

### External Context

- Local live UI used `http://127.0.0.1:5180` and `http://127.0.0.1:5180/api/v1`.
- F024 corpus path: `paper_data/f024_7paper_corpus/manifest.json`.

### Related Features

- [F019 Research Quality Evaluation Harness](F019-research-quality-evaluation-harness.md)
- [F022 Semantic Evidence Audit and Multi-paper Synthesis](F022-semantic-evidence-audit-and-multi-paper-synthesis.md)
- [F023 LLM Semantic Auditor](F023-llm-semantic-auditor.md)
- [F024 Evidence Matrix Literature Review](F024-evidence-matrix-literature-review.md)

## Acceptance Criteria

- [x] `research_demo_validation.py --mode quick` 生成完整 summary/results 并 overall pass。
- [x] full 模式生成完整 summary/results，live UI smoke pass，F024 Case D pass。
- [x] F023 Case C optional 策略诚实记录 blocked；未把 `llm_failed` 写成 passed。
- [x] Focused pytest 通过。
- [x] Payload golden eval 通过，新增 F025 cases 生效。
- [x] Literature-review negative case 的底层 quality gate 实际失败，并由 `expected_result=fail` 保护主 benchmark。
- [x] F024 live UI Case D 真实上传/选择 7 篇 PDF，经 Chat textarea 发送并生成 matrix/report artifact。
- [x] `results.json` / `summary.md` 区分 pass / fail / skipped / blocked / partial。
- [x] AgentMentor strict 与 F025 feature-index 检查通过。

## Acceptance Map

| Claim | Acceptance | Evidence | Status |
| --- | --- | --- | --- |
| One-command quick validation works. | Quick mode runs precheck, corpus check, focused tests, payload golden eval and writes results/summary. | `.pytest_tmp/f025-demo-validation-quick/results.json`, `.pytest_tmp/f025-demo-validation-quick/summary.md`. | Passed |
| Full validation calls real live UI paths. | Full mode runs live health, live UI smoke, Case C, and F024 Case D through `research_ui_e2e.py`. | `.pytest_tmp/f025-demo-validation-full/results.json`. | Partial: Case C blocked, Case D passed |
| Case C is honest. | Optional Case C with `llm_failed` is `blocked`, not `pass`. | Full artifact session `Nrn7kidUrq8BboRExjKVNg`, `semantic_auditor_mode=llm_failed`, `PermissionDeniedError`. | Passed as honesty gate |
| Required live blockers are not downgraded. | `live-ui-health-check`, required `live-ui-smoke`, and required Case D blocked states produce `overall_status=blocked`; only optional Case C alone can produce `partial`. | `.pytest_tmp/f025-review-focused`: 49 passed. | Passed |
| Case D is accepted. | 7 papers, 4 themes, 28 linked cells, 53 citations, report/matrix paths present. | Full artifact session `V48aUaZPveXwNJN8MpvDqU`. | Passed |
| Golden corpus is more realistic. | Added method/limitation, multi-citation QA, refusal, and expected-failure matrix negative payload cases. | `.pytest_tmp/f025-golden/results.json`: 15/15. | Passed |

## State Timeline

| Date | State | Trigger | Evidence | Note |
| --- | --- | --- | --- | --- |
| 2026-07-07 | active | User requested F025 one-click validation chain | This Feature | Scope excludes new research capability and UI rewrite. |
| 2026-07-07 | verified | Quick/full validation, focused tests, golden eval, docs checks | EV-026 | Full overall partial due optional Case C LLM permission blocker; F024 Case D passed. |
| 2026-07-07 | completed | Evidence and Feature Index updated | EV-026 | Completion is conditional on understanding that F023 live LLM was not verified in this run. |

## Patch History

| Patch | Date | Commit | Symptom | Root Cause | Protection | Status |
| --- | --- | --- | --- | --- | --- | --- |
| F025.1 | 2026-07-07 | pending | Demo validation was scattered across separate commands and Evidence docs. | No orchestration runner existed for F019/F023/F024 validation chain. | Added `research_demo_validation.py`, runner tests, expanded golden corpus, quick/full artifacts, F025/EV-026 docs. | verified |
| F025.2 | 2026-07-07 | pending | Review found required live UI / required 7-paper review blockers were aggregated as `partial`. | `_overall_status()` treated all blocked steps like optional Case C unless Case C was explicitly required. | Added regression tests for blocked live health, required live smoke, and required Case D; `_overall_status()` now returns `partial` only when the only blocked step is optional Case C. | verified |

## Evidence

- [EV-026 Reproducible Demo Validation Chain Verification](../evidence/EV-026-reproducible-demo-validation-chain-verification.md)

## Recovery Snapshot

- Read first: this Feature, EV-026, F019, F023, F024.
- Current script: `ScienceClaw/backend/scripts/research_demo_validation.py`.
- Current tests: `ScienceClaw/backend/tests/test_research_demo_validation.py`, `ScienceClaw/backend/tests/test_research_golden_eval.py`.
- Current quick artifact: `.pytest_tmp/f025-demo-validation-quick/`.
- Current full artifact: `.pytest_tmp/f025-demo-validation-full/`.
- Current full status: `partial`; Case C optional blocked with `PermissionDeniedError`; Case D passed.
- Current full sessions: Case C `Nrn7kidUrq8BboRExjKVNg`; Case D `V48aUaZPveXwNJN8MpvDqU`.
- If Case C is required, rerun with valid LLM permission or use `--reuse-existing-llm-artifact` only for a recent accepted `llm_enhanced` artifact and record its path/time.
- If Case D fails, inspect `paper_data/f024_7paper_corpus/`, live upload/indexing, Chat send, and report sidecar paths before changing assertions.
- Do not submit `.pytest_tmp` artifacts to git.
- Next safe action: rerun quick, then rerun full with live services; only require Case C after fixing live model permission.

## Next Step

Keep F025 as the release/interview validation entrypoint. Before demo, run quick first, then full with live services running; explain `partial` honestly if optional Case C is blocked by model permission.
