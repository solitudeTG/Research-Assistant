from pathlib import Path


def test_research_store_schema_defines_pgvector_and_evidence_tables():
    schema = (
        Path(__file__).resolve().parents[1]
        / "research_assistant"
        / "storage"
        / "schema.sql"
    )

    assert schema.is_file()
    sql = schema.read_text(encoding="utf-8").lower()

    assert "create extension if not exists vector" in sql
    for table_name in [
        "research_papers",
        "research_chunks",
        "research_embeddings",
        "research_evidence_records",
        "research_citations",
        "research_report_evidence_map",
    ]:
        assert f"create table if not exists {table_name}" in sql

    assert "tsvector" in sql
    assert "vector(" in sql
