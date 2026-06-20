from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import shortuuid

from backend.research_assistant.answering import (
    ResearchAnswer,
    ResearchCitation,
    answer_research_question,
)
from backend.research_assistant.storage.database import (
    persist_audit_result_to_database,
    persist_report_evidence_map_to_database,
)


@dataclass(frozen=True)
class MarkdownReportArtifact:
    report_id: str
    title: str
    question: str
    markdown_path: str
    evidence_map_path: str
    citation_count: int

    def to_dict(self) -> dict:
        return asdict(self)


async def generate_markdown_research_report(
    *,
    database_url: str,
    session_id: str,
    question: str,
    workspace_dir: Path,
    embedding_dimensions: int,
    embedding_model: str,
    limit: int = 8,
) -> MarkdownReportArtifact:
    answer = await answer_research_question(
        database_url=database_url,
        session_id=session_id,
        question=question,
        embedding_dimensions=embedding_dimensions,
        embedding_model=embedding_model,
        limit=limit,
    )
    report_id = f"research-report-{shortuuid.uuid()}"
    title = _report_title(question)
    report_dir = workspace_dir / "research_reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = report_dir / f"{report_id}.md"
    evidence_map_path = report_dir / f"{report_id}.evidence.json"

    markdown_path.write_text(
        _compose_markdown_report(
            report_id=report_id,
            title=title,
            question=question,
            answer=answer,
        ),
        encoding="utf-8",
    )
    evidence_map = _build_evidence_map(report_id=report_id, answer=answer)
    evidence_map_path.write_text(
        json.dumps(evidence_map, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    await persist_report_evidence_map_to_database(
        database_url,
        report_id=report_id,
        evidence_rows=[
            (
                item["evidence_id"],
                item["markdown_anchor"],
                item["claim_text"],
            )
            for item in evidence_map["evidence"]
        ],
    )
    await persist_audit_result_to_database(
        database_url,
        audit_id=f"{report_id}:audit",
        session_id=session_id,
        subject_type="report",
        subject_id=report_id,
        audit=answer.audit,
    )

    return MarkdownReportArtifact(
        report_id=report_id,
        title=title,
        question=question,
        markdown_path=str(markdown_path),
        evidence_map_path=str(evidence_map_path),
        citation_count=answer.citation_count,
    )


def _compose_markdown_report(
    *,
    report_id: str,
    title: str,
    question: str,
    answer: ResearchAnswer,
) -> str:
    generated_at = datetime.now(timezone.utc).isoformat()
    lines = [
        f"# {title}",
        "",
        f"- Report ID: `{report_id}`",
        f"- Generated at: `{generated_at}`",
        "- Evidence scope: uploaded papers only",
        "",
        "## Research Question",
        "",
        question.strip(),
        "",
        "## Evidence-Grounded Answer",
        "",
        *_compose_audited_answer_lines(answer),
        "",
        "## Citation Evidence",
        "",
    ]
    if not answer.citations:
        lines.append("No paper citation evidence was found for this report.")
    else:
        for index, citation in enumerate(answer.citations, start=1):
            anchor = _citation_anchor(index)
            lines.extend(
                [
                    f"### {anchor} {citation.citation_label}",
                    "",
                    f"- Paper: {citation.title}",
                    f"- Section: {citation.section}",
                    f"- Page: {_page_label(citation)}",
                    f"- Chunk: `{citation.chunk_id}`",
                    "",
                    "> " + citation.quote.replace("\n", "\n> "),
                    "",
                ]
            )
    lines.extend(
        [
            "## Evidence Audit",
            "",
            f"- Status: `{answer.audit.status}`",
            f"- Claims: {answer.audit.claim_count}",
            f"- Approved: {answer.audit.approved_claim_count}",
            f"- Unsupported: {answer.audit.unsupported_claim_count}",
            f"- Invalid sources: {answer.audit.invalid_source_count}",
            f"- Citation evidence sources: {_format_sources(answer.audit.boundaries['citation_evidence'])}",
            f"- Context-only sources: {_format_sources(answer.audit.boundaries['context_only'])}",
            "",
            "### Claim Checks",
            "",
            "| Claim | Status | Evidence IDs | Notes |",
            "| --- | --- | --- | --- |",
            *_compose_claim_check_rows(answer),
            "",
            "## Evidence Boundary",
            "",
            (
                "This Markdown artifact treats only uploaded paper chunks as citation evidence. "
                "Memory, model reasoning, process trace, and tool logs are not cited as evidence."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _build_evidence_map(*, report_id: str, answer: ResearchAnswer) -> dict:
    return {
        "report_id": report_id,
        "evidence_scope": "uploaded_papers_only",
        "citation_count": answer.citation_count,
        "audit": answer.audit.to_dict(),
        "evidence": [
            {
                "evidence_id": citation.evidence_id,
                "markdown_anchor": _citation_anchor(index),
                "claim_text": citation.quote,
                "citation": citation.to_dict(),
            }
            for index, citation in enumerate(answer.citations, start=1)
        ],
    }


def _report_title(question: str) -> str:
    title = re.sub(r"\s+", " ", question.strip()).strip(" .")
    if not title:
        return "Paper Research Note"
    if len(title) > 80:
        title = title[:77].rstrip() + "..."
    return title


def _citation_anchor(index: int) -> str:
    return f"evidence-{index}"


def _page_label(citation: ResearchCitation) -> str:
    if citation.page_start is None:
        return "not available"
    if citation.page_end and citation.page_end != citation.page_start:
        return f"{citation.page_start}-{citation.page_end}"
    return str(citation.page_start)


def _format_sources(sources: list[str]) -> str:
    return ", ".join(f"`{source}`" for source in sources)


def _compose_audited_answer_lines(answer: ResearchAnswer) -> list[str]:
    approved_claims = [
        claim.claim_text
        for claim in answer.audit.claims
        if claim.status == "approved"
    ]
    if approved_claims:
        return [
            "Only claims approved by Evidence Audit are listed here:",
            "",
            *[f"{index}. {claim_text}" for index, claim_text in enumerate(approved_claims, start=1)],
        ]
    return [
        "No claims passed Evidence Audit for this report. See Claim Checks before using this output.",
    ]


def _compose_claim_check_rows(answer: ResearchAnswer) -> list[str]:
    rows: list[str] = []
    for claim in answer.audit.claims:
        rows.append(
            "| "
            + " | ".join(
                [
                    _table_cell(claim.claim_text),
                    f"`{claim.status}`",
                    _format_evidence_ids(claim.evidence_ids),
                    _table_cell(" ".join(claim.notes)),
                ]
            )
            + " |"
        )
    if not rows:
        return ["| No auditable claims. | `unsupported` |  | No answer content was available. |"]
    return rows


def _format_evidence_ids(evidence_ids: list[int]) -> str:
    return ", ".join(f"`{evidence_id}`" for evidence_id in evidence_ids)


def _table_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", "<br>")
