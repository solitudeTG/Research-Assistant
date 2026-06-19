from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import httpx


@dataclass(frozen=True)
class ParsedSection:
    name: str
    text: str
    page: int | None = None


@dataclass(frozen=True)
class ParsedPaperDocument:
    title: str
    authors: list[str]
    abstract: str
    sections: list[ParsedSection]
    parser: str
    raw_text: str


class PaperParseError(RuntimeError):
    pass


def parse_pdf_document(
    path: Path,
    *,
    grobid_base_url: str | None = None,
    timeout_seconds: float = 30.0,
) -> ParsedPaperDocument:
    errors: list[str] = []
    grobid_url = (grobid_base_url or os.environ.get("RESEARCH_GROBID_URL") or "").rstrip("/")
    if grobid_url:
        try:
            return _parse_pdf_with_grobid(path, grobid_url=grobid_url, timeout_seconds=timeout_seconds)
        except Exception as exc:  # pragma: no cover - exact network failures vary
            errors.append(f"grobid: {exc}")

    try:
        return _parse_pdf_with_docling(path)
    except Exception as exc:
        errors.append(f"docling: {exc}")

    try:
        return _parse_pdf_with_pymupdf(path)
    except Exception as exc:
        errors.append(f"pymupdf: {exc}")

    raise PaperParseError("PDF parsing failed; " + "; ".join(errors))


def _parse_pdf_with_grobid(
    path: Path,
    *,
    grobid_url: str,
    timeout_seconds: float,
) -> ParsedPaperDocument:
    with path.open("rb") as pdf_file:
        response = httpx.post(
            f"{grobid_url}/api/processFulltextDocument",
            files={"input": (path.name, pdf_file, "application/pdf")},
            data={
                "consolidateHeader": "1",
                "consolidateCitations": "0",
                "includeRawCitations": "1",
            },
            timeout=timeout_seconds,
            trust_env=False,
        )
    response.raise_for_status()
    if not response.text.strip():
        raise PaperParseError("GROBID returned empty TEI")
    parsed = _parse_grobid_tei(response.text, fallback_title=path.stem)
    if not parsed.raw_text.strip():
        raise PaperParseError("GROBID returned TEI without citation text")
    return ParsedPaperDocument(
        title=parsed.title,
        authors=parsed.authors,
        abstract=parsed.abstract,
        sections=parsed.sections,
        parser="grobid-tei",
        raw_text=parsed.raw_text,
    )


def _parse_grobid_tei(tei_xml: str, *, fallback_title: str) -> ParsedPaperDocument:
    root = ET.fromstring(tei_xml)
    ns = {"tei": "http://www.tei-c.org/ns/1.0"}
    title = _first_text(
        root,
        [
            ".//tei:titleStmt/tei:title",
            ".//tei:fileDesc//tei:title[@level='a']",
            ".//tei:fileDesc//tei:title",
        ],
        ns,
    ) or fallback_title
    authors = _tei_authors(root, ns)
    abstract = _node_text(root.find(".//tei:profileDesc/tei:abstract", ns))
    sections = _tei_sections(root, ns)
    raw_text = "\n\n".join([abstract] + [section.text for section in sections if section.text]).strip()
    return ParsedPaperDocument(
        title=title,
        authors=authors,
        abstract=abstract,
        sections=sections,
        parser="grobid-tei",
        raw_text=raw_text,
    )


def _parse_pdf_with_docling(path: Path) -> ParsedPaperDocument:
    from docling.document_converter import DocumentConverter

    result = DocumentConverter().convert(str(path))
    document = result.document
    markdown = document.export_to_markdown()
    text = markdown.strip()
    if not text:
        raise PaperParseError("Docling returned empty text")
    return ParsedPaperDocument(
        title=_markdown_title(text) or path.stem,
        authors=[],
        abstract="",
        sections=[ParsedSection(name="Document", text=text, page=None)],
        parser="docling-fallback",
        raw_text=text,
    )


def _parse_pdf_with_pymupdf(path: Path) -> ParsedPaperDocument:
    import fitz

    sections: list[ParsedSection] = []
    raw_pages: list[str] = []
    with fitz.open(path) as document:
        for page_index, page in enumerate(document, start=1):
            text = page.get_text("text").strip()
            if not text:
                continue
            raw_pages.append(text)
            sections.append(ParsedSection(name=f"Page {page_index}", text=text, page=page_index))

    raw_text = "\n\n".join(raw_pages).strip()
    if not raw_text:
        raise PaperParseError("PyMuPDF returned empty text")
    return ParsedPaperDocument(
        title=_first_non_empty_line(raw_text) or path.stem,
        authors=[],
        abstract="",
        sections=sections,
        parser="pymupdf-fallback",
        raw_text=raw_text,
    )


def _first_text(root: ET.Element, paths: Iterable[str], ns: dict[str, str]) -> str:
    for path in paths:
        text = _node_text(root.find(path, ns))
        if text:
            return text
    return ""


def _node_text(node: ET.Element | None) -> str:
    if node is None:
        return ""
    return re.sub(r"\s+", " ", " ".join(node.itertext())).strip()


def _tei_authors(root: ET.Element, ns: dict[str, str]) -> list[str]:
    authors: list[str] = []
    for author in root.findall(".//tei:sourceDesc//tei:author", ns):
        name = _node_text(author.find(".//tei:persName", ns)) or _node_text(author)
        if name and name not in authors:
            authors.append(name)
    return authors


def _tei_sections(root: ET.Element, ns: dict[str, str]) -> list[ParsedSection]:
    sections: list[ParsedSection] = []
    body = root.find(".//tei:text/tei:body", ns)
    if body is None:
        return sections
    for index, div in enumerate(body.findall(".//tei:div", ns), start=1):
        head = _node_text(div.find("tei:head", ns)) or f"Section {index}"
        paragraphs: list[str] = []
        page = _first_page_number(div, ns)
        for paragraph in div.findall(".//tei:p", ns):
            text = _node_text(paragraph)
            if text:
                paragraphs.append(text)
        section_text = "\n".join(paragraphs).strip()
        if section_text:
            sections.append(ParsedSection(name=head, text=section_text, page=page))
    return sections


def _first_page_number(node: ET.Element, ns: dict[str, str]) -> int | None:
    for page_break in node.findall(".//tei:pb", ns):
        value = page_break.attrib.get("n")
        if value and value.isdigit():
            return int(value)
    return None


def _markdown_title(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    return ""


def _first_non_empty_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""
