import pytest

from backend.scripts.research_ui_e2e import (
    ResearchUiE2EResult,
    assert_literature_review_live_loop,
    assert_semantic_multi_paper_live_loop,
    assert_semantic_overreach_live_loop,
    assert_research_ui_loop,
    build_api_base_url,
    _write_e2e_outputs,
)


def test_assert_research_ui_loop_accepts_complete_evidence_loop():
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
        round_files=[
            "research-report-abc.evidence.json",
            "research-report-abc.md",
        ],
        error_events=[],
    )

    assert_research_ui_loop(result)


def test_assert_research_ui_loop_rejects_missing_trace_step():
    result = ResearchUiE2EResult(
        session_id="session-1",
        session_status="completed",
        citation_count=1,
        activity_steps=[
            "Research document uploaded",
            "Parsing research document",
            "Indexing paper evidence",
            "Markdown research artifact generated",
        ],
        round_files=[
            "research-report-abc.evidence.json",
            "research-report-abc.md",
        ],
        error_events=[],
    )

    with pytest.raises(AssertionError, match="Retrieving citation evidence"):
        assert_research_ui_loop(result)


def test_build_api_base_url_derives_v1_api_from_frontend_url():
    assert build_api_base_url("http://localhost:5173/") == "http://localhost:5173/api/v1"


def test_assert_semantic_multi_paper_live_loop_accepts_positive_and_refusal_cases():
    result = ResearchUiE2EResult(
        session_id="session-1",
        session_status="completed",
        citation_count=2,
        question_delivery="chat_ui",
        report_delivery="chat_ui",
        insufficient_question_delivery="chat_ui",
        activity_steps=[
            "Research document uploaded",
            "Parsing research document",
            "Indexing paper evidence",
            "Retrieving citation evidence",
            "Evidence audit completed",
            "Markdown research artifact generated",
        ],
        round_files=[
            "research-report-abc.evidence.json",
            "research-report-abc.md",
        ],
        error_events=[],
        answer_payload={
            "task_route": {"route": "evidence_qa"},
            "evidence_admission": {"decision": "accepted"},
            "citation_count": 2,
            "citations": [
                {
                    "evidence_id": 1,
                    "source_type": "paper",
                    "evidence_scope": "session",
                    "paper_id": "paper-a",
                    "title": "Paper A",
                    "section": "Intro",
                    "page_start": 1,
                    "page_end": 1,
                    "chunk_id": "chunk-a",
                    "quote": "Paper A frames LEO beamforming as narrow beam control.",
                },
                {
                    "evidence_id": 2,
                    "source_type": "paper",
                    "evidence_scope": "session",
                    "paper_id": "paper-b",
                    "title": "Paper B",
                    "section": "Intro",
                    "page_start": 1,
                    "page_end": 1,
                    "chunk_id": "chunk-b",
                    "quote": "Paper B frames LEO beamforming as integrated communication and navigation.",
                },
            ],
            "audit": {
                "claim_count": 1,
                "approved_claim_count": 1,
                "partial_claim_count": 0,
                "unsupported_claim_count": 0,
                "invalid_source_count": 0,
                "claims": [
                    {
                        "claim_id": "claim-1",
                        "support_status": "supported",
                        "semantic_relevance_score": 1.0,
                        "source_quality_score": 1.0,
                        "cited_evidence": [{"paper_id": "paper-a", "quote": "Paper A frames LEO beamforming."}],
                    }
                ]
            },
            "context_boundaries": {
                "citation_evidence": ["paper", "web", "database"],
                "context_only_memory": ["memory"],
                "process_trace": ["tool_logs", "runtime_results", "agent_lifecycle"],
                "model_reasoning": ["model_reasoning"],
            },
        },
        insufficient_answer_payload={
            "citations": [],
            "citation_count": 0,
            "context_boundaries": {
                "citation_evidence": ["paper", "web", "database"],
                "context_only_memory": ["memory"],
                "process_trace": ["tool_logs", "runtime_results", "agent_lifecycle"],
                "model_reasoning": ["model_reasoning"],
            },
            "evidence_admission": {"decision": "insufficient", "reason": "insufficient_evidence_should_refuse"},
            "audit": {
                "claims": [
                    {
                        "claim_id": "claim-1",
                        "support_status": "insufficient_evidence",
                        "semantic_relevance_score": 0.0,
                        "source_quality_score": 0.0,
                        "cited_evidence": [],
                        "finding_code": "insufficient_evidence_should_refuse",
                    }
                ]
            },
        },
    )

    assert_semantic_multi_paper_live_loop(result)


def test_assert_semantic_multi_paper_live_loop_rejects_non_chat_delivery():
    result = ResearchUiE2EResult(
        session_id="session-1",
        session_status="completed",
        citation_count=2,
        question_delivery="api_fetch",
        report_delivery="chat_ui",
        insufficient_question_delivery="chat_ui",
        activity_steps=[
            "Research document uploaded",
            "Parsing research document",
            "Indexing paper evidence",
            "Retrieving citation evidence",
            "Evidence audit completed",
            "Markdown research artifact generated",
        ],
        round_files=["research-report-abc.evidence.json", "research-report-abc.md"],
        error_events=[],
        answer_payload={
            "task_route": {"route": "evidence_qa"},
            "evidence_admission": {"decision": "accepted"},
            "citations": [
                {
                    "evidence_id": 1,
                    "source_type": "paper",
                    "evidence_scope": "session",
                    "paper_id": "paper-a",
                    "title": "Paper A",
                    "section": "Intro",
                    "chunk_id": "chunk-a",
                    "quote": "Paper A frames LEO beamforming.",
                },
                {
                    "evidence_id": 2,
                    "source_type": "paper",
                    "evidence_scope": "session",
                    "paper_id": "paper-b",
                    "title": "Paper B",
                    "section": "Intro",
                    "chunk_id": "chunk-b",
                    "quote": "Paper B frames LEO beamforming.",
                },
            ],
            "audit": {
                "claim_count": 1,
                "approved_claim_count": 1,
                "partial_claim_count": 0,
                "unsupported_claim_count": 0,
                "invalid_source_count": 0,
                "claims": [
                    {
                        "claim_id": "claim-1",
                        "support_status": "supported",
                        "semantic_relevance_score": 1.0,
                        "source_quality_score": 1.0,
                        "cited_evidence": [{"paper_id": "paper-a", "quote": "Paper A frames LEO beamforming."}],
                    }
                ],
            },
            "context_boundaries": {
                "citation_evidence": ["paper", "web", "database"],
                "context_only_memory": ["memory"],
                "process_trace": ["tool_logs", "runtime_results", "agent_lifecycle"],
                "model_reasoning": ["model_reasoning"],
            },
        },
        insufficient_answer_payload={
            "citations": [],
            "context_boundaries": {
                "citation_evidence": ["paper", "web", "database"],
                "context_only_memory": ["memory"],
                "process_trace": ["tool_logs", "runtime_results", "agent_lifecycle"],
                "model_reasoning": ["model_reasoning"],
            },
            "evidence_admission": {"decision": "insufficient", "reason": "insufficient_evidence_should_refuse"},
            "audit": {
                "claims": [
                    {
                        "claim_id": "claim-1",
                        "support_status": "insufficient_evidence",
                        "semantic_relevance_score": 0.0,
                        "source_quality_score": 0.0,
                        "cited_evidence": [],
                        "finding_code": "insufficient_evidence_should_refuse",
                    }
                ]
            },
        },
    )

    with pytest.raises(AssertionError, match="Chat UI"):
        assert_semantic_multi_paper_live_loop(result)


def test_assert_semantic_multi_paper_live_loop_uses_quality_gate():
    result = ResearchUiE2EResult(
        session_id="session-1",
        session_status="completed",
        citation_count=2,
        question_delivery="chat_ui",
        report_delivery="chat_ui",
        insufficient_question_delivery="chat_ui",
        activity_steps=[
            "Research document uploaded",
            "Parsing research document",
            "Indexing paper evidence",
            "Retrieving citation evidence",
            "Evidence audit completed",
            "Markdown research artifact generated",
        ],
        round_files=["research-report-abc.evidence.json", "research-report-abc.md"],
        error_events=[],
        answer_payload={
            "task_route": {"route": "evidence_qa"},
            "evidence_admission": {"decision": "accepted"},
            "citations": [
                {
                    "evidence_id": 1,
                    "source_type": "paper",
                    "evidence_scope": "session",
                    "paper_id": "paper-a",
                    "title": "Paper A",
                    "section": "Intro",
                    "chunk_id": "chunk-a",
                    "quote": "Paper A frames LEO beamforming.",
                },
                {
                    "evidence_id": 2,
                    "source_type": "paper",
                    "evidence_scope": "session",
                    "paper_id": "paper-b",
                    "title": "Paper B",
                    "section": "Intro",
                    "chunk_id": "chunk-b",
                    "quote": "Paper B frames LEO beamforming.",
                },
            ],
            "audit": {
                "claim_count": 2,
                "approved_claim_count": 0,
                "partial_claim_count": 0,
                "unsupported_claim_count": 2,
                "invalid_source_count": 0,
                "claims": [
                    {
                        "claim_id": "claim-1",
                        "support_status": "unsupported",
                        "semantic_relevance_score": 0.1,
                        "source_quality_score": 1.0,
                        "cited_evidence": [{"paper_id": "paper-a", "quote": "Paper A frames LEO beamforming."}],
                    },
                    {
                        "claim_id": "claim-2",
                        "support_status": "unsupported",
                        "semantic_relevance_score": 0.1,
                        "source_quality_score": 1.0,
                        "cited_evidence": [{"paper_id": "paper-b", "quote": "Paper B frames LEO beamforming."}],
                    },
                ],
            },
            "context_boundaries": {
                "citation_evidence": ["paper", "web", "database"],
                "context_only_memory": ["memory"],
                "process_trace": ["tool_logs", "runtime_results", "agent_lifecycle"],
                "model_reasoning": ["model_reasoning"],
            },
        },
        insufficient_answer_payload={
            "citations": [],
            "context_boundaries": {
                "citation_evidence": ["paper", "web", "database"],
                "context_only_memory": ["memory"],
                "process_trace": ["tool_logs", "runtime_results", "agent_lifecycle"],
                "model_reasoning": ["model_reasoning"],
            },
            "evidence_admission": {"decision": "insufficient", "reason": "insufficient_evidence_should_refuse"},
            "audit": {
                "claims": [
                    {
                        "claim_id": "claim-1",
                        "support_status": "insufficient_evidence",
                        "semantic_relevance_score": 0.0,
                        "source_quality_score": 0.0,
                        "cited_evidence": [],
                        "finding_code": "insufficient_evidence_should_refuse",
                    }
                ]
            },
        },
    )

    with pytest.raises(AssertionError, match="unsupported_claim_ratio_exceeded"):
        assert_semantic_multi_paper_live_loop(result)


def test_assert_literature_review_live_loop_accepts_7paper_matrix_and_report():
    result = ResearchUiE2EResult(
        session_id="session-1",
        session_status="completed",
        citation_count=14,
        question_delivery="chat_ui",
        report_delivery="chat_ui",
        activity_steps=[
            "Research document uploaded",
            "Parsing research document",
            "Indexing paper evidence",
            "Selected 7 papers for literature review",
            "Built evidence matrix",
            "Audited synthesis claims",
            "Generated literature review report",
        ],
        round_files=[
            "research-report-abc.evidence.json",
            "research-report-abc.evidence-matrix.json",
            "research-report-abc.md",
        ],
        error_events=[],
        answer_payload=_literature_review_answer_payload(),
        report_payload={
            "report_id": "report-1",
            "markdown_path": "research-report-abc.md",
            "evidence_map_path": "research-report-abc.evidence.json",
            "evidence_matrix_path": "research-report-abc.evidence-matrix.json",
        },
    )

    assert_literature_review_live_loop(result, min_paper_count=7)


def test_assert_literature_review_live_loop_rejects_six_papers():
    result = ResearchUiE2EResult(
        session_id="session-1",
        session_status="completed",
        citation_count=12,
        question_delivery="chat_ui",
        report_delivery="chat_ui",
        activity_steps=[
            "Selected 6 papers for literature review",
            "Built evidence matrix",
            "Audited synthesis claims",
            "Generated literature review report",
        ],
        round_files=["research-report-abc.evidence.json", "research-report-abc.md"],
        error_events=[],
        answer_payload=_literature_review_answer_payload(paper_count=6),
        report_payload={"report_id": "report-1"},
    )

    with pytest.raises(AssertionError, match="at least 7"):
        assert_literature_review_live_loop(result, min_paper_count=7)


def test_assert_literature_review_live_loop_rejects_missing_report_sidecar_paths():
    result = ResearchUiE2EResult(
        session_id="session-1",
        session_status="completed",
        citation_count=14,
        question_delivery="chat_ui",
        report_delivery="chat_ui",
        activity_steps=[
            "Research document uploaded",
            "Parsing research document",
            "Indexing paper evidence",
            "Selected 7 papers for literature review",
            "Built evidence matrix",
            "Audited synthesis claims",
            "Generated literature review report",
        ],
        round_files=[
            "research-report-abc.evidence.json",
            "research-report-abc.md",
        ],
        error_events=[],
        answer_payload=_literature_review_answer_payload(),
        report_payload={
            "report_id": "report-1",
            "markdown_path": "research-report-abc.md",
            "evidence_map_path": "research-report-abc.evidence.json",
        },
    )

    with pytest.raises(AssertionError, match="evidence_matrix_path"):
        assert_literature_review_live_loop(result, min_paper_count=7)


def test_write_e2e_outputs_requires_literature_review_artifact_files(tmp_path):
    result = ResearchUiE2EResult(
        session_id="session-1",
        session_status="completed",
        citation_count=14,
        question_delivery="chat_ui",
        report_delivery="chat_ui",
        activity_steps=[],
        round_files=[],
        error_events=[],
        answer_payload=_literature_review_answer_payload(),
        report_payload={
            "report_id": "report-1",
            "markdown_path": str(tmp_path / "missing-report.md"),
            "evidence_map_path": str(tmp_path / "missing.evidence.json"),
            "evidence_matrix_path": str(tmp_path / "missing.evidence-matrix.json"),
        },
    )

    with pytest.raises(FileNotFoundError, match="markdown_path"):
        _write_e2e_outputs(result, tmp_path / "out", literature_review=True)


def test_assert_semantic_overreach_live_loop_accepts_llm_enhanced_case_c():
    result = ResearchUiE2EResult(
        session_id="session-1",
        session_status="completed",
        citation_count=1,
        question_delivery="chat_ui",
        activity_steps=[
            "Research document uploaded",
            "Parsing research document",
            "Indexing paper evidence",
            "Retrieving citation evidence",
            "Deterministic evidence audit completed",
            "LLM semantic auditor completed",
        ],
        round_files=[],
        error_events=[],
        answer_payload=_case_c_answer_payload(
            semantic_mode="llm_enhanced",
            finding_code="llm_overreach",
            support_status="overreach",
            llm_support_status="overreach",
            llm_rationale="The evidence is about LEO beamforming, not patient safety outcomes.",
            citations=[
                {
                    "evidence_id": 1,
                    "source_type": "paper",
                    "evidence_scope": "session",
                    "paper_id": "paper-a",
                    "title": "Paper A",
                    "section": "Intro",
                    "chunk_id": "chunk-a",
                    "quote": "Paper A frames LEO beamforming as narrow beam control.",
                }
            ],
        ),
    )

    assert_semantic_overreach_live_loop(result)


def test_assert_semantic_overreach_live_loop_rejects_deterministic_fallback_as_case_c_pass():
    result = ResearchUiE2EResult(
        session_id="session-1",
        session_status="completed",
        citation_count=0,
        question_delivery="chat_ui",
        activity_steps=[
            "Research document uploaded",
            "Parsing research document",
            "Indexing paper evidence",
            "Retrieving citation evidence",
            "Deterministic evidence audit completed",
            "LLM semantic auditor unavailable; deterministic audit used",
        ],
        round_files=[],
        error_events=[],
        answer_payload=_case_c_answer_payload(
            semantic_mode="llm_failed",
            semantic_status="PermissionDeniedError",
            finding_code="insufficient_evidence_should_refuse",
            support_status="insufficient_evidence",
            llm_support_status=None,
            llm_rationale=None,
            citations=[],
            admission="insufficient",
        ),
    )

    with pytest.raises(AssertionError, match="requires a live LLM semantic auditor"):
        assert_semantic_overreach_live_loop(result)


def test_assert_semantic_overreach_live_loop_rejects_missing_audit_trace():
    result = ResearchUiE2EResult(
        session_id="session-1",
        session_status="completed",
        citation_count=0,
        question_delivery="chat_ui",
        activity_steps=[
            "Research document uploaded",
            "Parsing research document",
            "Indexing paper evidence",
        ],
        round_files=[],
        error_events=[],
        answer_payload={
            "citations": [],
            "audit": {
                "claims": [
                    {
                        "claim_id": "claim-1",
                        "support_status": "insufficient_evidence",
                        "semantic_relevance_score": 0.0,
                        "source_quality_score": 0.0,
                        "cited_evidence": [],
                        "finding_code": "insufficient_evidence_should_refuse",
                    }
                ]
            },
        },
    )

    with pytest.raises(AssertionError, match="Deterministic evidence audit completed"):
        assert_semantic_overreach_live_loop(result)


def _case_c_answer_payload(
    *,
    semantic_mode,
    finding_code,
    support_status,
    llm_support_status,
    llm_rationale,
    citations,
    admission="accepted",
    semantic_status="completed",
):
    return {
        "content": "Evidence only supports LEO beamforming, not clinical patient safety outcomes.",
        "task_route": {"route": "evidence_qa"},
        "evidence_admission": {"decision": admission},
        "citations": citations,
        "citation_count": len(citations),
        "audit": {
            "claim_count": 1,
            "approved_claim_count": 0,
            "partial_claim_count": 0,
            "unsupported_claim_count": 1,
            "invalid_source_count": 0,
            "semantic_auditor": {
                "mode": semantic_mode,
                "llm_auditor_status": semantic_status,
                "claim_count": 1,
                "overreach_count": 1 if support_status == "overreach" else 0,
                "unsupported_count": 1 if support_status == "unsupported" else 0,
            },
            "claims": [
                {
                    "claim_id": "claim-1",
                    "support_status": support_status,
                    "deterministic_support_status": "partial",
                    "llm_support_status": llm_support_status,
                    "llm_rationale": llm_rationale,
                    "semantic_relevance_score": 0.2,
                    "source_quality_score": 1.0 if citations else 0.0,
                    "cited_evidence": citations,
                    "finding_code": finding_code,
                }
            ],
        },
        "context_boundaries": {
            "citation_evidence": ["paper", "web", "database"],
            "context_only_memory": ["memory"],
            "process_trace": ["tool_logs", "runtime_results", "agent_lifecycle"],
            "model_reasoning": ["model_reasoning"],
        },
    }


def _literature_review_answer_payload(*, paper_count=7):
    paper_ids = [f"paper-{index}" for index in range(1, paper_count + 1)]
    citations = [
        {
            "evidence_id": index,
            "source_type": "paper",
            "evidence_scope": "session",
            "paper_id": paper_ids[(index - 1) % len(paper_ids)],
            "title": f"Paper {index}",
            "section": "Method",
            "chunk_id": f"chunk-{index}",
            "quote": "The paper reports method evidence and bounded limitations.",
            "citation_label": f"[paper-{index}:Method:{index}]",
            "source_identity": {"paper_id": paper_ids[(index - 1) % len(paper_ids)]},
        }
        for index in range(1, max(10, paper_count * 2) + 1)
    ]
    return {
        "content": (
            "# Literature Review\n\n"
            "## Evidence Matrix\n\n"
            "## Cross-paper synthesis\n\n"
            "## Agreements\n\n"
            "## Disagreements / gaps\n\n"
            "## Limitations\n"
        ),
        "task_route": {"route": "evidence_qa"},
        "evidence_admission": {"decision": "accepted"},
        "citation_count": len(citations),
        "citations": citations,
        "summary_synthesis": {"mode": "evidence_matrix_literature_review"},
        "report": {
            "artifact": True,
            "sections": [
                "Evidence Matrix",
                "Cross-paper synthesis",
                "Agreements",
                "Disagreements / gaps",
                "Limitations",
            ],
        },
        "evidence_matrix": {
            "paper_count": paper_count,
            "papers": [
                {
                    "paper_id": paper_id,
                    "title": f"Paper {index}",
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
                    "synthesis_claim": f"Cross-paper claim about {label}.",
                    "evidence_strength": "moderate",
                    "paper_cells": [
                        {
                            "paper_id": paper_id,
                            "stance": "supports",
                            "contribution": f"{paper_id} contributes {label}.",
                            "method": "Simulation.",
                            "limitation": "Bounded setup.",
                            "evidence_ids": [paper_index],
                            "citation_labels": [f"[{paper_id}:Method:{paper_index}]"],
                            "quote_snippets": ["The paper reports method evidence."],
                            "support_status": "supported",
                        }
                        for paper_index, paper_id in enumerate(paper_ids, start=1)
                    ],
                }
                for theme_index, label in enumerate(["Methods", "Evidence", "Agreements", "Limitations"], start=1)
            ],
            "agreements": ["Shared LEO beamforming focus."],
            "disagreements": ["Different method emphasis."],
            "gaps": ["Real-world validation."],
            "limitations": ["Snippet-bounded evidence."],
        },
        "audit": {
            "claim_count": 4,
            "approved_claim_count": 3,
            "partial_claim_count": 1,
            "unsupported_claim_count": 0,
            "invalid_source_count": 0,
            "claims": [
                {
                    "claim_id": f"claim-{index}",
                    "support_status": "supported" if index < 4 else "partial",
                    "semantic_relevance_score": 1.0,
                    "source_quality_score": 1.0,
                    "cited_evidence": citations[:2],
                }
                for index in range(1, 5)
            ],
        },
        "context_boundaries": {
            "citation_evidence": ["paper", "web", "database"],
            "context_only_memory": ["memory"],
            "process_trace": ["tool_logs", "runtime_results", "agent_lifecycle"],
            "model_reasoning": ["model_reasoning"],
        },
    }
