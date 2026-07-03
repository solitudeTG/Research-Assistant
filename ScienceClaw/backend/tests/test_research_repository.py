from pathlib import Path

import pytest

from backend.research_assistant.audit import EvidenceAudit, EvidenceAuditClaim
from backend.research_assistant.ingestion import ingest_uploaded_paper
from backend.research_assistant.models import (
    CanonicalPaper,
    EvidenceSource,
    IngestionArtifact,
    IngestionResult,
    PaperChunk,
)
from backend.research_assistant.subagents import default_subagent_definitions
from backend.research_assistant.storage import repository
from backend.research_assistant.storage.repository import (
    create_research_project,
    ensure_subagent_definitions,
    get_session_research_project,
    list_recent_subagent_runs,
    list_subagent_definitions,
    list_project_paper_assets,
    list_research_projects,
    persist_subagent_run,
    persist_chunk_embeddings,
    persist_database_evidence_source,
    persist_web_evidence_source,
    persist_ingestion_result,
    persist_report_evidence_map,
    upsert_session_research_project,
)


class RecordingTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class RecordingConnection:
    def __init__(self):
        self.executed = []
        self.executemany_calls = []
        self.fetchrow_calls = []
        self.fetchrow_result = None
        self.fetch_calls = []
        self.fetch_result = []

    def transaction(self):
        return RecordingTransaction()

    async def execute(self, sql, *args):
        self.executed.append((sql, args))

    async def executemany(self, sql, rows):
        self.executemany_calls.append((sql, rows))

    async def fetchrow(self, sql, *args):
        self.fetchrow_calls.append((sql, args))
        return self.fetchrow_result

    async def fetch(self, sql, *args):
        self.fetch_calls.append((sql, args))
        return self.fetch_result


@pytest.mark.asyncio
async def test_create_research_project_inserts_and_returns_project():
    connection = RecordingConnection()
    connection.fetchrow_result = {
        "project_id": "project-1",
        "user_id": "user-1",
        "name": "LEO Beamforming",
        "description": "Narrow beam papers",
        "created_at": None,
        "updated_at": None,
    }

    project = await create_research_project(
        connection,
        project_id="project-1",
        user_id="user-1",
        name="LEO Beamforming",
        description="Narrow beam papers",
    )

    sql, args = connection.fetchrow_calls[0]
    assert "insert into research_projects" in sql.lower()
    assert "returning" in sql.lower()
    assert args == ("project-1", "user-1", "LEO Beamforming", "Narrow beam papers")
    assert project.to_dict() == {
        "project_id": "project-1",
        "user_id": "user-1",
        "name": "LEO Beamforming",
        "description": "Narrow beam papers",
        "paper_count": 0,
        "chunk_count": 0,
        "evidence_record_count": 0,
        "created_at": None,
        "updated_at": None,
    }


@pytest.mark.asyncio
async def test_ensure_subagent_definitions_upserts_governed_defaults():
    connection = RecordingConnection()

    await ensure_subagent_definitions(
        connection,
        definitions=default_subagent_definitions(),
    )

    sql, rows = connection.executemany_calls[0]
    assert "insert into research_subagent_definitions" in sql.lower()
    assert "on conflict (name) do update" in sql.lower()
    assert len(rows) == 2
    first_row = rows[0]
    assert first_row[0] == "research_auditor"
    assert first_row[1] == "Auditor Agent"
    assert first_row[2] == "custom"
    assert first_row[3] == "registry"
    assert first_row[4] is True
    assert first_row[10] == "process_trace"
    assert first_row[11] is False
    assert first_row[12] is False
    assert first_row[16] is False


@pytest.mark.asyncio
async def test_list_subagent_definitions_returns_enabled_registry_rows():
    connection = RecordingConnection()
    connection.fetch_result = [
        {
            "name": "paper_reader_worker",
            "display_name": "Reader Worker",
            "agent_type": "custom",
            "source": "registry",
            "editable": True,
            "description": "Read scoped papers.",
            "system_prompt": "You are a scoped Reader Worker.",
            "skill_refs": '["research-paper-reading"]',
            "allowed_tools": '["read_research_evidence"]',
            "input_boundaries": '{"requires":["material_package"]}',
            "output_boundary": "context_only",
            "can_answer_user": False,
            "can_write_artifacts": False,
            "enabled": True,
            "version": 1,
            "validation_status": "valid",
            "citation_evidence": False,
            "metadata": '{"ui_order":2}',
        }
    ]

    definitions = await list_subagent_definitions(connection, enabled_only=True)

    sql, args = connection.fetch_calls[0]
    assert "from research_subagent_definitions" in sql.lower()
    assert "where enabled = true" in sql.lower()
    assert args == ()
    assert len(definitions) == 1
    assert definitions[0].name == "paper_reader_worker"
    assert definitions[0].agent_type == "custom"
    assert definitions[0].source == "registry"
    assert definitions[0].editable is True
    assert definitions[0].allowed_tools == ["read_research_evidence"]
    assert definitions[0].input_boundaries == {"requires": ["material_package"]}
    assert definitions[0].metadata == {"ui_order": 2}


@pytest.mark.asyncio
async def test_persist_subagent_run_records_context_only_boundary():
    connection = RecordingConnection()

    await persist_subagent_run(
        connection,
        task_id="task-1",
        parent_workflow_id="workflow-1",
        agent_name="paper_reader_worker",
        agent_role="reader",
        status="completed",
        input_boundary={"scope": "selected_evidence"},
        output_boundary="context_only",
        evidence_refs=[{"evidence_id": 9, "source_type": "paper"}],
        outputs={"notes": ["finding"]},
    )

    sql, args = connection.executed[0]
    assert "insert into research_subagent_runs" in sql.lower()
    assert "on conflict (task_id) do update" in sql.lower()
    assert args[0] == "task-1"
    assert args[1] == "workflow-1"
    assert args[2] == "paper_reader_worker"
    assert args[6] == "context_only"
    assert args[7] is False


@pytest.mark.asyncio
async def test_list_recent_subagent_runs_returns_preview_rows():
    connection = RecordingConnection()
    connection.fetch_result = [
        {
            "task_id": "task-1",
            "parent_workflow_id": "workflow-1",
            "agent_name": "paper_reader_worker",
            "agent_role": "reader",
            "status": "completed",
            "input_boundary": '{"scope":"selected"}',
            "output_boundary": "context_only",
            "citation_evidence": False,
            "evidence_refs": '[{"evidence_id":9,"source_type":"paper"}]',
            "outputs": '{"status":"completed"}',
            "warnings": "[]",
            "errors": "[]",
            "started_at": "2026-07-03T10:00:00Z",
            "completed_at": "2026-07-03T10:00:05Z",
        }
    ]

    runs = await list_recent_subagent_runs(connection, agent_name="paper_reader_worker", limit=3)

    sql, args = connection.fetch_calls[0]
    assert "from research_subagent_runs" in sql.lower()
    assert "where agent_name = $1" in sql.lower()
    assert "limit $2" in sql.lower()
    assert args == ("paper_reader_worker", 3)
    assert runs == [
        {
            "task_id": "task-1",
            "parent_workflow_id": "workflow-1",
            "agent_name": "paper_reader_worker",
            "agent_role": "reader",
            "status": "completed",
            "input_boundary": {"scope": "selected"},
            "output_boundary": "context_only",
            "citation_evidence": False,
            "evidence_refs": [{"evidence_id": 9, "source_type": "paper"}],
            "outputs": {"status": "completed"},
            "warnings": [],
            "errors": [],
            "started_at": "2026-07-03T10:00:00Z",
            "completed_at": "2026-07-03T10:00:05Z",
        }
    ]


@pytest.mark.asyncio
async def test_list_research_projects_reads_user_project_summaries():
    connection = RecordingConnection()
    connection.fetch_result = [
        {
            "project_id": "project-1",
            "user_id": "user-1",
            "name": "LEO Beamforming",
            "description": "Narrow beam papers",
            "paper_count": 2,
            "chunk_count": 8,
            "evidence_record_count": 8,
            "created_at": None,
            "updated_at": None,
        }
    ]

    projects = await list_research_projects(connection, user_id="user-1")

    sql, args = connection.fetch_calls[0]
    assert "from research_projects" in sql.lower()
    assert "left join research_papers" in sql.lower()
    assert "where rp.user_id = $1" in sql.lower()
    assert args == ("user-1",)
    assert len(projects) == 1
    assert projects[0].project_id == "project-1"
    assert projects[0].paper_count == 2
    assert projects[0].chunk_count == 8
    assert projects[0].evidence_record_count == 8


@pytest.mark.asyncio
async def test_list_project_paper_assets_reads_only_selected_project():
    connection = RecordingConnection()
    connection.fetch_result = [
        {
            "paper_id": "paper-1",
            "project_id": "project-1",
            "session_id": "session-1",
            "user_id": "user-1",
            "title": "Space-Time Beamforming",
            "authors": '["Ada Lovelace"]',
            "abstract": "Narrow beams for LEO.",
            "source_path": "/tmp/paper.pdf",
            "parser": "grobid-tei",
            "source_identity": '{"file_path":"/tmp/paper.pdf"}',
            "chunk_count": 4,
            "evidence_record_count": 4,
            "created_at": None,
            "updated_at": None,
        }
    ]

    papers = await list_project_paper_assets(
        connection,
        project_id="project-1",
        user_id="user-1",
    )

    sql, args = connection.fetch_calls[0]
    assert "from research_papers" in sql.lower()
    assert "where p.project_id = $1" in sql.lower()
    assert "and p.user_id = $2" in sql.lower()
    assert args == ("project-1", "user-1")
    assert len(papers) == 1
    assert papers[0].to_dict()["title"] == "Space-Time Beamforming"
    assert papers[0].to_dict()["status"] == "indexed"
    assert papers[0].to_dict()["citation_ready"] is True


@pytest.mark.asyncio
async def test_upsert_session_research_project_persists_binding():
    connection = RecordingConnection()
    connection.fetchrow_result = {
        "session_id": "session-1",
        "project_id": "project-1",
        "user_id": "user-1",
        "name": "LEO Beamforming",
        "description": "Narrow beam papers",
        "paper_count": 2,
        "chunk_count": 8,
        "evidence_record_count": 8,
        "created_at": None,
        "updated_at": None,
    }

    project = await upsert_session_research_project(
        connection,
        session_id="session-1",
        project_id="project-1",
        user_id="user-1",
    )

    sql, args = connection.fetchrow_calls[0]
    assert "insert into research_session_projects" in sql.lower()
    assert "on conflict (session_id)" in sql.lower()
    assert "join research_projects" in sql.lower()
    assert "left join research_papers" in sql.lower()
    assert "count(distinct p.paper_id)" in sql.lower()
    assert args == ("session-1", "project-1", "user-1")
    assert project is not None
    assert project.project_id == "project-1"
    assert project.paper_count == 2
    assert project.evidence_record_count == 8


@pytest.mark.asyncio
async def test_get_session_research_project_reads_binding_with_project_summary_counts():
    connection = RecordingConnection()
    connection.fetchrow_result = {
        "session_id": "session-1",
        "project_id": "project-1",
        "user_id": "user-1",
        "name": "LEO Beamforming",
        "description": "Narrow beam papers",
        "paper_count": 2,
        "chunk_count": 8,
        "evidence_record_count": 8,
        "created_at": None,
        "updated_at": None,
    }

    project = await get_session_research_project(
        connection,
        session_id="session-1",
        user_id="user-1",
    )

    sql, args = connection.fetchrow_calls[0]
    assert "from research_session_projects" in sql.lower()
    assert "join research_projects" in sql.lower()
    assert "left join research_papers" in sql.lower()
    assert "count(distinct p.paper_id)" in sql.lower()
    assert "rsp.session_id = $1" in sql.lower()
    assert "rp.user_id = $2" in sql.lower()
    assert args == ("session-1", "user-1")
    assert project is not None
    assert project.project_id == "project-1"
    assert project.paper_count == 2
    assert project.chunk_count == 8
    assert project.evidence_record_count == 8


@pytest.mark.asyncio
async def test_persist_ingestion_result_writes_paper_chunks_and_evidence(tmp_path: Path):
    paper_path = tmp_path / "sample.md"
    paper_path.write_text(
        "\n".join(
            [
                "Title: Hybrid Retrieval for Papers",
                "Authors: Ada Lovelace",
                "Abstract: Hybrid retrieval keeps lexical and semantic evidence.",
                "",
                "1 Introduction",
                "PostgreSQL full-text search helps citation recall.",
                "",
                "2 Method",
                "pgvector stores semantic evidence candidates.",
            ]
        ),
        encoding="utf-8",
    )
    ingestion = ingest_uploaded_paper(
        file_path=paper_path,
        session_id="session-1",
        user_id="user-1",
        workspace_dir=tmp_path,
    )
    connection = RecordingConnection()

    summary = await persist_ingestion_result(connection, ingestion)

    assert summary.paper_id == ingestion.paper.paper_id
    assert summary.chunk_count == len(ingestion.chunks)
    assert summary.evidence_record_count == len(ingestion.chunks)
    assert any("insert into research_papers" in sql.lower() for sql, _ in connection.executed)
    assert any("insert into research_chunks" in sql.lower() for sql, _ in connection.executemany_calls)
    assert any("insert into research_evidence_records" in sql.lower() for sql, _ in connection.executemany_calls)
    evidence_sql = next(
        sql.lower()
        for sql, _ in connection.executemany_calls
        if "insert into research_evidence_records" in sql.lower()
    )
    assert "on conflict" in evidence_sql


@pytest.mark.asyncio
async def test_persist_ingestion_result_can_attach_paper_to_project(tmp_path: Path):
    paper_path = tmp_path / "sample.md"
    paper_path.write_text(
        "\n".join(
            [
                "Title: Project Scoped Paper",
                "Authors: Ada Lovelace",
                "Abstract: Project assets need boundaries.",
                "",
                "1 Method",
                "Research Project isolates paper evidence.",
            ]
        ),
        encoding="utf-8",
    )
    ingestion = ingest_uploaded_paper(
        file_path=paper_path,
        session_id="library-project-1",
        user_id="user-1",
        workspace_dir=tmp_path,
    )
    connection = RecordingConnection()

    await persist_ingestion_result(connection, ingestion, project_id="project-1")

    paper_sql, paper_args = connection.executed[0]
    assert "project_id" in paper_sql.lower()
    assert paper_args[0:4] == (
        ingestion.paper.paper_id,
        "project-1",
        "library-project-1",
        "user-1",
    )


@pytest.mark.asyncio
async def test_persist_ingestion_result_removes_nul_bytes_before_database_write():
    ingestion = IngestionResult(
        paper=CanonicalPaper(
            paper_id="paper-nul",
            title="Title\x00With NUL",
            authors=["Ada\x00Lovelace"],
            abstract="Abstract\x00text",
            file_path="/tmp/paper.pdf",
            session_id="session-1",
            user_id="user-1",
            parser="pdf-text",
        ),
        chunks=[
            PaperChunk(
                chunk_id="chunk-nul",
                text="Chunk\x00text",
                source=EvidenceSource(
                    paper_id="paper-nul",
                    file_path="/tmp/paper.pdf",
                    section="Result\x00section",
                    page=1,
                ),
            )
        ],
        artifact=IngestionArtifact(
            manifest_path="/tmp/manifest.json",
            evidence_preview_path="/tmp/evidence.json",
        ),
    )
    connection = RecordingConnection()

    await persist_ingestion_result(connection, ingestion, project_id="project-1")

    _, paper_args = connection.executed[0]
    assert "\x00" not in paper_args[4]
    assert "\x00" not in paper_args[5]
    assert "\x00" not in paper_args[6]

    _, chunk_rows = connection.executemany_calls[0]
    assert "\x00" not in chunk_rows[0][2]
    assert "\x00" not in chunk_rows[0][6]
    assert "\x00" not in chunk_rows[0][7]

    _, evidence_rows = connection.executemany_calls[1]
    assert "\x00" not in evidence_rows[0][1]
    assert "\x00" not in evidence_rows[0][2]
    assert "\x00" not in evidence_rows[0][5]


@pytest.mark.asyncio
async def test_persist_ingestion_result_bounds_evidence_quote_without_truncating_chunk_content():
    long_text = "A" * 6000
    ingestion = IngestionResult(
        paper=CanonicalPaper(
            paper_id="paper-long",
            title="Long Evidence",
            authors=[],
            abstract="",
            file_path="/tmp/paper.pdf",
            session_id="session-1",
            user_id="user-1",
            parser="pdf-text",
        ),
        chunks=[
            PaperChunk(
                chunk_id="chunk-long",
                text=long_text,
                source=EvidenceSource(
                    paper_id="paper-long",
                    file_path="/tmp/paper.pdf",
                    section="Results",
                    page=1,
                ),
            )
        ],
        artifact=IngestionArtifact(
            manifest_path="/tmp/manifest.json",
            evidence_preview_path="/tmp/evidence.json",
        ),
    )
    connection = RecordingConnection()

    await persist_ingestion_result(connection, ingestion)

    _, chunk_rows = connection.executemany_calls[0]
    assert chunk_rows[0][6] == long_text

    _, evidence_rows = connection.executemany_calls[1]
    quote = evidence_rows[0][1]
    assert len(quote) < len(long_text)
    assert len(quote.encode("utf-8")) <= 1200
    assert quote.endswith("...")


@pytest.mark.asyncio
async def test_persist_web_evidence_source_writes_source_chunks_and_web_evidence():
    connection = RecordingConnection()

    summary = await persist_web_evidence_source(
        connection,
        session_id="session-1",
        user_id="user-1",
        source_id="web-source-1",
        url="https://example.org/evidence-boundaries",
        title="Evidence Boundaries on the Web",
        retrieved_at="2026-06-21T00:00:00Z",
        chunks=[
            {
                "chunk_id": "web-source-1:chunk-1",
                "section": "Main",
                "content": "Web evidence must preserve source identity.",
                "quote": "Web evidence must preserve source identity.",
            }
        ],
    )

    assert summary.paper_id == "web-source-1"
    assert summary.chunk_count == 1
    assert summary.evidence_record_count == 1
    assert any("insert into research_papers" in sql.lower() for sql, _ in connection.executed)
    paper_sql, paper_args = connection.executed[0]
    assert "parser" in paper_sql.lower()
    assert paper_args[0:8] == (
        "web-source-1",
        "session-1",
        "user-1",
        "Evidence Boundaries on the Web",
        "[]",
        "",
        "https://example.org/evidence-boundaries",
        "web-source",
    )
    assert '"source_type":"web"' in paper_args[8]
    chunk_sql, chunk_rows = connection.executemany_calls[0]
    assert "insert into research_chunks" in chunk_sql.lower()
    assert chunk_rows[0][0:7] == (
        "web-source-1:chunk-1",
        "web-source-1",
        "Main",
        None,
        None,
        1,
        "Web evidence must preserve source identity.",
    )
    assert '"url":"https://example.org/evidence-boundaries"' in chunk_rows[0][7]
    evidence_sql, evidence_rows = connection.executemany_calls[1]
    assert "insert into research_evidence_records" in evidence_sql.lower()
    assert "'web'" in evidence_sql.lower()
    assert evidence_rows[0][0:5] == (
        "web-source-1:chunk-1",
        "Web evidence must preserve source identity.",
        "Main",
        None,
        None,
    )


@pytest.mark.asyncio
async def test_persist_database_evidence_source_writes_source_chunks_and_database_evidence():
    connection = RecordingConnection()

    summary = await persist_database_evidence_source(
        connection,
        session_id="session-1",
        user_id="user-1",
        source_id="database-source-1",
        database_name="OpenAlex",
        query="topic:evidence-boundaries",
        title="OpenAlex Evidence Boundary Results",
        retrieved_at="2026-06-21T00:00:00Z",
        chunks=[
            {
                "chunk_id": "database-source-1:chunk-1",
                "section": "Result row",
                "content": "Database evidence must preserve query identity.",
                "quote": "Database evidence must preserve query identity.",
            }
        ],
    )

    assert summary.paper_id == "database-source-1"
    assert summary.chunk_count == 1
    assert summary.evidence_record_count == 1
    paper_sql, paper_args = connection.executed[0]
    assert "insert into research_papers" in paper_sql.lower()
    assert paper_args[0:8] == (
        "database-source-1",
        "session-1",
        "user-1",
        "OpenAlex Evidence Boundary Results",
        "[]",
        "",
        "database:OpenAlex",
        "database-source",
    )
    assert '"source_type":"database"' in paper_args[8]
    assert '"database_name":"OpenAlex"' in paper_args[8]
    assert '"query":"topic:evidence-boundaries"' in paper_args[8]
    chunk_sql, chunk_rows = connection.executemany_calls[0]
    assert "insert into research_chunks" in chunk_sql.lower()
    assert chunk_rows[0][0:7] == (
        "database-source-1:chunk-1",
        "database-source-1",
        "Result row",
        None,
        None,
        1,
        "Database evidence must preserve query identity.",
    )
    evidence_sql, evidence_rows = connection.executemany_calls[1]
    assert "insert into research_evidence_records" in evidence_sql.lower()
    assert "'database'" in evidence_sql.lower()
    assert evidence_rows[0][0:5] == (
        "database-source-1:chunk-1",
        "Database evidence must preserve query identity.",
        "Result row",
        None,
        None,
    )


@pytest.mark.asyncio
async def test_persist_chunk_embeddings_writes_pgvector_rows():
    connection = RecordingConnection()

    await persist_chunk_embeddings(
        connection,
        embeddings=[
            ("chunk-1", [0.1, 0.2, 0.3]),
            ("chunk-2", [0.4, 0.5, 0.6]),
        ],
        embedding_model="test-embedding",
    )

    sql, rows = connection.executemany_calls[0]
    assert "insert into research_embeddings" in sql.lower()
    assert "on conflict" in sql.lower()
    assert rows == [
        ("chunk-1", "test-embedding", "[0.1,0.2,0.3]"),
        ("chunk-2", "test-embedding", "[0.4,0.5,0.6]"),
    ]


@pytest.mark.asyncio
async def test_persist_report_evidence_map_upserts_rows():
    connection = RecordingConnection()

    await persist_report_evidence_map(
        connection,
        report_id="report-1",
        evidence_rows=[(3, "evidence-1", "Claim text")],
    )

    sql, rows = connection.executemany_calls[0]
    assert "insert into research_report_evidence_map" in sql.lower()
    assert "on conflict" in sql.lower()
    assert rows == [("report-1", 3, "evidence-1", "Claim text")]


@pytest.mark.asyncio
async def test_persist_audit_result_upserts_claim_boundaries():
    connection = RecordingConnection()
    audit = EvidenceAudit(
        status="approved",
        claims=[
            EvidenceAuditClaim(
                claim_text="Hybrid retrieval improves recall.",
                status="approved",
                evidence_ids=[17],
                notes=[],
            )
        ],
        boundaries={
            "citation_evidence": ["paper"],
            "context_only": ["memory", "model_reasoning", "process_trace", "tool_logs"],
        },
    )

    await repository.persist_audit_result(
        connection,
        audit_id="audit-1",
        session_id="session-1",
        subject_type="report",
        subject_id="report-1",
        audit=audit,
    )

    sql, args = connection.executed[0]
    assert "insert into research_audit_results" in sql.lower()
    assert "on conflict (subject_type, subject_id)" in sql.lower()
    assert args[0:9] == (
        "audit-1",
        "session-1",
        "report",
        "report-1",
        "approved",
        1,
        1,
        0,
        0,
    )
    assert '"citation_evidence":["paper"]' in args[9]
    assert '"claim_text":"Hybrid retrieval improves recall."' in args[10]


@pytest.mark.asyncio
async def test_get_audit_result_reads_session_scoped_subject():
    connection = RecordingConnection()
    connection.fetchrow_result = {
        "audit_id": "report-1:audit",
        "session_id": "session-1",
        "subject_type": "report",
        "subject_id": "report-1",
        "status": "approved",
        "claim_count": 1,
        "approved_claim_count": 1,
        "unsupported_claim_count": 0,
        "invalid_source_count": 0,
        "boundaries": '{"citation_evidence":["paper"],"context_only":["memory"]}',
        "claims": '[{"claim_text":"Claim","status":"approved","evidence_ids":[17],"notes":[]}]',
    }

    result = await repository.get_audit_result(
        connection,
        session_id="session-1",
        subject_type="report",
        subject_id="report-1",
    )

    sql, args = connection.fetchrow_calls[0]
    assert "from research_audit_results" in sql.lower()
    assert "session_id = $1" in sql.lower()
    assert "subject_type = $2" in sql.lower()
    assert "subject_id = $3" in sql.lower()
    assert args == ("session-1", "report", "report-1")
    assert result is not None
    assert result.audit_id == "report-1:audit"
    assert result.claims[0]["evidence_ids"] == [17]
    assert result.to_dict()["boundaries"]["citation_evidence"] == ["paper"]


@pytest.mark.asyncio
async def test_get_audit_result_returns_none_when_missing():
    connection = RecordingConnection()

    result = await repository.get_audit_result(
        connection,
        session_id="session-1",
        subject_type="answer",
        subject_id="missing-answer",
    )

    assert result is None


@pytest.mark.asyncio
async def test_get_evidence_record_reads_session_scoped_paper_evidence():
    connection = RecordingConnection()
    connection.fetchrow_result = {
        "evidence_id": 17,
        "evidence_type": "paper",
        "chunk_id": "chunk-17",
        "paper_id": "paper-1",
        "title": "Evidence Boundaries",
        "section": "Method",
        "page_start": 2,
        "page_end": 3,
        "quote": "Citation evidence is bounded.",
        "chunk_content": "Citation evidence is bounded. Memory is context-only.",
        "source_identity": '{"paper_id":"paper-1","file_path":"paper.pdf","section":"Method","page":2}',
    }

    result = await repository.get_evidence_record(
        connection,
        session_id="session-1",
        evidence_id=17,
    )

    sql, args = connection.fetchrow_calls[0]
    assert "from research_evidence_records" in sql.lower()
    assert "join research_papers" in sql.lower()
    assert "p.session_id = $1" in sql.lower()
    assert "er.evidence_id = $2" in sql.lower()
    assert args == ("session-1", 17)
    assert result is not None
    assert result.evidence_id == 17
    assert result.evidence_type == "paper"
    assert result.paper_id == "paper-1"
    assert result.source_identity["file_path"] == "paper.pdf"
    assert result.to_dict()["chunk_content"].startswith("Citation evidence")


@pytest.mark.asyncio
async def test_get_evidence_record_returns_none_when_missing():
    connection = RecordingConnection()

    result = await repository.get_evidence_record(
        connection,
        session_id="session-1",
        evidence_id=999,
    )

    assert result is None


@pytest.mark.asyncio
async def test_persist_memory_entry_forces_context_only_memory_boundary():
    connection = RecordingConnection()

    await repository.persist_memory_entry(
        connection,
        memory_id="mem-1",
        session_id="session-1",
        user_id="user-1",
        layer="L2",
        title="Confirmed retrieval preference",
        content="Prefer hybrid retrieval for scholarly terminology.",
        source_subject_type="answer",
        source_subject_id="answer-1",
    )

    sql, args = connection.executed[0]
    assert "insert into research_memory_entries" in sql.lower()
    assert "source_type" in sql.lower()
    assert "context_only" in sql.lower()
    assert "on conflict (memory_id)" in sql.lower()
    assert args == (
        "mem-1",
        "session-1",
        "user-1",
        "l2",
        "Confirmed retrieval preference",
        "Prefer hybrid retrieval for scholarly terminology.",
        "answer",
        "answer-1",
    )


@pytest.mark.asyncio
async def test_list_memory_entries_returns_context_only_memory_contexts():
    connection = RecordingConnection()
    connection.fetch_result = [
        {
            "memory_id": "mem-1",
            "session_id": "session-1",
            "user_id": "user-1",
            "layer": "l2",
            "title": "Confirmed retrieval preference",
            "content": "Prefer hybrid retrieval for scholarly terminology.",
            "source_type": "memory",
            "context_only": True,
            "source_subject_type": "answer",
            "source_subject_id": "answer-1",
            "created_at": None,
        }
    ]

    memories = await repository.list_memory_entries(
        connection,
        session_id="session-1",
        layer="L2",
        limit=5,
    )

    sql, args = connection.fetch_calls[0]
    assert "from research_memory_entries" in sql.lower()
    assert "session_id = $1" in sql.lower()
    assert "user_id = $2" in sql.lower()
    assert "layer in ('l2', 'l3')" in sql.lower()
    assert "layer = $3" in sql.lower()
    assert "context_only = true" in sql.lower()
    assert args == ("session-1", None, "l2", 5)
    assert len(memories) == 1
    assert memories[0].source_type == "memory"
    assert memories[0].context_only is True
    assert memories[0].to_context_dict() == {
        "memory_id": "mem-1",
        "layer": "l2",
        "title": "Confirmed retrieval preference",
        "content": "Prefer hybrid retrieval for scholarly terminology.",
        "source_type": "memory",
        "context_only": True,
        "source_subject_type": "answer",
        "source_subject_id": "answer-1",
    }


@pytest.mark.asyncio
async def test_list_memory_entries_can_include_same_user_l2_l3_across_sessions():
    connection = RecordingConnection()
    connection.fetch_result = [
        {
            "memory_id": "mem-cross-session",
            "session_id": "session-2",
            "user_id": "user-1",
            "layer": "l2",
            "title": "Confirmed retrieval preference",
            "content": "Prefer hybrid retrieval for scholarly terminology.",
            "source_type": "memory",
            "context_only": True,
            "source_subject_type": "answer",
            "source_subject_id": "answer-1",
            "created_at": None,
        }
    ]

    memories = await repository.list_memory_entries(
        connection,
        session_id="session-1",
        user_id="user-1",
        layer="L2",
        limit=10,
    )

    sql, args = connection.fetch_calls[0]
    assert "user_id = $2" in sql.lower()
    assert "layer in ('l2', 'l3')" in sql.lower()
    assert args == ("session-1", "user-1", "l2", 10)
    assert memories[0].memory_id == "mem-cross-session"
    assert memories[0].session_id == "session-2"
    assert memories[0].user_id == "user-1"


@pytest.mark.asyncio
async def test_delete_memory_entry_deletes_session_scoped_context_only_memory():
    connection = RecordingConnection()

    async def execute(sql, *args):
        connection.executed.append((sql, args))
        return "DELETE 1"

    connection.execute = execute

    deleted = await repository.delete_memory_entry(
        connection,
        session_id="session-1",
        memory_id="mem-1",
    )

    sql, args = connection.executed[0]
    assert deleted is True
    assert "delete from research_memory_entries" in sql.lower()
    assert "session_id = $1" in sql.lower()
    assert "memory_id = $2" in sql.lower()
    assert "source_type = 'memory'" in sql.lower()
    assert "context_only = true" in sql.lower()
    assert args == ("session-1", "mem-1")


@pytest.mark.asyncio
async def test_delete_memory_entry_returns_false_when_no_row_deleted():
    connection = RecordingConnection()

    async def execute(sql, *args):
        connection.executed.append((sql, args))
        return "DELETE 0"

    connection.execute = execute

    deleted = await repository.delete_memory_entry(
        connection,
        session_id="session-1",
        memory_id="missing-memory",
    )

    assert deleted is False
