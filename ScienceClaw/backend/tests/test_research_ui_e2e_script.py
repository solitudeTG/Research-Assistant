import pytest

from backend.scripts.research_ui_e2e import (
    ResearchUiE2EResult,
    assert_semantic_multi_paper_live_loop,
    assert_semantic_overreach_live_loop,
    assert_research_ui_loop,
    build_api_base_url,
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
