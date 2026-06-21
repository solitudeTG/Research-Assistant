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
            context_memory=[
                {
                    "memory_id": "mem-1",
                    "layer": "l2",
                    "title": "Retrieval preference",
                    "content": "Prefer hybrid retrieval for scholarly terminology.",
                    "source_type": "memory",
                    "context_only": True,
                    "relevance_score": 0.67,
                    "recall_reason": "matched question terms: hybrid, retrieval; source answer answer-1.",
                    "source_subject_type": "answer",
                    "source_subject_id": "answer-1",
                }
            ],
        )

    persisted = {}
    persisted_audit = {}

    async def fake_persist(database_url, *, report_id, evidence_rows):
        persisted["database_url"] = database_url
        persisted["report_id"] = report_id
        persisted["evidence_rows"] = evidence_rows

    async def fake_persist_audit(database_url, *, audit_id, session_id, subject_type, subject_id, audit):
        persisted_audit["database_url"] = database_url
        persisted_audit["audit_id"] = audit_id
        persisted_audit["session_id"] = session_id
        persisted_audit["subject_type"] = subject_type
        persisted_audit["subject_id"] = subject_id
        persisted_audit["status"] = audit.status

    monkeypatch.setattr("backend.research_assistant.reports.answer_research_question", fake_answer)
    monkeypatch.setattr(
        "backend.research_assistant.reports.persist_report_evidence_map_to_database",
        fake_persist,
    )
    monkeypatch.setattr(
        "backend.research_assistant.reports.persist_audit_result_to_database",
        fake_persist_audit,
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
    assert "Evidence Audit" in markdown
    assert "Status: `approved`" in markdown
    assert "### Claim Checks" in markdown
    assert "| Claim | Status | Support | Evidence IDs | Notes |" in markdown
    assert "| Hybrid retrieval improves recall. [paper-1:Results:4] | `approved` | `1.00` | `17` |  |" in markdown
    assert "- Source: Hybrid Retrieval" in markdown
    assert "- Source type: `paper`" in markdown
    assert "- Paper: Hybrid Retrieval" not in markdown
    assert "Citation evidence sources: `paper`, `web`, `database`" in markdown
    assert "Context-only sources: `memory`, `model_reasoning`, `process_trace`, `tool_logs`" in markdown
    assert "Hybrid retrieval improves recall. [paper-1:Results:4]" in markdown
    assert "## Context-Only Memory" in markdown
    assert "| Memory | Layer | Score | Reason |" in markdown
    assert "| Retrieval preference | `l2` | `0.67` | matched question terms: hybrid, retrieval; source answer answer-1. |" in markdown
    assert "These memory entries are context only and are not citation evidence." in markdown
    assert "This Markdown artifact can cite paper, web, or database evidence when present." in markdown
    assert "This generated report currently used uploaded-paper retrieval." in markdown
    assert "only uploaded paper chunks as citation evidence" not in markdown
    assert "Memory, model reasoning, process trace, and tool logs remain context-only" in markdown
    assert evidence["audit"]["status"] == "approved"
    assert evidence["audit"]["boundaries"]["citation_evidence"] == ["paper", "web", "database"]
    assert evidence["context_memory_count"] == 1
    assert evidence["context_memory"][0]["memory_id"] == "mem-1"
    assert evidence["context_memory"][0]["source_type"] == "memory"
    assert evidence["context_memory"][0]["context_only"] is True
    assert evidence["audit"]["claims"][0]["support_score"] == 1.0
    assert evidence["evidence"][0]["evidence_id"] == 17
    assert evidence["evidence"][0]["claim_text"] == "Hybrid retrieval improves recall. [paper-1:Results:4]"
    assert persisted["database_url"] == "postgresql://test"
    assert persisted["report_id"] == report.report_id
    assert persisted["evidence_rows"] == [(17, "evidence-1", "Hybrid retrieval improves recall. [paper-1:Results:4]")]
    assert persisted_audit == {
        "database_url": "postgresql://test",
        "audit_id": f"{report.report_id}:audit",
        "session_id": "session-1",
        "subject_type": "report",
        "subject_id": report.report_id,
        "status": "approved",
    }


@pytest.mark.asyncio
async def test_generate_markdown_research_report_keeps_unsupported_claims_out_of_findings(tmp_path, monkeypatch):
    async def fake_answer(**kwargs):
        return ResearchAnswer(
            content=(
                "Based on uploaded paper evidence:\n"
                "1. Hybrid retrieval improves recall. [paper-1:Results:4]\n"
                "2. Hybrid retrieval proves clinical benefit."
            ),
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

    async def fake_persist(*args, **kwargs):
        return None

    monkeypatch.setattr("backend.research_assistant.reports.answer_research_question", fake_answer)
    monkeypatch.setattr(
        "backend.research_assistant.reports.persist_report_evidence_map_to_database",
        fake_persist,
    )
    monkeypatch.setattr(
        "backend.research_assistant.reports.persist_audit_result_to_database",
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
    findings_section = markdown.split("## Citation Evidence", maxsplit=1)[0]

    assert "Status: `partial`" in markdown
    assert "Hybrid retrieval improves recall. [paper-1:Results:4]" in findings_section
    assert "Hybrid retrieval proves clinical benefit." not in findings_section
    assert (
        "| Hybrid retrieval proves clinical benefit. | `unsupported` | `0.40` |  | "
        "Nearest citation evidence: 17 with lexical support 0.40. No explicit citation label was attached to this claim. |"
    ) in markdown
