from __future__ import annotations

import json
from dataclasses import replace

import pytest

from backend.research_assistant.subagents import (
    SubagentDefinition,
    audit_evidence_claims,
    build_deepagents_subagent_configs,
    build_subagent_lifecycle_step_event,
    build_subagent_result_envelope,
    default_subagent_definitions,
    read_research_evidence,
    registry_subagent_definitions,
    system_builtin_subagent_definitions,
    validate_subagent_definition,
)


def _definitions_by_name() -> dict[str, SubagentDefinition]:
    return {definition.name: definition for definition in default_subagent_definitions()}


def test_default_research_subagents_are_governed_workers_not_user_agents():
    definitions = _definitions_by_name()

    assert set(definitions) == {"research_auditor", "paper_reader_worker"}

    auditor = definitions["research_auditor"]
    assert auditor.agent_type == "custom"
    assert auditor.source == "registry"
    assert auditor.editable is True
    assert auditor.display_name == "Auditor Agent"
    assert auditor.output_boundary == "process_trace"
    assert auditor.allowed_tools == ["audit_evidence_claims"]
    assert auditor.can_answer_user is False
    assert auditor.can_write_artifacts is False
    assert auditor.citation_evidence is False
    assert "deterministic evidence boundary" in auditor.system_prompt
    assert "cannot upgrade" in auditor.system_prompt

    reader = definitions["paper_reader_worker"]
    assert reader.agent_type == "custom"
    assert reader.source == "registry"
    assert reader.editable is True
    assert reader.display_name == "Reader Worker"
    assert reader.output_boundary == "context_only"
    assert reader.allowed_tools == ["read_research_evidence"]
    assert reader.can_answer_user is False
    assert reader.can_write_artifacts is False
    assert reader.citation_evidence is False
    assert "multi-paper" in reader.description
    assert "follow-up" in reader.description


def test_registry_read_model_includes_read_only_system_builtin_agent():
    definitions = {definition.name: definition for definition in registry_subagent_definitions()}

    assert set(definitions) == {"general-purpose", "research_auditor", "paper_reader_worker"}
    builtin = definitions["general-purpose"]
    assert builtin.agent_type == "system_builtin"
    assert builtin.source == "deepagents_builtin"
    assert builtin.editable is False
    assert builtin.enabled is True
    assert builtin.output_boundary == "process_trace"
    assert builtin.citation_evidence is False
    assert builtin.validation_status == "system_managed"
    assert builtin.allowed_tools == []
    assert builtin.can_answer_user is False


def test_system_builtin_agent_validation_rejects_editable_or_citation_evidence():
    builtin = system_builtin_subagent_definitions()[0]

    validate_subagent_definition(builtin)

    with pytest.raises(ValueError, match="system_builtin"):
        validate_subagent_definition(replace(builtin, editable=True))

    with pytest.raises(ValueError, match="citation_evidence"):
        validate_subagent_definition(replace(builtin, citation_evidence=True))


def test_subagent_definition_validation_rejects_boundary_drift():
    auditor = _definitions_by_name()["research_auditor"]

    with pytest.raises(ValueError, match="can_answer_user"):
        validate_subagent_definition(replace(auditor, can_answer_user=True))

    with pytest.raises(ValueError, match="allowed_tools"):
        validate_subagent_definition(replace(auditor, allowed_tools=[]))

    with pytest.raises(ValueError, match="output_boundary"):
        validate_subagent_definition(replace(auditor, output_boundary="citation_evidence"))

    with pytest.raises(ValueError, match="citation_evidence"):
        validate_subagent_definition(replace(auditor, citation_evidence=True))


def test_build_deepagents_subagent_configs_preserves_registry_intent():
    audit_tool = object()
    reader_tool = object()

    configs = build_deepagents_subagent_configs(
        definitions=default_subagent_definitions(),
        available_tools={
            "audit_evidence_claims": audit_tool,
            "read_research_evidence": reader_tool,
        },
    )

    by_name = {config["name"]: config for config in configs}
    assert set(by_name) == {"research_auditor", "paper_reader_worker"}
    assert by_name["research_auditor"]["description"].startswith("Audit")
    assert by_name["research_auditor"]["tools"] == [audit_tool]
    assert by_name["paper_reader_worker"]["tools"] == [reader_tool]
    assert "You are the Research Auditor Agent" in by_name["research_auditor"]["system_prompt"]
    assert "You are a scoped Reader Worker" in by_name["paper_reader_worker"]["system_prompt"]


def test_build_deepagents_subagent_configs_rejects_missing_tools():
    with pytest.raises(ValueError, match="read_research_evidence"):
        build_deepagents_subagent_configs(
            definitions=default_subagent_definitions(),
            available_tools={"audit_evidence_claims": object()},
        )


def test_subagent_lifecycle_event_is_a_real_step_with_boundary_metadata():
    event = build_subagent_lifecycle_step_event(
        workflow_id="wf-1",
        task_id="task-1",
        agent_name="paper_reader_worker",
        agent_role="reader",
        status="running",
        phase="started",
        description="Reader Worker started for 3 papers",
        output_boundary="context_only",
        evidence_refs=[{"evidence_id": 12, "source_type": "paper"}],
    )

    assert event["event"] == "step"
    data = event["data"]
    assert data["id"] == "subagent-task-1"
    assert data["status"] == "running"
    assert data["description"] == "Reader Worker started for 3 papers"
    assert data["metadata"]["subagent_lifecycle"] == {
        "workflow_id": "wf-1",
        "task_id": "task-1",
        "parent_agent": "DeepAgent",
        "agent_name": "paper_reader_worker",
        "agent_role": "reader",
        "agent_type": "custom",
        "source": "registry",
        "phase": "started",
        "status": "running",
        "output_boundary": "context_only",
        "citation_evidence": False,
        "evidence_refs": [{"evidence_id": 12, "source_type": "paper"}],
    }


def test_subagent_result_envelope_keeps_stable_top_level_fields_minimal():
    envelope = build_subagent_result_envelope(
        status="completed",
        agent="general-purpose",
        boundary="process_trace",
        content="runtime note",
        metadata={"extension": {"future": True}},
    )

    assert set(envelope) == {"status", "agent", "boundary", "citation_evidence", "content", "metadata"}
    assert envelope == {
        "status": "completed",
        "agent": "general-purpose",
        "boundary": "process_trace",
        "citation_evidence": False,
        "content": "runtime note",
        "metadata": {"extension": {"future": True}},
    }


def test_auditor_tool_returns_minimal_process_trace_envelope():
    result = audit_evidence_claims.invoke(
        {
            "answer_content": "Unsupported claim.",
            "citations_json": "[]",
        }
    )

    assert set(result) == {"status", "agent", "boundary", "citation_evidence", "content", "metadata"}
    assert result["status"] == "completed"
    assert result["agent"] == "research_auditor"
    assert result["boundary"] == "process_trace"
    assert result["citation_evidence"] is False
    assert result["content"]["audit"]["status"] == "unsupported"
    assert result["metadata"]["audit_status"] == "unsupported"
    assert result["metadata"]["deterministic_boundary"] is True


def test_reader_tool_returns_minimal_context_only_envelope_with_metadata_refs():
    result = read_research_evidence.invoke(
        {
            "material_package_json": json.dumps(
                {
                    "records": [
                        {
                            "evidence_id": 17,
                            "source_type": "paper",
                            "title": "Trace Honesty",
                            "quote": "Reader notes are context only.",
                        }
                    ]
                }
            )
        }
    )

    assert set(result) == {"status", "agent", "boundary", "citation_evidence", "content", "metadata"}
    assert result["status"] == "completed"
    assert result["agent"] == "paper_reader_worker"
    assert result["boundary"] == "context_only"
    assert result["citation_evidence"] is False
    assert result["content"]["notes"][0]["note"] == "Reader notes are context only."
    assert result["metadata"]["evidence_refs"] == [{"evidence_id": 17, "source_type": "paper"}]
