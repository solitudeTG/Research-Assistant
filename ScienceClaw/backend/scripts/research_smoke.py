from __future__ import annotations

import argparse
import asyncio
import os
import sys
import tempfile
from pathlib import Path

import httpx

from backend.research_assistant.answering import answer_research_question
from backend.research_assistant.indexing import index_ingestion_result
from backend.research_assistant.ingestion import ingest_uploaded_paper
from backend.research_assistant.reports import generate_markdown_research_report


async def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Research Assistant uploaded-paper smoke loop.")
    parser.add_argument(
        "--database-url",
        default=os.environ.get(
            "RESEARCH_DATABASE_URL",
            "postgresql://research:research_dev_password@localhost:25432/research_assistant",
        ),
    )
    parser.add_argument("--grobid-url", default=os.environ.get("RESEARCH_GROBID_URL", "http://localhost:8070"))
    parser.add_argument(
        "--allow-grobid-unavailable",
        action="store_true",
        help="Run the same loop through the fallback parser when the local GROBID service is unavailable.",
    )
    parser.add_argument("--session-id", default="research-smoke-session")
    parser.add_argument("--user-id", default="research-smoke-user")
    parser.add_argument("--embedding-dimensions", type=int, default=1536)
    parser.add_argument("--embedding-model", default="local-hashing-v1")
    args = parser.parse_args()

    _require_module("asyncpg", "asyncpg is required for the PostgreSQL smoke test.")
    _require_module("fitz", "PyMuPDF is required to generate the smoke PDF and test fallback parsing.")
    await _check_postgres(args.database_url)
    grobid_available = await _check_grobid(args.grobid_url)
    if not grobid_available and not args.allow_grobid_unavailable:
        raise AssertionError("GROBID is unavailable; rerun only with --allow-grobid-unavailable for fallback smoke.")

    os.environ["RESEARCH_GROBID_URL"] = args.grobid_url if grobid_available else ""

    with tempfile.TemporaryDirectory(prefix="research-smoke-") as tmp:
        workspace = Path(tmp)
        pdf_path = workspace / "evidence-aware-research-assistant.pdf"
        _write_smoke_pdf(pdf_path)

        ingestion = ingest_uploaded_paper(
            file_path=pdf_path,
            session_id=args.session_id,
            user_id=args.user_id,
            workspace_dir=workspace,
        )
        if not ingestion.chunks:
            raise AssertionError("PDF ingestion produced no citation chunks")
        if not args.allow_grobid_unavailable and ingestion.paper.parser != "grobid-tei":
            raise AssertionError(
                f"GROBID smoke requires parser=grobid-tei, got parser={ingestion.paper.parser!r}"
            )

        indexing = await index_ingestion_result(
            database_url=args.database_url,
            result=ingestion,
            embedding_dimensions=args.embedding_dimensions,
            embedding_model=args.embedding_model,
        )
        answer = await answer_research_question(
            database_url=args.database_url,
            session_id=args.session_id,
            question="What does the paper say about evidence boundaries?",
            embedding_dimensions=args.embedding_dimensions,
            embedding_model=args.embedding_model,
            limit=5,
        )
        if answer.citation_count < 1:
            raise AssertionError("Research answer returned no citations")

        report = await generate_markdown_research_report(
            database_url=args.database_url,
            session_id=args.session_id,
            question="What does the paper say about evidence boundaries?",
            workspace_dir=workspace,
            embedding_dimensions=args.embedding_dimensions,
            embedding_model=args.embedding_model,
            limit=5,
        )
        if not Path(report.markdown_path).is_file() or not Path(report.evidence_map_path).is_file():
            raise AssertionError("Markdown report artifacts were not created")

        print("research smoke passed")
        print(f"paper_id={ingestion.paper.paper_id}")
        print(f"parser={ingestion.paper.parser}")
        print(f"grobid_available={grobid_available}")
        print(f"chunks={len(ingestion.chunks)}")
        print(f"evidence_records={indexing.evidence_record_count}")
        print(f"embeddings={indexing.embedding_count}")
        print(f"citations={answer.citation_count}")
        print(f"report={report.markdown_path}")
        return 0


def _require_module(name: str, message: str) -> None:
    try:
        __import__(name)
    except ImportError as exc:
        raise SystemExit(message) from exc


async def _check_postgres(database_url: str) -> None:
    import asyncpg

    connection = await asyncpg.connect(database_url)
    try:
        vector_available = await connection.fetchval(
            "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')"
        )
        if not vector_available:
            raise AssertionError("pgvector extension is not installed")
    finally:
        await connection.close()


async def _check_grobid(grobid_url: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=10, trust_env=False) as client:
            response = await client.get(f"{grobid_url.rstrip('/')}/api/isalive")
        response.raise_for_status()
        return True
    except Exception:
        return False


def _write_smoke_pdf(path: Path) -> None:
    import fitz

    document = fitz.open()
    page = document.new_page()
    text = "\n".join(
        [
            "Evidence-Aware Research Assistants",
            "Ada Lovelace",
            "",
            "Abstract",
            "This paper studies citation evidence boundaries for research assistants.",
            "",
            "1 Introduction",
            "Research assistants need paper-grounded citations.",
            "They must not cite memory, tool logs, or model reasoning as evidence.",
            "",
            "2 Method",
            "Hybrid retrieval combines PostgreSQL full-text search and vector search.",
        ]
    )
    page.insert_textbox(fitz.Rect(72, 72, 520, 760), text, fontsize=12, fontname="helv")
    document.save(path)
    document.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
