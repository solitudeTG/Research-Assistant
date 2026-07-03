from __future__ import annotations

from dataclasses import replace

import pytest

from backend.research_assistant.subagents import (
    SubagentDefinition,
    build_deepagents_subagent_configs,
    build_subagent_lifecycle_step_event,
    default_subagent_definitions,
    validate_subagent_definition,
)


def _definitions_by_name() -> dict[str, SubagentDefinition]:
    return {definition.name: definition for definition in default_subagent_definitions()}


def test_default_research_subagents_are_governed_workers_not_user_agents():
    definitions = _definitions_by_name()

    assert set(definitions) == {"research_auditor", "paper_reader_worker"}

    auditor = definitions["research_auditor"]
    assert auditor.display_name == "Auditor Agent"
    assert auditor.output_boundary == "process_trace"
    assert auditor.allowed_tools == ["audit_evidence_claims"]
    assert auditor.can_answer_user is False
    assert auditor.can_write_artifacts is False
    assert auditor.citation_evidence is False
    assert "deterministic evidence boundary" in auditor.system_prompt
    assert "cannot upgrade" in auditor.system_prompt

    reader = definitions["paper_reader_worker"]
    assert reader.display_name == "Reader Worker"
    assert reader.output_boundary == "context_only"
    assert reader.allowed_tools == ["read_research_evidence"]
    assert reader.can_answer_user is False
    assert reader.can_write_artifacts is False
    assert reader.citation_evidence is False
    assert "multi-paper" in reader.description
    assert "follow-up" in reader.description


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
        "agent_name": "paper_reader_worker",
        "agent_role": "reader",
        "phase": "started",
        "status": "running",
        "output_boundary": "context_only",
        "citation_evidence": False,
        "evidence_refs": [{"evidence_id": 12, "source_type": "paper"}],
    }
