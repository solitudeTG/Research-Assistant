from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class CanonicalPaper:
    paper_id: str
    title: str
    authors: list[str]
    abstract: str
    file_path: str
    session_id: str
    user_id: str
    parser: str


@dataclass(frozen=True)
class EvidenceSource:
    paper_id: str
    file_path: str
    section: str
    page: int | None = None


@dataclass(frozen=True)
class PaperChunk:
    chunk_id: str
    text: str
    source: EvidenceSource


@dataclass(frozen=True)
class IngestionArtifact:
    manifest_path: str
    evidence_preview_path: str


@dataclass(frozen=True)
class IngestionResult:
    paper: CanonicalPaper
    chunks: list[PaperChunk]
    artifact: IngestionArtifact

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

