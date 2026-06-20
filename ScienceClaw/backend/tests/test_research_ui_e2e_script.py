import pytest

from backend.scripts.research_ui_e2e import (
    ResearchUiE2EResult,
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
