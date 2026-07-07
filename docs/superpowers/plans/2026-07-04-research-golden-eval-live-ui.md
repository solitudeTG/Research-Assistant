# Research Golden Eval Live UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a compact real-paper golden evaluation loop with live UI E2E evidence for Research Assistant quality gates.

**Architecture:** Add a focused evaluation module that loads golden cases, maps case thresholds to existing F019 `ResearchQualityRequirement`, evaluates saved or live-produced answer payloads, and writes JSON plus Markdown summaries. Reuse the existing live UI browser workflow for the real product-path E2E instead of inventing another UI harness.

**Tech Stack:** Python dataclasses/JSON/argparse, existing FastAPI session APIs, existing Playwright UI helper, existing F019 evaluation module, pytest.

---

## File Structure

- Create `ScienceClaw/backend/research_assistant/golden_eval.py`: case schema, threshold mapping, per-case result model, batch aggregation, Markdown summary writer.
- Create `ScienceClaw/backend/scripts/research_golden_eval.py`: CLI entrypoint for payload mode and live UI mode.
- Modify `ScienceClaw/backend/scripts/research_ui_e2e.py`: return answer/report payloads and add assertion helpers needed by golden eval.
- Create `ScienceClaw/backend/tests/test_research_golden_eval.py`: focused tests for schema, evaluation, aggregation, summary, and live UI assertion behavior.
- Create `docs/evals/research_golden_cases.json`: first six golden cases using current real paper paths plus payload fixture paths.
- Update `docs/features/F019-research-quality-evaluation-harness.md`: add the live golden-eval slice and expected Evidence link.
- Create `docs/evidence/EV-018-f019-golden-eval-live-ui-e2e.md` after live UI verification.

## Task 1: Golden Eval Core

**Files:**
- Create: `ScienceClaw/backend/research_assistant/golden_eval.py`
- Test: `ScienceClaw/backend/tests/test_research_golden_eval.py`

- [ ] **Step 1: Write failing tests for case loading and threshold mapping**

Add tests:

```python
def test_load_golden_cases_maps_thresholds_to_quality_requirement(tmp_path):
    cases_path = tmp_path / "cases.json"
    cases_path.write_text(json.dumps({
        "cases": [{
            "case_id": "summary-1",
            "task_type": "whole_paper_summary",
            "mode": "payload",
            "paper_paths": ["paper_data/a.pdf"],
            "question": "Summarize the paper.",
            "answer_payload_path": "workspace/evals/summary-1.answer.json",
            "quality_thresholds": {
                "min_citation_count": 3,
                "max_unsupported_claim_ratio": 0.25,
                "max_invalid_claims": 0,
                "required_summary_mode": "llm_section_global"
            },
            "required_outputs": {"answer": True, "report": False, "markdown_summary": True}
        }]
    }), encoding="utf-8")

    cases = load_golden_cases(cases_path)
    requirement = cases[0].to_quality_requirement()

    assert cases[0].case_id == "summary-1"
    assert requirement.expected_route == "whole_paper_summary"
    assert requirement.min_citation_count == 3
    assert requirement.max_unsupported_claim_ratio == 0.25
    assert requirement.required_summary_mode == "llm_section_global"
```

- [ ] **Step 2: Verify RED**

Run:

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python -m pytest ScienceClaw\backend\tests\test_research_golden_eval.py -q --basetemp .pytest_tmp\golden-eval-red
```

Expected: fail because `backend.research_assistant.golden_eval` does not exist.

- [ ] **Step 3: Implement minimal schema and threshold mapping**

Add dataclasses `GoldenEvalCase`, `GoldenEvalThresholds`, `GoldenEvalRequiredOutputs`, `GoldenEvalSuite`, plus `load_golden_cases(path)`.

- [ ] **Step 4: Verify GREEN**

Run the same focused test command. Expected: pass.

## Task 2: Batch Evaluation and Markdown Summary

**Files:**
- Modify: `ScienceClaw/backend/research_assistant/golden_eval.py`
- Modify: `ScienceClaw/backend/tests/test_research_golden_eval.py`

- [ ] **Step 1: Write failing tests for failed-case isolation and Markdown diagnostics**

Add tests that build two payload cases: one passing, one failing with `citation_count_too_low`. Assert:

- `run_payload_golden_eval(...)` returns both cases.
- overall passed is false.
- `summary.md` includes `Passed: 1`, `Failed: 1`, `citation_count_too_low`, and `F005 retrieval`.

- [ ] **Step 2: Verify RED**

Run focused tests. Expected: fail because batch evaluation and summary rendering are missing.

- [ ] **Step 3: Implement batch evaluation**

Implement:

- `GoldenEvalCaseResult`
- `GoldenEvalRunResult`
- `evaluate_payload_cases(cases, root, output_dir)`
- `write_golden_eval_outputs(run_result, output_dir)`
- `render_markdown_summary(run_result)`

Use existing `evaluate_research_answer` and do not duplicate F019 quality logic.

- [ ] **Step 4: Verify GREEN**

Run focused tests. Expected: pass.

## Task 3: CLI Entrypoint

**Files:**
- Create: `ScienceClaw/backend/scripts/research_golden_eval.py`
- Modify: `ScienceClaw/backend/tests/test_research_golden_eval.py`

- [ ] **Step 1: Write failing CLI test**

Add a subprocess test that runs:

```powershell
python -m backend.scripts.research_golden_eval --cases <cases.json> --mode payload --output <tmp_output>
```

Assert return code is non-zero for a failing required case, and output files exist.

- [ ] **Step 2: Verify RED**

Expected: module not found.

- [ ] **Step 3: Implement CLI**

CLI args:

- `--cases`
- `--mode payload|live-ui`
- `--output`
- `--frontend-url`
- `--api-base-url`
- `--username`
- `--password`
- `--headed`
- `--timeout-ms`

For this task implement payload mode; live UI mode can raise a clear error until Task 4.

- [ ] **Step 4: Verify GREEN**

Run focused tests. Expected: pass.

## Task 4: Live UI Golden Eval Bridge

**Files:**
- Modify: `ScienceClaw/backend/scripts/research_ui_e2e.py`
- Modify: `ScienceClaw/backend/research_assistant/golden_eval.py`
- Modify: `ScienceClaw/backend/scripts/research_golden_eval.py`
- Modify: `ScienceClaw/backend/tests/test_research_golden_eval.py`

- [ ] **Step 1: Write failing tests for live UI result validation**

Add a unit test using a constructed live result that includes:

- `answer_payload`
- `report_payload`
- `activity_steps`
- `round_files`

Assert `assert_live_golden_eval_result(...)` passes only when answer payload has citations/audit/context boundaries and report sidecar exists.

- [ ] **Step 2: Verify RED**

Expected: fail because live result fields and assertion function are missing.

- [ ] **Step 3: Extend `ResearchUiE2EResult`**

Add optional fields:

- `answer_payload: dict | None`
- `report_payload: dict | None`

Collect the POST `/research/answer` and `/research/report` response data in `_run_browser_loop`.

- [ ] **Step 4: Implement live UI mode in golden eval CLI**

For `--mode live-ui`, require at least one case with `mode="live_ui"`. Run the existing browser loop using the case question and first paper path when provided. Feed `answer_payload` into the same quality evaluation and write outputs.

- [ ] **Step 5: Verify GREEN**

Run focused tests. Expected: pass.

## Task 5: Golden Case Fixture

**Files:**
- Create: `docs/evals/research_golden_cases.json`

- [ ] **Step 1: Add six first-version cases**

Include:

- two `whole_paper_summary`
- two `evidence_qa`
- one `no_evidence_or_insufficient_evidence`
- one `multi_paper_synthesis`

Reference the real PDFs under `paper_data/` where available. Use payload mode for breadth and one live UI case for product-path acceptance.

- [ ] **Step 2: Validate case schema**

Run:

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python -m backend.scripts.research_golden_eval --cases docs\evals\research_golden_cases.json --mode payload --output workspace\research_eval\schema-smoke
```

Expected: if payload fixtures are not yet present, the command records missing payload files as failed cases without crashing.

## Task 6: Focused Verification

**Files:**
- No new files unless failures require minimal fixes.

- [ ] **Step 1: Run focused backend tests**

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python -m pytest ScienceClaw\backend\tests\test_research_golden_eval.py ScienceClaw\backend\tests\test_research_evaluation.py ScienceClaw\backend\tests\test_research_ui_e2e_script.py -q --basetemp .pytest_tmp\golden-eval
```

- [ ] **Step 2: Run broader research tests if focused tests pass**

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python -m pytest ScienceClaw\backend\tests -k research -q --basetemp .pytest_tmp\golden-eval-research
```

## Task 7: Live UI E2E Evidence

**Files:**
- Create: `docs/evidence/EV-018-f019-golden-eval-live-ui-e2e.md`
- Modify: `docs/features/F019-research-quality-evaluation-harness.md`

- [ ] **Step 1: Run live UI E2E golden eval**

Requires running backend/frontend stack.

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; python -m backend.scripts.research_golden_eval --cases docs\evals\research_golden_cases.json --mode live-ui --output workspace\research_eval\live-ui --frontend-url http://127.0.0.1:5173 --api-base-url http://127.0.0.1:12001/api/v1
```

Expected: at least one live UI case completes; answer/report payloads are saved; `summary.md` exists.

- [ ] **Step 2: Record Evidence**

Create EV-018 with:

- supported claim
- commands
- session id(s)
- output artifact paths
- pass/fail counts
- known limitations

- [ ] **Step 3: Update F019**

Add State Timeline row, Evidence link, Acceptance Map row, and Patch History row for the golden eval slice.

## Task 8: AgentMentor Validation and Final Checks

**Files:**
- Modified AgentMentor docs.

- [ ] **Step 1: Validate AgentMentor docs**

```powershell
python C:\Users\HUAWEI\.codex\skills\using-agentmentor\scripts\knowledge_check.py --root E:\Self-Project\Research-Assistant --docs-path docs --strict
```

- [ ] **Step 2: Git diff check**

```powershell
git diff --check
```

- [ ] **Step 3: Commit coherent slices**

Commit after tests and docs are coherent. Verify git identity remains `solitudeTG` before each commit.
