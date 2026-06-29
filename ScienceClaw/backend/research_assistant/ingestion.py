from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .models import (
    CanonicalPaper,
    EvidenceSource,
    IngestionArtifact,
    IngestionResult,
    PaperChunk,
)
from .parsers import ParsedSection, parse_pdf_document


SECTION_HEADING_RE = re.compile(r"^\s*(?:\d+(?:\.\d+)*\s+)?([A-Z][A-Za-z0-9 ,:/()_-]{2,})\s*$")
RESEARCH_DOCUMENT_SUFFIXES = {".pdf", ".txt", ".md"}


def is_research_document(file_path: Path | str) -> bool:
    return Path(file_path).suffix.lower() in RESEARCH_DOCUMENT_SUFFIXES


def ingest_uploaded_paper(
    *,
    file_path: Path | str,
    session_id: str,
    user_id: str,
    workspace_dir: Path | str,
    paper_id_namespace: str | None = None,
) -> IngestionResult:
    path = Path(file_path)
    workspace = Path(workspace_dir)
    parsed = _extract_document(path)
    raw_text = parsed.raw_text
    paper_id = _paper_id(path, raw_text, namespace=paper_id_namespace)

    paper = CanonicalPaper(
        paper_id=paper_id,
        title=parsed.title or path.stem,
        authors=parsed.authors,
        abstract=parsed.abstract,
        file_path=str(path),
        session_id=session_id,
        user_id=user_id,
        parser=parsed.parser,
    )
    chunks = _build_chunks(paper, parsed.sections)
    if not chunks and raw_text.strip():
        chunks = [
            PaperChunk(
                chunk_id=f"{paper.paper_id}_chunk_0001",
                text=raw_text.strip(),
                source=EvidenceSource(
                    paper_id=paper.paper_id,
                    file_path=paper.file_path,
                    section="Document",
                ),
            )
        ]

    artifact_dir = workspace / "research_data" / paper.paper_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = artifact_dir / "canonical_paper.json"
    evidence_preview_path = artifact_dir / "evidence_preview.md"

    result = IngestionResult(
        paper=paper,
        chunks=chunks,
        artifact=IngestionArtifact(
            manifest_path=str(manifest_path),
            evidence_preview_path=str(evidence_preview_path),
        ),
    )
    _write_manifest(manifest_path, result)
    _write_evidence_preview(evidence_preview_path, result)
    return result


def _extract_document(path: Path):
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        raw_text = path.read_text(encoding="utf-8")
        metadata, section_blocks = _parse_text_paper(raw_text)
        return ParsedTextDocument(
            title=metadata.get("title") or path.stem,
            authors=_split_authors(metadata.get("authors", "")),
            abstract=metadata.get("abstract", ""),
            sections=section_blocks,
            parser="plain-text-fallback",
            raw_text=raw_text,
        )
    if suffix == ".pdf":
        return parse_pdf_document(path)
    raw_text = path.read_text(encoding="utf-8", errors="ignore")
    metadata, section_blocks = _parse_text_paper(raw_text)
    return ParsedTextDocument(
        title=metadata.get("title") or path.stem,
        authors=_split_authors(metadata.get("authors", "")),
        abstract=metadata.get("abstract", ""),
        sections=section_blocks,
        parser="text-fallback",
        raw_text=raw_text,
    )


def _paper_id(path: Path, text: str, *, namespace: str | None = None) -> str:
    digest = hashlib.sha256()
    if namespace:
        digest.update(namespace.encode("utf-8"))
        digest.update(b"\0")
    digest.update(path.name.encode("utf-8"))
    digest.update(b"\0")
    digest.update(text.encode("utf-8", errors="ignore"))
    return f"paper_{digest.hexdigest()[:16]}"


class ParsedTextDocument:
    def __init__(
        self,
        *,
        title: str,
        authors: list[str],
        abstract: str,
        sections: list[ParsedSection],
        parser: str,
        raw_text: str,
    ) -> None:
        self.title = title
        self.authors = authors
        self.abstract = abstract
        self.sections = sections
        self.parser = parser
        self.raw_text = raw_text


def _parse_text_paper(raw_text: str) -> tuple[dict[str, str], list[ParsedSection]]:
    metadata: dict[str, str] = {}
    sections: list[tuple[str, list[str]]] = []
    current_section: tuple[str, list[str]] | None = None

    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        key, sep, value = stripped.partition(":")
        normalized_key = key.lower()
        if sep and normalized_key in {"title", "authors", "abstract"}:
            metadata[normalized_key] = value.strip()
            continue

        heading_match = SECTION_HEADING_RE.match(stripped)
        if heading_match and len(stripped.split()) <= 8:
            current_section = (heading_match.group(1).strip(), [])
            sections.append(current_section)
            continue

        if current_section is None:
            current_section = ("Document", [])
            sections.append(current_section)
        current_section[1].append(stripped)

    return metadata, [
        ParsedSection(name=name, text="\n".join(lines).strip(), page=None)
        for name, lines in sections
        if "\n".join(lines).strip()
    ]


def _split_authors(authors: str) -> list[str]:
    if not authors:
        return []
    return [author.strip() for author in re.split(r";|,", authors) if author.strip()]


def _build_chunks(paper: CanonicalPaper, section_blocks: list[ParsedSection]) -> list[PaperChunk]:
    chunks: list[PaperChunk] = []
    for index, section in enumerate(section_blocks, start=1):
        chunks.append(
            PaperChunk(
                chunk_id=f"{paper.paper_id}_chunk_{index:04d}",
                text=section.text,
                source=EvidenceSource(
                    paper_id=paper.paper_id,
                    file_path=paper.file_path,
                    section=section.name,
                    page=section.page,
                ),
            )
        )
    return chunks


def _write_manifest(path: Path, result: IngestionResult) -> None:
    path.write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _write_evidence_preview(path: Path, result: IngestionResult) -> None:
    lines = [
        f"# {result.paper.title}",
        "",
        "This file previews citation evidence chunks extracted from the uploaded paper.",
        "",
    ]
    for chunk in result.chunks:
        lines.extend(
            [
                f"## {chunk.source.section}",
                "",
                f"- paper: `{result.paper.paper_id}`",
                f"- chunk: `{chunk.chunk_id}`",
                "",
                chunk.text,
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")
