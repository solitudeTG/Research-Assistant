import json

import pytest

from backend.research_assistant.answering import ResearchAnswer, ResearchCitation
from backend.research_assistant.reports import generate_markdown_research_report


@pytest.mark.asyncio
async def test_generate_markdown_research_report_writes_artifact_and_evidence_map(tmp_path, monkeypatch):
    async def fake_answer(**kwargs):
        assert kwargs["database_url"] == "postgresql://test"
        assert kwargs["session_id"] == "session-1"
        assert kwargs["question"] == "What does the paper say about retrieval?"
        return ResearchAnswer(
            content="Based on uploaded paper evidence:\n1. Hybrid retrieval improves recall. [paper-1:Results:4]",
            citations=[
                ResearchCitation(
                    evidence_id=17,
                    chunk_id="chunk-17",
                    paper_id="paper-1",
                    title="Hybrid Retrieval",
                    section="Results",
                    page_start=4,
                    page_end=4,
                    quote="Hybrid retrieval improves recall.",
                    citation_label="[paper-1:Results:4]",
                )
            ],
        )

    persisted = {}

    async def fake_persist(database_url, *, report_id, evidence_rows):
        persisted["database_url"] = database_url
        persisted["report_id"] = report_id
        persisted["evidence_rows"] = evidence_rows

    monkeypatch.setattr("backend.research_assistant.reports.answer_research_question", fake_answer)
    monkeypatch.setattr(
        "backend.research_assistant.reports.persist_report_evidence_map_to_database",
        fake_persist,
    )

    report = await generate_markdown_research_report(
        database_url="postgresql://test",
        session_id="session-1",
        question="What does the paper say about retrieval?",
        workspace_dir=tmp_path,
        embedding_dimensions=8,
        embedding_model="local-hashing-v1",
        limit=5,
    )

    markdown = (tmp_path / "research_reports" / f"{report.report_id}.md").read_text(encoding="utf-8")
    evidence = json.loads(
        (tmp_path / "research_reports" / f"{report.report_id}.evidence.json").read_text(encoding="utf-8")
    )

    assert report.citation_count == 1
    assert "Evidence scope: uploaded papers only" in markdown
    assert "Hybrid retrieval improves recall. [paper-1:Results:4]" in markdown
    assert "Memory, model reasoning, process trace, and tool logs are not cited" in markdown
    assert evidence["evidence"][0]["evidence_id"] == 17
    assert persisted["database_url"] == "postgresql://test"
    assert persisted["report_id"] == report.report_id
    assert persisted["evidence_rows"] == [(17, "evidence-1", "Hybrid retrieval improves recall.")]
