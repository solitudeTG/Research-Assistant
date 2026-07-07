import json
import subprocess
import sys

import pytest

from backend.scripts.research_ui_e2e import ResearchUiE2EResult


def test_load_golden_cases_maps_thresholds_to_quality_requirement(tmp_path):
    from backend.research_assistant.golden_eval import load_golden_cases

    cases_path = tmp_path / "cases.json"
    cases_path.write_text(
        json.dumps(
            {
                "cases": [
                    {
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
                            "required_summary_mode": "llm_section_global",
                        },
                        "required_outputs": {
                            "answer": True,
                            "report": False,
                            "markdown_summary": True,
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    cases = load_golden_cases(cases_path)
    requirement = cases[0].to_quality_requirement()

    assert cases[0].case_id == "summary-1"
    assert cases[0].required_outputs.answer is True
    assert requirement.expected_route == "whole_paper_summary"
    assert requirement.min_citation_count == 3
    assert requirement.max_unsupported_claim_ratio == 0.25
    assert requirement.required_summary_mode == "llm_section_global"


def test_payload_golden_eval_continues_after_failed_case_and_writes_summary(tmp_path):
    from backend.research_assistant.golden_eval import evaluate_payload_cases, load_golden_cases, write_golden_eval_outputs

    _write_paper_fixtures(tmp_path, "a.pdf")
    passing_payload = _answer_payload(
        route="evidence_qa",
        admission="accepted",
        citation_count=2,
        summary_mode="",
        claim_count=2,
        approved=2,
        partial=0,
        unsupported=0,
    )
    failing_payload = _answer_payload(
        route="evidence_qa",
        admission="accepted",
        citation_count=0,
        summary_mode="",
        claim_count=2,
        approved=0,
        partial=0,
        unsupported=2,
    )
    (tmp_path / "passing.answer.json").write_text(json.dumps(passing_payload), encoding="utf-8")
    (tmp_path / "failing.answer.json").write_text(json.dumps(failing_payload), encoding="utf-8")
    cases_path = tmp_path / "cases.json"
    cases_path.write_text(
        json.dumps(
            {
                "cases": [
                    _case("passing", "passing.answer.json", min_citations=1),
                    _case("failing", "failing.answer.json", min_citations=1),
                ]
            }
        ),
        encoding="utf-8",
    )

    run_result = evaluate_payload_cases(load_golden_cases(cases_path), root=tmp_path)
    output_dir = tmp_path / "out"
    write_golden_eval_outputs(run_result, output_dir)

    assert run_result.case_count == 2
    assert run_result.passed_count == 1
    assert run_result.failed_count == 1
    assert not run_result.passed
    summary = (output_dir / "summary.md").read_text(encoding="utf-8")
    assert "Passed: 1" in summary
    assert "Failed: 1" in summary
    assert "citation_count_too_low" in summary
    assert "F005 retrieval" in summary
    assert (output_dir / "results.json").exists()
    results = json.loads((output_dir / "results.json").read_text(encoding="utf-8"))
    failing = next(case for case in results["cases"] if case["case_id"] == "failing")
    assert "F005 retrieval" in failing["owner_module_hints"]
    assert failing["failure_summary_path"].endswith("failing.failure.md")
    assert (output_dir / "cases" / "failing.failure.md").exists()
    assert failing["quality"]["findings"][0]["owner_module_hints"]


def test_research_golden_eval_cli_writes_outputs_and_returns_nonzero_for_failed_case(tmp_path):
    _write_paper_fixtures(tmp_path, "a.pdf")
    payload_dir = tmp_path / "payloads"
    payload_dir.mkdir()
    answer_path = payload_dir / "failing.answer.json"
    answer_path.write_text(
        json.dumps(
            _answer_payload(
                route="evidence_qa",
                admission="accepted",
                citation_count=0,
                summary_mode="",
                claim_count=1,
                approved=0,
                partial=0,
                unsupported=1,
            )
        ),
        encoding="utf-8",
    )
    cases_path = tmp_path / "cases.json"
    cases_path.write_text(json.dumps({"cases": [_case("failing", "payloads/failing.answer.json", min_citations=1)]}), encoding="utf-8")
    output_dir = tmp_path / "out"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "backend.scripts.research_golden_eval",
            "--cases",
            str(cases_path),
            "--mode",
            "payload",
            "--output",
            str(output_dir),
            "--payload-dir",
            str(payload_dir),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert (output_dir / "results.json").exists()
    assert (output_dir / "summary.md").exists()


def test_payload_golden_eval_checks_multi_paper_and_insufficient_evidence_contracts(tmp_path):
    from backend.research_assistant.golden_eval import evaluate_payload_cases, load_golden_cases

    _write_paper_fixtures(tmp_path, "a.pdf", "b.pdf")
    insufficient = _answer_payload(
        route="evidence_qa",
        admission="rejected",
        citation_count=0,
        summary_mode="",
        claim_count=1,
        approved=0,
        partial=0,
        unsupported=1,
    )
    multi_paper = _answer_payload(
        route="evidence_qa",
        admission="accepted",
        citation_count=2,
        summary_mode="",
        claim_count=2,
        approved=2,
        partial=0,
        unsupported=0,
    )
    multi_paper["citations"][0]["paper_id"] = "paper-a"
    multi_paper["citations"][0]["source_identity"] = {"paper_id": "paper-a"}
    multi_paper["citations"][1]["paper_id"] = "paper-b"
    multi_paper["citations"][1]["source_identity"] = {"paper_id": "paper-b"}
    (tmp_path / "insufficient.answer.json").write_text(json.dumps(insufficient), encoding="utf-8")
    (tmp_path / "multi.answer.json").write_text(json.dumps(multi_paper), encoding="utf-8")
    cases_path = tmp_path / "cases.json"
    cases_path.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        **_case("insufficient", "insufficient.answer.json", min_citations=0),
                        "task_type": "no_evidence_or_insufficient_evidence",
                        "quality_thresholds": {
                            "min_citation_count": 0,
                            "max_citation_count": 0,
                            "allowed_admission_decisions": ["rejected", "insufficient", "no_evidence"],
                            "max_unsupported_claim_ratio": 1.0,
                            "max_invalid_claims": 0,
                        },
                    },
                    {
                        **_case("multi", "multi.answer.json", min_citations=2),
                        "task_type": "multi_paper_synthesis",
                        "paper_paths": ["paper_data/a.pdf", "paper_data/b.pdf"],
                        "quality_thresholds": {
                            "min_citation_count": 2,
                            "min_distinct_cited_papers": 2,
                            "max_unsupported_claim_ratio": 0.5,
                            "max_invalid_claims": 0,
                        },
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    run_result = evaluate_payload_cases(load_golden_cases(cases_path), root=tmp_path)

    assert run_result.passed
    multi_result = next(case for case in run_result.cases if case.case_id == "multi")
    assert multi_result.quality["metrics"]["distinct_cited_paper_count"] == 2


def test_payload_golden_eval_checks_expected_semantic_statuses_and_finding_codes(tmp_path):
    from backend.research_assistant.golden_eval import evaluate_payload_cases, load_golden_cases

    _write_paper_fixtures(tmp_path, "a.pdf")
    payload = _answer_payload(
        route="evidence_qa",
        admission="accepted",
        citation_count=1,
        summary_mode="",
        claim_count=2,
        approved=1,
        partial=1,
        unsupported=0,
    )
    payload["audit"]["claims"][1]["finding_code"] = "semantic_support_partial"
    (tmp_path / "answer.json").write_text(json.dumps(payload), encoding="utf-8")
    case = _case("semantic-partial", "answer.json", min_citations=1)
    case["quality_thresholds"]["expected_support_statuses"] = ["supported", "partial"]
    case["quality_thresholds"]["expected_finding_codes"] = ["semantic_support_partial"]
    cases_path = tmp_path / "cases.json"
    cases_path.write_text(json.dumps({"cases": [case]}), encoding="utf-8")

    run_result = evaluate_payload_cases(load_golden_cases(cases_path), root=tmp_path)

    assert run_result.passed
    assert run_result.cases[0].quality["metrics"]["semantic_support_statuses"] == ["partial", "supported"]
    assert run_result.cases[0].quality["metrics"]["semantic_finding_codes"] == ["semantic_support_partial"]


def test_payload_golden_eval_requires_llm_semantic_audit_when_declared(tmp_path):
    from backend.research_assistant.golden_eval import evaluate_payload_cases, load_golden_cases

    _write_paper_fixtures(tmp_path, "a.pdf")
    payload = _answer_payload(
        route="evidence_qa",
        admission="accepted",
        citation_count=1,
        summary_mode="",
        claim_count=1,
        approved=1,
        partial=0,
        unsupported=0,
    )
    (tmp_path / "answer.json").write_text(json.dumps(payload), encoding="utf-8")
    case = _case("llm-required", "answer.json", min_citations=1)
    case["quality_thresholds"]["require_llm_semantic_audit"] = True
    cases_path = tmp_path / "cases.json"
    cases_path.write_text(json.dumps({"cases": [case]}), encoding="utf-8")

    run_result = evaluate_payload_cases(load_golden_cases(cases_path), root=tmp_path)

    assert not run_result.passed
    finding_codes = {finding["code"] for finding in run_result.cases[0].quality["findings"]}
    assert "llm_semantic_auditor_missing" in finding_codes
    assert "F023 LLM semantic auditor" in run_result.cases[0].owner_module_hints


def test_payload_golden_eval_checks_literature_review_matrix_contract(tmp_path):
    from backend.research_assistant.golden_eval import evaluate_payload_cases, load_golden_cases

    _write_paper_fixtures(tmp_path, *[f"p{index}.pdf" for index in range(1, 8)])
    payload = _literature_review_payload()
    (tmp_path / "literature.answer.json").write_text(json.dumps(payload), encoding="utf-8")
    (tmp_path / "literature.report.json").write_text(
        json.dumps({"report_id": "report-1", "evidence_matrix": payload["evidence_matrix"]}),
        encoding="utf-8",
    )
    case = _case("literature-review", "literature.answer.json", min_citations=7)
    case["task_type"] = "literature_review"
    case["paper_paths"] = [f"paper_data/p{index}.pdf" for index in range(1, 8)]
    case["report_payload_path"] = "literature.report.json"
    case["required_outputs"]["report"] = True
    case["quality_thresholds"].update(
        {
            "min_distinct_cited_papers": 7,
            "min_evidence_matrix_papers": 7,
            "min_evidence_matrix_themes": 4,
            "min_theme_paper_cells": 5,
            "min_evidence_linked_cells": 10,
            "required_report_sections": [
                "Evidence Matrix",
                "Cross-paper synthesis",
                "Agreements",
                "Disagreements / gaps",
                "Limitations",
            ],
        }
    )
    cases_path = tmp_path / "cases.json"
    cases_path.write_text(json.dumps({"cases": [case]}), encoding="utf-8")

    run_result = evaluate_payload_cases(load_golden_cases(cases_path), root=tmp_path)

    assert run_result.passed
    quality = run_result.cases[0].quality
    assert quality["metrics"]["distinct_cited_paper_count"] == 7
    assert quality["metrics"]["evidence_matrix_paper_count"] == 7
    assert quality["metrics"]["evidence_matrix_theme_count"] == 4
    assert quality["metrics"]["evidence_matrix_linked_cell_count"] >= 10


def test_payload_golden_eval_rejects_fabricated_citation_for_insufficient_evidence(tmp_path):
    from backend.research_assistant.golden_eval import evaluate_payload_cases, load_golden_cases

    _write_paper_fixtures(tmp_path, "a.pdf")
    payload = _answer_payload(
        route="evidence_qa",
        admission="accepted",
        citation_count=1,
        summary_mode="",
        claim_count=1,
        approved=1,
        partial=0,
        unsupported=0,
    )
    (tmp_path / "bad.answer.json").write_text(json.dumps(payload), encoding="utf-8")
    cases_path = tmp_path / "cases.json"
    bad_case = _case("bad-insufficient", "bad.answer.json", min_citations=0)
    bad_case["task_type"] = "no_evidence_or_insufficient_evidence"
    bad_case["quality_thresholds"] = {
        "min_citation_count": 0,
        "max_citation_count": 0,
        "allowed_admission_decisions": ["rejected", "insufficient", "no_evidence"],
        "max_unsupported_claim_ratio": 1.0,
        "max_invalid_claims": 0,
    }
    cases_path.write_text(json.dumps({"cases": [bad_case]}), encoding="utf-8")

    run_result = evaluate_payload_cases(load_golden_cases(cases_path), root=tmp_path)

    assert not run_result.passed
    findings = run_result.cases[0].quality["findings"]
    assert {finding["code"] for finding in findings} >= {"citation_count_too_high", "admission_not_insufficient"}
    assert "F011 admission" in run_result.cases[0].owner_module_hints


def test_payload_golden_eval_rejects_missing_real_paper_fixture(tmp_path):
    from backend.research_assistant.golden_eval import evaluate_payload_cases, load_golden_cases

    payload = _answer_payload(
        route="evidence_qa",
        admission="accepted",
        citation_count=1,
        summary_mode="",
        claim_count=1,
        approved=1,
        partial=0,
        unsupported=0,
    )
    (tmp_path / "answer.json").write_text(json.dumps(payload), encoding="utf-8")
    case = _case("missing-paper", "answer.json", min_citations=1)
    case["paper_paths"] = ["missing/nonexistent.pdf"]
    cases_path = tmp_path / "cases.json"
    cases_path.write_text(json.dumps({"cases": [case]}), encoding="utf-8")

    run_result = evaluate_payload_cases(load_golden_cases(cases_path), root=tmp_path)

    assert not run_result.passed
    assert run_result.cases[0].quality["findings"][0]["code"] == "paper_fixture_missing"
    assert "F019 golden eval" in run_result.cases[0].owner_module_hints


def test_payload_golden_eval_rejects_missing_required_report_payload(tmp_path):
    from backend.research_assistant.golden_eval import evaluate_payload_cases, load_golden_cases

    _write_paper_fixtures(tmp_path, "a.pdf")
    payload = _answer_payload(
        route="evidence_qa",
        admission="accepted",
        citation_count=1,
        summary_mode="",
        claim_count=1,
        approved=1,
        partial=0,
        unsupported=0,
    )
    (tmp_path / "answer.json").write_text(json.dumps(payload), encoding="utf-8")
    case = _case("missing-report", "answer.json", min_citations=1)
    case["required_outputs"]["report"] = True
    cases_path = tmp_path / "cases.json"
    cases_path.write_text(json.dumps({"cases": [case]}), encoding="utf-8")

    run_result = evaluate_payload_cases(load_golden_cases(cases_path), root=tmp_path)

    assert not run_result.passed
    assert run_result.cases[0].quality["findings"][0]["code"] == "required_report_missing"
    assert "F019 golden eval" in run_result.cases[0].owner_module_hints


def test_payload_golden_eval_accepts_required_report_payload(tmp_path):
    from backend.research_assistant.golden_eval import evaluate_payload_cases, load_golden_cases, write_golden_eval_outputs

    _write_paper_fixtures(tmp_path, "a.pdf")
    payload = _answer_payload(
        route="evidence_qa",
        admission="accepted",
        citation_count=1,
        summary_mode="",
        claim_count=1,
        approved=1,
        partial=0,
        unsupported=0,
    )
    (tmp_path / "answer.json").write_text(json.dumps(payload), encoding="utf-8")
    (tmp_path / "report.json").write_text(json.dumps({"report_id": "report-1"}), encoding="utf-8")
    case = _case("with-report", "answer.json", min_citations=1)
    case["required_outputs"]["report"] = True
    case["report_payload_path"] = "report.json"
    cases_path = tmp_path / "cases.json"
    cases_path.write_text(json.dumps({"cases": [case]}), encoding="utf-8")

    run_result = evaluate_payload_cases(load_golden_cases(cases_path), root=tmp_path)
    output_dir = tmp_path / "out"
    write_golden_eval_outputs(run_result, output_dir)

    assert run_result.passed
    results = json.loads((output_dir / "results.json").read_text(encoding="utf-8"))
    assert results["cases"][0]["report_payload_path"].endswith("with-report.report.json")
    assert (output_dir / "cases" / "with-report.report.json").exists()


def test_assert_live_golden_eval_result_rejects_missing_answer_payload():
    from backend.research_assistant.golden_eval import assert_live_golden_eval_result

    result = ResearchUiE2EResult(
        session_id="session-1",
        session_status="completed",
        citation_count=1,
        activity_steps=[
            "Research document uploaded",
            "Parsing research document",
            "Indexing paper evidence",
            "Retrieving citation evidence",
            "Markdown research artifact generated",
        ],
        round_files=["research-report-abc.md", "research-report-abc.evidence.json"],
        error_events=[],
    )

    with pytest.raises(AssertionError, match="answer payload"):
        assert_live_golden_eval_result(result, require_report=True)


def test_assert_live_golden_eval_result_accepts_answer_report_and_trace_payloads():
    from backend.research_assistant.golden_eval import assert_live_golden_eval_result

    result = ResearchUiE2EResult(
        session_id="session-1",
        session_status="completed",
        citation_count=1,
        activity_steps=[
            "Research document uploaded",
            "Parsing research document",
            "Indexing paper evidence",
            "Retrieving citation evidence",
            "Markdown research artifact generated",
        ],
        round_files=["research-report-abc.md", "research-report-abc.evidence.json"],
        error_events=[],
        answer_payload=_answer_payload(
            route="evidence_qa",
            admission="accepted",
            citation_count=1,
            summary_mode="",
            claim_count=1,
            approved=1,
            partial=0,
            unsupported=0,
        ),
        report_payload={"report_id": "report-1", "markdown_path": "research-report-abc.md", "evidence_map_path": "research-report-abc.evidence.json"},
    )

    assert_live_golden_eval_result(result, require_report=True)


def test_live_golden_eval_outputs_write_payload_artifacts_without_inlining(tmp_path):
    from backend.research_assistant.golden_eval import (
        GoldenEvalCaseResult,
        GoldenEvalRunResult,
        write_golden_eval_outputs,
    )

    answer_payload = _answer_payload(
        route="whole_paper_summary",
        admission="accepted",
        citation_count=2,
        summary_mode="llm_section_global",
        claim_count=1,
        approved=1,
        partial=0,
        unsupported=0,
    )
    report_payload = {"report_id": "report-1", "markdown_path": "research-report.md"}
    run_result = GoldenEvalRunResult(
        run_id="live-ui-test",
        mode="live-ui",
        cases=[
            GoldenEvalCaseResult(
                case_id="live-summary",
                task_type="whole_paper_summary",
                mode="live_ui",
                passed=True,
                quality={"case_id": "live-summary", "passed": True, "metrics": {}, "findings": []},
                answer_payload=answer_payload,
                report_payload=report_payload,
            )
        ],
    )

    output_dir = tmp_path / "out"
    write_golden_eval_outputs(run_result, output_dir)

    results = json.loads((output_dir / "results.json").read_text(encoding="utf-8"))
    case_result = results["cases"][0]
    assert (output_dir / "cases" / "live-summary.answer.json").exists()
    assert (output_dir / "cases" / "live-summary.report.json").exists()
    assert case_result["answer_payload_path"].endswith("live-summary.answer.json")
    assert case_result["report_payload_path"].endswith("live-summary.report.json")
    assert case_result["answer_payload"] is None
    assert case_result["report_payload"] is None


def _case(case_id: str, payload_path: str, *, min_citations: int):
    return {
        "case_id": case_id,
        "task_type": "evidence_qa",
        "mode": "payload",
        "paper_paths": ["paper_data/a.pdf"],
        "question": "What evidence is available?",
        "answer_payload_path": payload_path,
        "quality_thresholds": {
            "min_citation_count": min_citations,
            "max_unsupported_claim_ratio": 0.5,
            "max_invalid_claims": 0,
        },
        "required_outputs": {"answer": True, "report": False, "markdown_summary": True},
    }


def _write_paper_fixtures(root, *names: str) -> None:
    paper_dir = root / "paper_data"
    paper_dir.mkdir()
    for name in names:
        (paper_dir / name).write_bytes(b"%PDF-1.4\n% golden eval fixture\n")


def _answer_payload(
    *,
    route: str,
    admission: str,
    citation_count: int,
    summary_mode: str,
    claim_count: int,
    approved: int,
    partial: int,
    unsupported: int,
):
    citations = [
        {
            "evidence_id": index,
            "chunk_id": f"chunk-{index}",
            "paper_id": "paper-1",
            "title": "Paper",
            "section": "Results",
            "page_start": index,
            "page_end": index,
            "quote": "The paper reports a grounded finding.",
            "citation_label": f"paper-1:Results:{index}",
            "source_type": "paper",
            "source_identity": {"paper_id": "paper-1"},
            "evidence_scope": "project",
        }
        for index in range(1, citation_count + 1)
    ]
    return {
        "content": "Grounded answer.",
        "citations": citations,
        "citation_count": citation_count,
        "context_boundaries": {
            "citation_evidence": ["paper", "web", "database"],
            "context_only_memory": ["memory"],
            "process_trace": ["tool_logs", "runtime_results", "agent_lifecycle"],
            "model_reasoning": ["model_reasoning"],
        },
        "summary_synthesis": {"mode": summary_mode} if summary_mode else {},
        "evidence_admission": {"decision": admission},
        "task_route": {"route": route},
        "audit": {
            "status": "partial" if unsupported or partial else "approved",
            "claim_count": claim_count,
            "approved_claim_count": approved,
            "partial_claim_count": partial,
            "unsupported_claim_count": unsupported,
            "invalid_source_count": 0,
            "claims": [
                {
                    "claim_id": f"claim-{index}",
                    "claim_text": "The paper reports a grounded finding.",
                    "support_status": (
                        "supported"
                        if index <= approved
                        else "partial"
                        if index <= approved + partial
                        else "unsupported"
                    ),
                    "semantic_relevance_score": 1.0 if index <= approved else 0.5 if index <= approved + partial else 0.2,
                    "source_quality_score": 1.0,
                    "cited_evidence": [
                        {
                            "source_type": "paper",
                            "paper_id": "paper-1",
                            "title": "Paper",
                            "section": "Results",
                            "page_start": 1,
                            "page_end": 1,
                            "chunk_id": "chunk-1",
                            "quote": "The paper reports a grounded finding.",
                        }
                    ],
                    "rationale": "Fixture semantic audit claim.",
                    "finding_code": None if index <= approved else "semantic_support_partial" if index <= approved + partial else "semantic_support_missing",
                }
                for index in range(1, claim_count + 1)
            ],
        },
    }


def _literature_review_payload():
    payload = _answer_payload(
        route="evidence_qa",
        admission="accepted",
        citation_count=14,
        summary_mode="evidence_matrix_literature_review",
        claim_count=4,
        approved=3,
        partial=1,
        unsupported=0,
    )
    paper_ids = [f"paper-{index}" for index in range(1, 8)]
    for index, citation in enumerate(payload["citations"]):
        paper_id = paper_ids[index % len(paper_ids)]
        citation["paper_id"] = paper_id
        citation["source_identity"] = {"paper_id": paper_id}
        citation["citation_label"] = f"[{paper_id}:Method:{index + 1}]"
    payload["evidence_matrix"] = {
        "paper_count": 7,
        "papers": [
            {
                "paper_id": paper_id,
                "title": f"LEO Beamforming Study {index}",
                "year": str(2020 + index),
                "source_type": "paper",
                "citation_label": f"[{paper_id}:Method:{index}]",
            }
            for index, paper_id in enumerate(paper_ids, start=1)
        ],
        "themes": [
            {
                "theme_id": f"theme-{theme_index}",
                "label": label,
                "synthesis_claim": f"The corpus supports a cross-paper claim about {label}.",
                "evidence_strength": "strong",
                "paper_cells": [
                    {
                        "paper_id": paper_id,
                        "stance": "supports",
                        "contribution": f"{paper_id} contributes evidence for {label}.",
                        "method": "Simulation and analytical comparison.",
                        "limitation": "Deployment assumptions remain bounded.",
                        "evidence_ids": [paper_index],
                        "citation_labels": [f"[{paper_id}:Method:{paper_index}]"],
                        "quote_snippets": [f"{paper_id} reports method evidence."],
                        "support_status": "supported",
                    }
                    for paper_index, paper_id in enumerate(paper_ids, start=1)
                ],
            }
            for theme_index, label in enumerate(["Methods", "Evidence strength", "Agreements", "Limitations"], start=1)
        ],
        "agreements": ["The papers agree on deployment trade-offs."],
        "disagreements": ["The papers differ in method emphasis."],
        "gaps": ["Real-world validation remains open."],
        "limitations": ["Evidence comes from admitted snippets only."],
    }
    payload["report"] = {
        "artifact": True,
        "sections": [
            "Evidence Matrix",
            "Cross-paper synthesis",
            "Agreements",
            "Disagreements / gaps",
            "Limitations",
        ],
    }
    return payload
