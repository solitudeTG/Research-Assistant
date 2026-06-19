from pathlib import Path

from backend.research_assistant.ingestion import ingest_uploaded_paper, is_research_document
from backend.research_assistant.parsers import ParsedPaperDocument, ParsedSection


def test_ingest_uploaded_paper_creates_canonical_manifest_and_chunks(tmp_path: Path):
    paper = tmp_path / "sample-paper.txt"
    paper.write_text(
        "\n".join(
            [
                "Title: Evidence Boundaries for Research Agents",
                "Authors: Ada Lovelace; Grace Hopper",
                "Abstract: This paper studies citation evidence boundaries.",
                "",
                "1 Introduction",
                "Research assistants need traceable evidence.",
                "They must not cite memory as evidence.",
                "",
                "2 Method",
                "We compare lexical and semantic retrieval.",
            ]
        ),
        encoding="utf-8",
    )

    result = ingest_uploaded_paper(
        file_path=paper,
        session_id="session-123",
        user_id="user-123",
        workspace_dir=tmp_path,
    )

    assert result.paper.paper_id
    assert result.paper.title == "Evidence Boundaries for Research Agents"
    assert result.paper.authors == ["Ada Lovelace", "Grace Hopper"]
    assert result.chunks
    assert result.chunks[0].source.paper_id == result.paper.paper_id
    assert result.chunks[0].source.file_path == str(paper)
    assert result.chunks[0].source.section

    manifest = tmp_path / "research_data" / result.paper.paper_id / "canonical_paper.json"
    evidence_markdown = tmp_path / "research_data" / result.paper.paper_id / "evidence_preview.md"

    assert manifest.is_file()
    assert evidence_markdown.is_file()
    assert "citation evidence" in evidence_markdown.read_text(encoding="utf-8")


def test_is_research_document_only_accepts_paper_like_files():
    assert is_research_document(Path("paper.pdf"))
    assert is_research_document(Path("notes.md"))
    assert is_research_document(Path("excerpt.txt"))
    assert not is_research_document(Path("figure.png"))
    assert not is_research_document(Path("archive.zip"))


def test_ingest_uploaded_pdf_uses_parser_document_with_page_identity(tmp_path: Path, monkeypatch):
    paper = tmp_path / "paper.pdf"
    paper.write_bytes(b"%PDF-1.4\n")

    def fake_parse_pdf_document(path):
        assert path == paper
        return ParsedPaperDocument(
            title="Structured PDF Research",
            authors=["Ada Lovelace"],
            abstract="A paper parsed through the PDF stack.",
            sections=[
                ParsedSection(
                    name="Introduction",
                    text="PDF evidence keeps page identity.",
                    page=3,
                )
            ],
            parser="grobid-tei",
            raw_text="Structured PDF Research\nPDF evidence keeps page identity.",
        )

    monkeypatch.setattr("backend.research_assistant.ingestion.parse_pdf_document", fake_parse_pdf_document)

    result = ingest_uploaded_paper(
        file_path=paper,
        session_id="session-123",
        user_id="user-123",
        workspace_dir=tmp_path,
    )

    assert result.paper.title == "Structured PDF Research"
    assert result.paper.parser == "grobid-tei"
    assert result.chunks[0].source.section == "Introduction"
    assert result.chunks[0].source.page == 3
    assert result.chunks[0].text == "PDF evidence keeps page identity."
