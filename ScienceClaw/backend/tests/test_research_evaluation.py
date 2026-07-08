import json
import subprocess
import sys

import pytest

from backend.research_assistant.evaluation import (
    evaluate_research_answer,
    evidence_qa_quality_gate,
    literature_review_quality_gate,
    non_evidence_turn_quality_gate,
    whole_paper_summary_quality_gate,
)


def test_whole_paper_summary_quality_gate_accepts_grounded_llm_synthesis():
    report = evaluate_research_answer(
        _answer_payload(
            route="whole_paper_summary",
            admission="accepted",
            citation_count=2,
            summary_mode="llm_section_global",
            claim_count=10,
            approved=6,
            partial=2,
            unsupported=2,
        ),
        whole_paper_summary_quality_gate(max_unsupported_claim_ratio=0.3),
    )

    assert report.passed
    assert report.metrics["unsupported_claim_ratio"] == 0.2
    report.assert_passed()


def test_whole_paper_summary_quality_gate_rejects_wrong_route_and_noisy_audit():
    report = evaluate_research_answer(
        _answer_payload(
            route="evidence_qa",
            admission="accepted",
            citation_count=2,
            summary_mode="deterministic_extractive",
            claim_count=10,
            approved=2,
            partial=1,
            unsupported=7,
        ),
        whole_paper_summary_quality_gate(max_unsupported_claim_ratio=0.5),
    )

    assert not report.passed
    assert {finding.code for finding in report.findings} == {
        "route_mismatch",
        "summary_mode_mismatch",
        "unsupported_claim_ratio_exceeded",
    }
    with pytest.raises(AssertionError, match="Research quality gate failed"):
        report.assert_passed()


def test_evidence_qa_quality_gate_rejects_context_only_citation_source():
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
    payload["citations"][0]["source_type"] = "memory"

    report = evaluate_research_answer(payload, evidence_qa_quality_gate())

    assert not report.passed
    assert report.findings[0].code == "citation_source_type_invalid"


def test_evidence_qa_quality_gate_requires_semantic_audit_fields_and_traceable_citations():
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
    payload["citations"][0]["quote"] = ""
    payload["audit"]["claims"] = [
        {
            "claim_id": "claim-1",
            "claim_text": "The paper reports a grounded finding.",
            "support_status": "approved",
            "semantic_relevance_score": None,
            "source_quality_score": None,
            "cited_evidence": [],
        }
    ]

    report = evaluate_research_answer(payload, evidence_qa_quality_gate())

    assert not report.passed
    assert {finding.code for finding in report.findings} >= {
        "citation_quote_missing",
        "semantic_audit_support_status_invalid",
        "semantic_audit_score_missing",
        "semantic_audit_cited_evidence_missing",
    }


def test_quality_gate_requires_llm_semantic_auditor_when_configured():
    payload = _answer_payload(
        route="evidence_qa",
        admission="accepted",
        citation_count=1,
        summary_mode="",
        claim_count=1,
        approved=0,
        partial=0,
        unsupported=1,
    )
    payload["audit"]["semantic_auditor"] = {
        "mode": "llm_enhanced",
        "model": "fake-auditor",
        "claim_count": 1,
        "overreach_count": 1,
        "unsupported_count": 0,
        "llm_auditor_status": "completed",
    }
    payload["audit"]["claims"][0].update(
        {
            "support_status": "overreach",
            "finding_code": "llm_overreach",
            "deterministic_support_status": "supported",
            "llm_support_status": "overreach",
            "llm_rationale": "The quote is related but does not entail the outcome claim.",
        }
    )

    report = evaluate_research_answer(
        payload,
        evidence_qa_quality_gate().__class__(
            case_id="llm-required",
            expected_route="evidence_qa",
            expected_admission="accepted",
            min_citation_count=1,
            max_unsupported_claim_ratio=1.0,
            require_llm_semantic_audit=True,
        ),
    )

    assert report.passed
    assert report.metrics["semantic_auditor_mode"] == "llm_enhanced"
    assert "overreach" in report.metrics["semantic_support_statuses"]


def test_quality_gate_fails_when_llm_semantic_auditor_required_but_missing():
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

    report = evaluate_research_answer(
        payload,
        evidence_qa_quality_gate().__class__(
            case_id="llm-required",
            expected_route="evidence_qa",
            expected_admission="accepted",
            min_citation_count=1,
            require_llm_semantic_audit=True,
        ),
    )

    assert not report.passed
    assert "llm_semantic_auditor_missing" in {finding.code for finding in report.findings}


def test_literature_review_quality_gate_requires_matrix_report_sections_and_paper_grounding():
    payload = _literature_review_payload()

    report = evaluate_research_answer(payload, literature_review_quality_gate())

    assert report.passed
    assert report.metrics["evidence_matrix_paper_count"] == 7
    assert report.metrics["evidence_matrix_theme_count"] == 4
    assert report.metrics["evidence_matrix_linked_cell_count"] >= 10
    report.assert_passed()


def test_literature_review_quality_gate_rejects_underpowered_or_context_only_matrix():
    payload = _literature_review_payload()
    payload["evidence_matrix"]["paper_count"] = 6
    payload["evidence_matrix"]["themes"] = payload["evidence_matrix"]["themes"][:3]
    payload["citations"][0]["source_type"] = "memory"
    payload["report"] = {"artifact": False, "sections": ["Evidence Matrix"]}

    report = evaluate_research_answer(payload, literature_review_quality_gate())

    assert not report.passed
    codes = {finding.code for finding in report.findings}
    assert "evidence_matrix_paper_count_too_low" in codes
    assert "evidence_matrix_theme_count_too_low" in codes
    assert "citation_source_type_invalid" in codes
    assert "literature_review_report_section_missing" in codes


def test_evidence_qa_quality_gate_accepts_paper_citation_without_page_when_traceable_fields_exist():
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
    payload["citations"][0]["page_start"] = None
    payload["citations"][0]["page_end"] = None

    report = evaluate_research_answer(payload, evidence_qa_quality_gate())

    assert report.passed
    assert "citation_page_missing" not in {finding.code for finding in report.findings}


def test_non_evidence_turn_quality_gate_accepts_skipped_retrieval_without_citations():
    report = evaluate_research_answer(
        _answer_payload(
            route="general_chat",
            admission="skipped",
            citation_count=0,
            summary_mode="",
            claim_count=0,
            approved=0,
            partial=0,
            unsupported=0,
        ),
        non_evidence_turn_quality_gate(),
    )

    assert report.passed
    assert report.metrics["citation_count"] == 0


def test_research_quality_eval_cli_returns_nonzero_for_failed_gate(tmp_path):
    answer_path = tmp_path / "answer.json"
    answer_path.write_text(
        json.dumps(
            _answer_payload(
                route="evidence_qa",
                admission="accepted",
                citation_count=0,
                summary_mode="deterministic_extractive",
                claim_count=2,
                approved=0,
                partial=0,
                unsupported=2,
            )
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "backend.scripts.research_quality_eval",
            str(answer_path),
            "--case",
            "whole_paper_summary",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "citation_count_too_low" in result.stdout


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
        citation["title"] = f"LEO Beamforming Study {index % len(paper_ids) + 1}"
        citation["source_identity"] = {"paper_id": paper_id}
        citation["citation_label"] = f"[{paper_id}:Method:{index + 1}]"
    themes = []
    for theme_index, label in enumerate(["Methods", "Evidence strength", "Agreements", "Limitations"], start=1):
        cells = []
        for paper_index, paper_id in enumerate(paper_ids, start=1):
            cells.append(
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
            )
        themes.append(
            {
                "theme_id": f"theme-{theme_index}",
                "label": label,
                "synthesis_claim": f"The corpus supports a cross-paper claim about {label}.",
                "evidence_strength": "strong",
                "paper_cells": cells,
            }
        )
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
        "themes": themes,
        "agreements": ["The papers agree that LEO beamforming is constrained by deployment trade-offs."],
        "disagreements": ["The papers differ in method emphasis and evaluation settings."],
        "gaps": ["Open gaps remain around real-world validation."],
        "limitations": ["Evidence comes from admitted paper snippets only."],
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
