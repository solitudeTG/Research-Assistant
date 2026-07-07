import json
import sys

from backend.scripts import research_demo_validation as demo


def test_step_runner_failure_makes_overall_fail(tmp_path):
    runner = demo.DemoValidationRunner(
        repo_root=tmp_path,
        output_dir=tmp_path / "out",
        command_runner=_fake_runner({"failing": demo.CommandResult(1, "bad", "boom")}),
    )

    step = runner.run_command_step("failing-step", ["failing"], tmp_path / "failing")
    results = demo.build_results(
        run_id="run-1",
        mode="quick",
        started_at="2026-07-07T00:00:00Z",
        completed_at="2026-07-07T00:00:01Z",
        steps=[step],
    )

    assert step.status == "fail"
    assert results["overall_status"] == "fail"


def test_optional_llm_blocked_is_partial_but_not_passed(tmp_path):
    blocked = demo.StepResult(
        name="case-c-semantic-auditor",
        status="blocked",
        command=["case-c"],
        duration_ms=10,
        output_path=str(tmp_path / "case-c"),
        failure_reason="PermissionDeniedError: quota unavailable",
        key_metrics={"semantic_auditor_mode": "llm_failed"},
    )

    results = demo.build_results(
        run_id="run-1",
        mode="full",
        started_at="2026-07-07T00:00:00Z",
        completed_at="2026-07-07T00:00:01Z",
        steps=[blocked],
        llm_case_c_policy="optional",
    )

    assert results["overall_status"] == "partial"
    assert results["case_c"]["status"] == "blocked"
    assert results["case_c"]["semantic_auditor_mode"] == "llm_failed"


def test_required_llm_blocked_makes_overall_blocked(tmp_path):
    blocked = demo.StepResult(
        name="case-c-semantic-auditor",
        status="blocked",
        command=["case-c"],
        duration_ms=10,
        output_path=str(tmp_path / "case-c"),
        failure_reason="PermissionDeniedError: quota unavailable",
    )

    results = demo.build_results(
        run_id="run-1",
        mode="live",
        started_at="2026-07-07T00:00:00Z",
        completed_at="2026-07-07T00:00:01Z",
        steps=[blocked],
        llm_case_c_policy="required",
    )

    assert results["overall_status"] == "blocked"


def test_required_live_ui_blocked_makes_overall_blocked(tmp_path):
    blocked = demo.StepResult(
        name="live-ui-smoke",
        status="blocked",
        command=["live-ui"],
        duration_ms=10,
        output_path=str(tmp_path / "live-ui-smoke"),
        failure_reason="frontend unavailable",
    )

    results = demo.build_results(
        run_id="run-1",
        mode="full",
        started_at="2026-07-07T00:00:00Z",
        completed_at="2026-07-07T00:00:01Z",
        steps=[blocked],
        llm_case_c_policy="optional",
    )

    assert results["overall_status"] == "blocked"


def test_live_health_blocked_makes_overall_blocked(tmp_path):
    blocked = demo.StepResult(
        name="live-ui-health-check",
        status="blocked",
        command=["GET", "/auth/status"],
        duration_ms=10,
        output_path=str(tmp_path / "live-ui-smoke"),
        failure_reason="connection refused",
    )

    results = demo.build_results(
        run_id="run-1",
        mode="live",
        started_at="2026-07-07T00:00:00Z",
        completed_at="2026-07-07T00:00:01Z",
        steps=[blocked],
        llm_case_c_policy="optional",
    )

    assert results["overall_status"] == "blocked"


def test_required_case_d_blocked_makes_overall_blocked_even_with_optional_case_c(tmp_path):
    optional_case_c = demo.StepResult(
        name="case-c-semantic-auditor",
        status="blocked",
        command=["case-c"],
        duration_ms=10,
        output_path=str(tmp_path / "case-c"),
        failure_reason="PermissionDeniedError",
    )
    blocked_case_d = demo.StepResult(
        name="case-d-literature-review-7paper",
        status="blocked",
        command=["case-d"],
        duration_ms=10,
        output_path=str(tmp_path / "case-d"),
        failure_reason="7-paper review failed",
    )

    results = demo.build_results(
        run_id="run-1",
        mode="full",
        started_at="2026-07-07T00:00:00Z",
        completed_at="2026-07-07T00:00:01Z",
        steps=[optional_case_c, blocked_case_d],
        llm_case_c_policy="optional",
    )

    assert results["overall_status"] == "blocked"


def test_missing_f024_corpus_or_less_than_7_pdfs_fails(tmp_path):
    corpus_dir = tmp_path / "paper_data" / "f024_7paper_corpus"
    corpus_dir.mkdir(parents=True)
    (corpus_dir / "manifest.json").write_text(json.dumps({"papers": []}), encoding="utf-8")
    for index in range(6):
        (corpus_dir / f"{index}.pdf").write_bytes(b"%PDF-1.4\n")

    step, corpus = demo.check_f024_corpus(tmp_path, corpus_dir)

    assert step.status == "fail"
    assert corpus["paper_count"] == 6
    assert "at least 7" in (step.failure_reason or "")


def test_results_json_and_summary_shape(tmp_path):
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    step = demo.StepResult(
        name="golden-eval",
        status="pass",
        command=[sys.executable, "golden"],
        duration_ms=1,
        output_path=str(output_dir / "golden-eval"),
        key_metrics={"case_count": 16, "passed": 16, "failed": 0},
    )
    results = demo.build_results(
        run_id="run-1",
        mode="quick",
        started_at="2026-07-07T00:00:00Z",
        completed_at="2026-07-07T00:00:01Z",
        steps=[step],
        golden_eval={"case_count": 16, "passed": 16, "failed": 0},
    )
    demo.write_outputs(output_dir, results, commands=[{"name": "golden-eval", "command": step.command}], environment={})

    saved = json.loads((output_dir / "results.json").read_text(encoding="utf-8"))
    summary = (output_dir / "summary.md").read_text(encoding="utf-8")
    assert saved["run_id"] == "run-1"
    assert saved["overall_status"] == "pass"
    assert "citation-grounded QA" in summary
    assert "golden-eval" in summary


def test_reused_llm_artifact_records_path_and_metrics(tmp_path):
    artifact_dir = tmp_path / "case-c-old"
    artifact_dir.mkdir()
    (artifact_dir / "results.json").write_text(
        json.dumps(
            {
                "session_id": "session-c",
                "quality_reports": {"case_c": {"passed": True}},
                "artifact_paths": {"answer_payload_path": str(artifact_dir / "case-c-answer.json")},
            }
        ),
        encoding="utf-8",
    )
    (artifact_dir / "case-c-answer.json").write_text(
        json.dumps(
            {
                "audit": {
                    "semantic_auditor": {"mode": "llm_enhanced", "model": "model-x"},
                    "claims": [{"finding_code": "llm_overreach"}],
                }
            }
        ),
        encoding="utf-8",
    )

    step, case_c = demo.reuse_llm_artifact_step(artifact_dir)

    assert step.status == "pass"
    assert case_c["session_id"] == "session-c"
    assert case_c["semantic_auditor_mode"] == "llm_enhanced"
    assert case_c["artifact_paths"]["reused_results_path"].endswith("results.json")


def _fake_runner(results):
    def run(command, cwd, timeout_ms, output_dir):
        return results[command[0]]

    return run
