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
- Desired outcome: 一个 repo 内脚本输出 `results.json`、`summary.md`、`commands.json`、`environment.json` 和分步骤 artifact，覆盖 quick/live/full 模式，并诚实区分 pass / fail / skipped / blocked / partial。
- Non-goals: 不实现新的研究能力；不做三层记忆产品化；不重写 F024 literature review；不引入新 UI shell；不把 `llm_failed` 写成 passed；不放松 demo 断言；不提交 `.pytest_tmp`。
- Exit Gate source: 本 Feature、EV-026、focused pytest、payload golden eval、quick/full validation artifacts、AgentMentor strict 与 F025 feature-index 检查。

## Feature Intake

- Original problem: F019/F022/F023/F024 已分别完成，但验收链条仍散落，无法用一条命令复现环境预检、fixture 检查、测试、payload eval、live UI smoke、Case C、Case D 和最终报告。
- User pain point: 面试展示需要可运行、可断言、可追溯的能力增量，而不是口头说“这些能力都做过”。
- Capability promise: `research_demo_validation.py` 提供 quick/live/full 模式，调用现有脚本和真实 UI E2E，聚合状态和关键指标，并允许复用已经验收的 `llm_enhanced` Case C artifact 来形成展示级 full pass。
- Non-goals: 不改 ScienceClaw app shell；不发明 ActivityPanel / Agent / tool 事件；不把 memory、tool logs、model reasoning 当 citation；不把 live UI 失败改成 direct API 成功。
- Acceptance source: 用户 2026-07-07 F025 任务说明中的命令接口、输出 shape、golden corpus 扩展、live UI 验收和质量门要求。
- Open questions: 新跑 F023 live Case C 依赖当前模型额度/权限；当模型不可用时，runner 必须记录 blocked/partial，而不是伪造 pass。

## Capability Contract

- `ScienceClaw/backend/scripts/research_demo_validation.py` 支持 `--mode quick|live|full`。
- quick 模式执行环境预检、F024 corpus/fixture 检查、focused tests、payload golden eval，不跑 live UI。
- live 模式执行环境预检、F024 corpus/fixture 检查、live health、live UI smoke、F024 Case D，并按 `--llm-case-c` 处理 F023 Case C。
- full 模式执行 quick + live。
- `--llm-case-c required` 要求 Case C 产出 `semantic_auditor.mode=llm_enhanced`，否则 overall 为 blocked/fail。
- `--llm-case-c optional` 允许模型权限/额度失败记录为 blocked，并使 overall 为 partial；不能把 F023 live LLM 写成 passed。
- `--reuse-existing-llm-artifact <dir>` 只能复用最近已验收的 `llm_enhanced` Case C artifact；如果 artifact 不是 `llm_enhanced`，必须 blocked。
- `--llm-case-c skip` 记录 skipped，并在 summary 中说明未验证 live LLM auditor。
- 输出目录固定包含 `results.json`、`summary.md`、`commands.json`、`environment.json`、`golden-eval/`、`focused-tests/`、`live-ui-smoke/`、`case-d-literature-review-7paper/`、`artifacts/`，required/optional Case C 时包含 `case-c-semantic-auditor/`。
- Golden corpus 新增 F025 payload cases，覆盖 method/limitation summary、multi-citation QA、insufficient-evidence refusal、literature-review negative gate。
- Literature-review negative case 使用 `expected_result=fail`，要求底层 quality gate 实际失败；主 golden eval 只有在该失败被观察到时才通过。

## Decision Context

### Why

F025 的价值不在新增回答能力，而在把能力变成可复现验收链。Agent 时代的风险不是代码写不出来，而是状态不可验收、失败不可定位、demo 与真实产品路径脱节。

### Why Not

没有另起 UI/Workbench，因为 ScienceClaw 已经提供 Chat、ActivityPanel、file/artifact panel、SSE trace 和 report path。没有用 direct API 替代 live UI，因为 F024/F023 的验收要求是真实浏览器、Chat textarea 和真实 artifact。没有把 Case C optional blocked 算作 pass，因为 LLM auditor 是 F023 的独立验收面；展示级 full pass 只能复用或重新生成真实 `llm_enhanced` artifact。

### If Modifying This Area, Check

- F004 Citation Evidence Boundary。
- F019 Research Quality Evaluation Harness。
- F022 Semantic Evidence Audit and Multi-paper Synthesis。
- F023 LLM Semantic Auditor。
- F024 Evidence Matrix Literature Review。
- EV-026 verification artifacts。

## Current Status

Completed. Quick validation passes. Full validation can be run in two honest modes:

- Fresh live Case C mode: if the current model returns `PermissionDeniedError` or quota errors, Case C is recorded as blocked and full overall becomes `partial`.
- Interview/release evidence mode: pass `--reuse-existing-llm-artifact .pytest_tmp\f023-live-case-c-qwen37` to reuse the accepted real browser `llm_enhanced` Case C artifact, while live health, smoke, and F024 Case D still run fresh. This produces full `overall_status=pass` only because Case C evidence is real and already accepted.

Review hardening guarantees non-Case-C blockers such as live health, required live UI smoke, or required Case D produce `overall_status=blocked` instead of `partial`.

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
- Accepted reusable Case C artifact: `.pytest_tmp/f023-live-case-c-qwen37`.

### Related Features

- [F019 Research Quality Evaluation Harness](F019-research-quality-evaluation-harness.md)
- [F022 Semantic Evidence Audit and Multi-paper Synthesis](F022-semantic-evidence-audit-and-multi-paper-synthesis.md)
- [F023 LLM Semantic Auditor](F023-llm-semantic-auditor.md)
- [F024 Evidence Matrix Literature Review](F024-evidence-matrix-literature-review.md)

## Acceptance Criteria

- [x] `research_demo_validation.py --mode quick` 生成完整 summary/results 并 overall pass。
- [x] full 模式生成完整 summary/results，live UI smoke pass，F024 Case D pass。
- [x] F023 Case C optional 策略诚实记录 blocked；未把 `llm_failed` 写成 passed。
- [x] F023 Case C 可通过 `--reuse-existing-llm-artifact` 复用已验收 `llm_enhanced` artifact，并使 full overall pass。
- [x] Focused pytest 通过。
- [x] Payload golden eval 通过，新增 F025 cases 生效。
- [x] Literature-review negative case 的底层 quality gate 实际失败，并由 `expected_result=fail` 保护为 benchmark。
- [x] F024 live UI Case D 真实上传/选择 7 篇 PDF，经 Chat textarea 发送并生成 matrix/report artifact。
- [x] `results.json` / `summary.md` 区分 pass / fail / skipped / blocked / partial。
- [x] AgentMentor strict 与 F025 feature-index 检查通过。

## Acceptance Map

| Claim | Acceptance | Evidence | Status |
| --- | --- | --- | --- |
| One-command quick validation works. | Quick mode runs precheck, corpus check, focused tests, payload golden eval and writes results/summary. | `.pytest_tmp/f025-demo-validation-quick/results.json`, `.pytest_tmp/completion-assessment-quick/results.json`. | Passed |
| Fresh full validation calls real live UI paths. | Full mode runs live health, live UI smoke, Case C, and F024 Case D through `research_ui_e2e.py`. | `.pytest_tmp/f025-demo-validation-full/results.json`. | Partial when live model permission blocks Case C |
| Interview full validation can pass honestly. | Full mode reuses accepted `llm_enhanced` Case C artifact and still runs live UI smoke plus F024 Case D. | `.pytest_tmp/f025-full-reuse-accepted-case-c/results.json`. | Passed |
| Case C is honest. | Optional Case C with `llm_failed` is `blocked`, not `pass`; reused artifacts must be `llm_enhanced`. | Runner tests and accepted Case C artifact. | Passed |
| Required live blockers are not downgraded. | `live-ui-health-check`, required `live-ui-smoke`, and required Case D blocked states produce `overall_status=blocked`; only optional Case C alone can produce `partial`. | Focused demo validation tests. | Passed |
| Case D is accepted. | 7 papers, 4 themes, 28 linked cells, citation-grounded report/matrix paths present. | F024/F025 full artifacts. | Passed |
| Golden corpus is more realistic. | Added method/limitation, multi-citation QA, refusal, and expected-failure matrix negative payload cases. | Golden eval results: 15/15. | Passed |

## State Timeline

| Date | State | Trigger | Evidence | Note |
| --- | --- | --- | --- | --- |
| 2026-07-07 | active | User requested F025 one-click validation chain | This Feature | Scope excludes new research capability and UI rewrite. |
| 2026-07-07 | verified | Quick/full validation, focused tests, golden eval, docs checks | EV-026 | Fresh full was partial due optional Case C LLM permission blocker; F024 Case D passed. |
| 2026-07-07 | completed | Evidence and Feature Index updated | EV-026 | Completion is conditional on understanding that fresh live Case C depends on model permission. |
| 2026-07-07 | completed | User requested fixing full partial for interview readiness | EV-026 | Full pass path now uses the accepted `.pytest_tmp/f023-live-case-c-qwen37` `llm_enhanced` artifact instead of rerunning a quota-sensitive Case C. |

## Patch History

| Patch | Date | Commit | Symptom | Root Cause | Protection | Status |
| --- | --- | --- | --- | --- | --- | --- |
| F025.1 | 2026-07-07 | `be56d60` | Demo validation was scattered across separate commands and Evidence docs. | No orchestration runner existed for F019/F023/F024 validation chain. | Added `research_demo_validation.py`, runner tests, expanded golden corpus, quick/full artifacts, F025/EV-026 docs. | verified |
| F025.2 | 2026-07-07 | `be56d60` | Review found required live UI / required 7-paper review blockers were aggregated as `partial`. | `_overall_status()` treated all blocked steps like optional Case C unless Case C was explicitly required. | Added regression tests for blocked live health, required live smoke, and required Case D; `_overall_status()` now returns `partial` only when the only blocked step is optional Case C. | verified |
| F025.3 | 2026-07-07 | pending | Interview full validation remained `partial` when Case C reran against a quota/permission-blocked model. | The full command reran a volatile LLM Case C even though a real accepted `llm_enhanced` Case C artifact already existed. | Added regression coverage for reused `llm_enhanced` Case C making full overall pass; documented the honest reuse command and artifact. | verified |

## Patch Churn Review

F025 now has three patch rows, but the churn is still within one stable invariant: the demo chain must be reproducible and honest. F025.1 created the runner, F025.2 fixed blocker aggregation, and F025.3 separates volatile fresh LLM execution from accepted reusable LLM evidence. No new Feature or ADR is needed yet because the changes do not expand the product surface; they harden release/interview validation semantics around already accepted F023/F024 evidence.

## Evidence

- [EV-026 Reproducible Demo Validation Chain Verification](../evidence/EV-026-reproducible-demo-validation-chain-verification.md)

## Recovery Snapshot

- Read first: this Feature, EV-026, F019, F023, F024.
- Current script: `ScienceClaw/backend/scripts/research_demo_validation.py`.
- Current tests: `ScienceClaw/backend/tests/test_research_demo_validation.py`, `ScienceClaw/backend/tests/test_research_golden_eval.py`.
- Quick artifact: `.pytest_tmp/completion-assessment-quick/`.
- Historical fresh full artifact: `.pytest_tmp/f025-demo-validation-full/`; status `partial` only because optional Case C was blocked with `PermissionDeniedError`; Case D passed.
- Accepted reusable Case C artifact: `.pytest_tmp/f023-live-case-c-qwen37/`; session `FjQPSdT36Q4CE5AauEQmEd`; `semantic_auditor.mode=llm_enhanced`; model `qwen3.7-plus`; finding `llm_insufficient_evidence`.
- Interview full artifact: `.pytest_tmp/f025-full-reuse-accepted-case-c/`; status `pass`.
- If Case C must be freshly rerun, use valid model permission and `--llm-case-c required`; do not reuse blocked `llm_failed` artifacts.
- If Case D fails, inspect `paper_data/f024_7paper_corpus/`, live upload/indexing, Chat send, and report sidecar paths before changing assertions.
- Do not submit `.pytest_tmp` artifacts to git.
- Next safe action: run quick validation, then run full validation with `--reuse-existing-llm-artifact .pytest_tmp\f023-live-case-c-qwen37` for interview evidence; only rerun fresh required Case C when model permission is known-good.

## Next Step

Keep F025 as the release/interview validation entrypoint. For a stable interview demo, run quick first, then full with `--reuse-existing-llm-artifact .pytest_tmp\f023-live-case-c-qwen37` so the LLM auditor evidence remains real without depending on current model quota.
