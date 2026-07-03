from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping

from langchain_core.tools import tool

from backend.research_assistant.audit import audit_evidence_claims as _audit_evidence_claims


OUTPUT_BOUNDARIES = {"context_only", "process_trace", "artifact"}
AGENT_TYPES = {"system_builtin", "custom"}
VALIDATION_STATUSES = {"valid", "invalid", "draft", "system_managed"}
RESULT_STATUSES = {"queued", "running", "completed", "failed", "deferred", "cancelled"}


@dataclass(frozen=True)
class SubagentDefinition:
    name: str
    display_name: str
    description: str
    system_prompt: str
    skill_refs: list[str]
    allowed_tools: list[str]
    input_boundaries: dict[str, Any]
    output_boundary: str
    can_answer_user: bool
    can_write_artifacts: bool
    enabled: bool = True
    version: int = 1
    validation_status: str = "valid"
    citation_evidence: bool = False
    agent_type: str = "custom"
    source: str = "registry"
    editable: bool = True
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["metadata"] = data["metadata"] or {}
        return data


@dataclass(frozen=True)
class CitationPayload:
    evidence_id: int
    quote: str
    source_type: str
    citation_label: str


def default_subagent_definitions() -> list[SubagentDefinition]:
    definitions = [
        SubagentDefinition(
            name="research_auditor",
            display_name="Auditor Agent",
            description=(
                "Audit a drafted answer or report against attached citation evidence. "
                "Use only after Supervisor has produced claims and evidence refs."
            ),
            system_prompt=(
                "You are the Research Auditor Agent. Your job is to inspect claims, "
                "citation labels, source types, and evidence boundaries. Treat the "
                "deterministic evidence boundary audit as the hard floor: you may be "
                "stricter than it, but you cannot upgrade invalid or unsupported evidence. "
                "Return process-trace findings to Supervisor. Never answer the user directly."
            ),
            skill_refs=["research-evidence-audit"],
            allowed_tools=["audit_evidence_claims"],
            input_boundaries={
                "requires": ["answer_content", "citations"],
                "citation_sources": ["paper", "web", "database"],
                "context_only_sources": ["memory", "model_reasoning", "process_trace", "tool_logs"],
            },
            output_boundary="process_trace",
            can_answer_user=False,
            can_write_artifacts=False,
        ),
        SubagentDefinition(
            name="paper_reader_worker",
            display_name="Reader Worker",
            description=(
                "Read a scoped evidence/material package for multi-paper batch analysis "
                "or a Supervisor-owned follow-up re-read. Return context-only notes."
            ),
            system_prompt=(
                "You are a scoped Reader Worker. Read only the material package delegated "
                "by Supervisor, extract relevant notes, preserve evidence identifiers when "
                "provided, and return concise context-only findings. Do not create citations, "
                "do not write artifacts, and never answer the user directly."
            ),
            skill_refs=["research-paper-reading"],
            allowed_tools=["read_research_evidence"],
            input_boundaries={
                "requires": ["material_package"],
                "accepted_materials": ["paper_chunks", "evidence_records", "uploaded_text"],
                "supervisor_owns_scope": True,
            },
            output_boundary="context_only",
            can_answer_user=False,
            can_write_artifacts=False,
        ),
    ]
    for definition in definitions:
        validate_subagent_definition(definition)
    return definitions


def system_builtin_subagent_definitions() -> list[SubagentDefinition]:
    definitions = [
        SubagentDefinition(
            name="general-purpose",
            display_name="General Purpose",
            agent_type="system_builtin",
            source="deepagents_builtin",
            editable=False,
            description="DeepAgents built-in general task worker.",
            system_prompt="",
            skill_refs=[],
            allowed_tools=[],
            input_boundaries={},
            output_boundary="process_trace",
            can_answer_user=False,
            can_write_artifacts=False,
            enabled=True,
            validation_status="system_managed",
            citation_evidence=False,
            metadata={"runtime_managed": True},
        ),
    ]
    for definition in definitions:
        validate_subagent_definition(definition)
    return definitions


def registry_subagent_definitions() -> list[SubagentDefinition]:
    return [*system_builtin_subagent_definitions(), *default_subagent_definitions()]


def subagent_lifecycle_identity(agent_name: str) -> dict[str, str]:
    identities = {
        "paper_reader_worker": {
            "agent_role": "reader",
            "agent_type": "custom",
            "source": "registry",
            "output_boundary": "context_only",
        },
        "research_auditor": {
            "agent_role": "auditor",
            "agent_type": "custom",
            "source": "registry",
            "output_boundary": "process_trace",
        },
        "general-purpose": {
            "agent_role": "general",
            "agent_type": "system_builtin",
            "source": "deepagents_builtin",
            "output_boundary": "process_trace",
        },
    }
    return identities.get(
        agent_name,
        {
            "agent_role": "subagent",
            "agent_type": "custom",
            "source": "runtime",
            "output_boundary": "process_trace",
        },
    )


def validate_subagent_definition(definition: SubagentDefinition) -> None:
    if not definition.name.strip():
        raise ValueError("subagent name is required")
    if not definition.description.strip():
        raise ValueError(f"{definition.name}: description is required")
    if definition.agent_type not in AGENT_TYPES:
        raise ValueError(f"{definition.name}: agent_type is invalid")
    if not definition.source.strip():
        raise ValueError(f"{definition.name}: source is required")
    if definition.agent_type == "custom":
        if not definition.system_prompt.strip():
            raise ValueError(f"{definition.name}: system_prompt is required")
        if not definition.allowed_tools:
            raise ValueError(f"{definition.name}: allowed_tools must not be empty")
        if definition.source != "registry":
            raise ValueError(f"{definition.name}: custom source must be registry")
        if not definition.editable:
            raise ValueError(f"{definition.name}: custom agents must be editable")
    if definition.agent_type == "system_builtin":
        if definition.editable:
            raise ValueError(f"{definition.name}: system_builtin agents must be read-only")
        if definition.can_write_artifacts:
            raise ValueError(f"{definition.name}: system_builtin agents cannot write artifacts in F020")
    if definition.output_boundary not in OUTPUT_BOUNDARIES:
        raise ValueError(f"{definition.name}: output_boundary is invalid")
    if definition.validation_status not in VALIDATION_STATUSES:
        raise ValueError(f"{definition.name}: validation_status is invalid")
    if definition.can_answer_user:
        raise ValueError(f"{definition.name}: can_answer_user must stay false for F020")
    if definition.citation_evidence:
        raise ValueError(f"{definition.name}: citation_evidence must stay false for subagent outputs")


def build_deepagents_subagent_configs(
    *,
    definitions: Iterable[SubagentDefinition],
    available_tools: Mapping[str, Any],
) -> list[dict[str, Any]]:
    configs: list[dict[str, Any]] = []
    for definition in definitions:
        validate_subagent_definition(definition)
        if not definition.enabled or definition.agent_type != "custom":
            continue
        tools = []
        for tool_name in definition.allowed_tools:
            if tool_name not in available_tools:
                raise ValueError(f"{definition.name}: missing allowed tool {tool_name}")
            tools.append(available_tools[tool_name])
        configs.append(
            {
                "name": definition.name,
                "description": definition.description,
                "system_prompt": definition.system_prompt,
                "tools": tools,
                "skills": definition.skill_refs,
            }
        )
    return configs


def build_subagent_lifecycle_step_event(
    *,
    workflow_id: str,
    task_id: str,
    agent_name: str,
    agent_role: str,
    status: str,
    phase: str,
    description: str,
    output_boundary: str,
    evidence_refs: list[dict[str, Any]] | None = None,
    parent_agent: str = "DeepAgent",
) -> dict[str, Any]:
    if output_boundary not in OUTPUT_BOUNDARIES:
        raise ValueError("output_boundary is invalid")
    identity = subagent_lifecycle_identity(agent_name)
    metadata = {
        "subagent_lifecycle": {
            "workflow_id": workflow_id,
            "task_id": task_id,
            "parent_agent": parent_agent,
            "agent_name": agent_name,
            "agent_role": agent_role,
            "agent_type": identity["agent_type"],
            "source": identity["source"],
            "phase": phase,
            "status": status,
            "output_boundary": output_boundary,
            "citation_evidence": False,
            "evidence_refs": evidence_refs or [],
        }
    }
    return {
        "event": "step",
        "data": {
            "event_id": f"evt_{uuid.uuid4().hex[:8]}",
            "timestamp": int(time.time()),
            "status": status,
            "id": f"subagent-{task_id}",
            "description": description,
            "metadata": metadata,
        },
    }


def build_subagent_result_envelope(
    *,
    status: str,
    agent: str,
    boundary: str,
    content: Any,
    metadata: dict[str, Any] | None = None,
    citation_evidence: bool = False,
) -> dict[str, Any]:
    if status not in RESULT_STATUSES:
        raise ValueError("status is invalid")
    if not agent.strip():
        raise ValueError("agent is required")
    if boundary not in OUTPUT_BOUNDARIES:
        raise ValueError("boundary is invalid")
    if citation_evidence:
        raise ValueError("subagent result envelope cannot be citation evidence")
    return {
        "status": status,
        "agent": agent,
        "boundary": boundary,
        "citation_evidence": False,
        "content": content,
        "metadata": metadata or {},
    }


@tool
def audit_evidence_claims(answer_content: str, citations_json: str) -> dict[str, Any]:
    """Audit answer claims against citation evidence.

    Args:
        answer_content: Draft answer or report section to audit.
        citations_json: JSON array with evidence_id, quote, source_type, and citation_label.

    Returns:
        Process-trace audit result. This is not citation evidence.
    """
    citations = _citation_payloads(citations_json)
    audit = _audit_evidence_claims(answer_content=answer_content, citations=citations)
    audit_payload = audit.to_dict()
    return build_subagent_result_envelope(
        status="completed",
        agent="research_auditor",
        boundary="process_trace",
        content={"audit": audit_payload},
        metadata={
            "audit_status": audit.status,
            "claim_count": audit.claim_count,
            "deterministic_boundary": True,
        },
    )


@tool
def read_research_evidence(material_package_json: str) -> dict[str, Any]:
    """Read a Supervisor-scoped material package and return context-only notes.

    Args:
        material_package_json: JSON object or array containing evidence records, chunks, or uploaded text.

    Returns:
        Context-only notes with preserved evidence refs when present.
    """
    package = _json_loads(material_package_json, default=[])
    records = package.get("records", package.get("evidence_records", [])) if isinstance(package, dict) else package
    if not isinstance(records, list):
        records = [records]

    notes: list[dict[str, Any]] = []
    evidence_refs: list[dict[str, Any]] = []
    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            text = str(record)
            record = {"content": text}
        evidence_id = record.get("evidence_id")
        source_type = record.get("source_type") or record.get("evidence_type") or "context"
        quote = str(record.get("quote") or record.get("content") or record.get("text") or "").strip()
        title = str(record.get("title") or record.get("paper_title") or "").strip()
        if evidence_id is not None:
            evidence_refs.append({"evidence_id": evidence_id, "source_type": source_type})
        notes.append(
            {
                "index": index,
                "title": title,
                "source_type": source_type,
                "evidence_id": evidence_id,
                "note": quote[:800],
            }
        )

    return build_subagent_result_envelope(
        status="completed",
        agent="paper_reader_worker",
        boundary="context_only",
        content={"notes": notes},
        metadata={
            "evidence_refs": evidence_refs,
            "record_count": len(records),
        },
    )


def _citation_payloads(citations_json: str) -> list[CitationPayload]:
    payload = _json_loads(citations_json, default=[])
    if not isinstance(payload, list):
        raise ValueError("citations_json must decode to a JSON array")
    citations: list[CitationPayload] = []
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            continue
        raw_evidence_id = item.get("evidence_id")
        citations.append(
            CitationPayload(
                evidence_id=_safe_int(raw_evidence_id, fallback=index),
                quote=str(item.get("quote", "")),
                source_type=str(item.get("source_type", "")),
                citation_label=str(item.get("citation_label") or raw_evidence_id or ""),
            )
        )
    return citations


def _safe_int(value: Any, *, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _json_loads(value: str, *, default: Any) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON payload: {exc}") from exc
