from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal, Mapping, Sequence


FindingSeverity = Literal["error", "warning"]


@dataclass(frozen=True)
class ResearchQualityFinding:
    code: str
    message: str
    severity: FindingSeverity = "error"
    path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ResearchQualityRequirement:
    case_id: str
    expected_route: str | None = None
    expected_admission: str | None = None
    min_citation_count: int = 0
    allowed_source_types: set[str] = field(default_factory=lambda: {"paper", "web", "database"})
    allowed_evidence_scopes: set[str] = field(default_factory=lambda: {"session", "project"})
    required_summary_mode: str | None = None
    max_invalid_claims: int = 0
    max_unsupported_claim_ratio: float | None = None
    require_context_boundaries: bool = True
    require_original_evidence_citations: bool = True
    require_semantic_audit_fields: bool = True
    require_llm_semantic_audit: bool = False
    allowed_semantic_auditor_modes: set[str] = field(default_factory=lambda: {"llm_enhanced"})


@dataclass(frozen=True)
class ResearchQualityReport:
    case_id: str
    passed: bool
    metrics: dict[str, Any]
    findings: list[ResearchQualityFinding]

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "passed": self.passed,
            "metrics": self.metrics,
            "findings": [finding.to_dict() for finding in self.findings],
        }

    def assert_passed(self) -> None:
        if self.passed:
            return
        messages = "; ".join(f"{finding.code}: {finding.message}" for finding in self.findings)
        raise AssertionError(f"Research quality gate failed for {self.case_id}: {messages}")


def whole_paper_summary_quality_gate(*, max_unsupported_claim_ratio: float = 0.6) -> ResearchQualityRequirement:
    return ResearchQualityRequirement(
        case_id="whole_paper_summary",
        expected_route="whole_paper_summary",
        expected_admission="accepted",
        min_citation_count=1,
        required_summary_mode="llm_section_global",
        max_unsupported_claim_ratio=max_unsupported_claim_ratio,
    )


def evidence_qa_quality_gate(*, max_unsupported_claim_ratio: float = 0.5) -> ResearchQualityRequirement:
    return ResearchQualityRequirement(
        case_id="evidence_qa",
        expected_route="evidence_qa",
        expected_admission="accepted",
        min_citation_count=1,
        max_unsupported_claim_ratio=max_unsupported_claim_ratio,
    )


def non_evidence_turn_quality_gate() -> ResearchQualityRequirement:
    return ResearchQualityRequirement(
        case_id="non_evidence_turn",
        expected_route="general_chat",
        expected_admission="skipped",
        min_citation_count=0,
        max_unsupported_claim_ratio=1.0,
        require_original_evidence_citations=False,
    )


def evaluate_research_answer(
    answer_payload: Mapping[str, Any],
    requirement: ResearchQualityRequirement,
) -> ResearchQualityReport:
    findings: list[ResearchQualityFinding] = []
    citations = _as_sequence(answer_payload.get("citations"))
    audit = _as_mapping(answer_payload.get("audit"))
    route = _as_mapping(answer_payload.get("task_route"))
    admission = _as_mapping(answer_payload.get("evidence_admission"))
    summary = _as_mapping(answer_payload.get("summary_synthesis"))
    boundaries = _as_mapping(answer_payload.get("context_boundaries"))

    claim_count = _as_int(audit.get("claim_count"))
    unsupported_count = _as_int(audit.get("unsupported_claim_count"))
    invalid_count = _as_int(audit.get("invalid_source_count"))
    unsupported_ratio = unsupported_count / claim_count if claim_count else 0.0

    metrics = {
        "route": route.get("route"),
        "admission": admission.get("decision"),
        "citation_count": len(citations),
        "summary_mode": summary.get("mode"),
        "claim_count": claim_count,
        "approved_claim_count": _as_int(audit.get("approved_claim_count")),
        "partial_claim_count": _as_int(audit.get("partial_claim_count")),
        "unsupported_claim_count": unsupported_count,
        "invalid_source_count": invalid_count,
        "unsupported_claim_ratio": round(unsupported_ratio, 4),
        "citation_source_types": sorted({str(citation.get("source_type", "")) for citation in citations if isinstance(citation, Mapping)}),
        "citation_evidence_scopes": sorted({str(citation.get("evidence_scope", "")) for citation in citations if isinstance(citation, Mapping)}),
        "semantic_finding_codes": sorted(
            {
                str(claim.get("finding_code"))
                for claim in _as_sequence(audit.get("claims"))
                if isinstance(claim, Mapping) and claim.get("finding_code")
            }
        ),
        "semantic_support_statuses": sorted(
            {
                str(claim.get("support_status"))
                for claim in _as_sequence(audit.get("claims"))
                if isinstance(claim, Mapping) and claim.get("support_status")
            }
        ),
        "semantic_auditor_mode": _as_mapping(audit.get("semantic_auditor")).get("mode"),
        "semantic_auditor_status": _as_mapping(audit.get("semantic_auditor")).get("llm_auditor_status"),
    }

    _check_equals(findings, "route", route.get("route"), requirement.expected_route, "task_route.route")
    _check_equals(findings, "admission", admission.get("decision"), requirement.expected_admission, "evidence_admission.decision")

    if len(citations) < requirement.min_citation_count:
        findings.append(
            ResearchQualityFinding(
                code="citation_count_too_low",
                message=f"Expected at least {requirement.min_citation_count} citations, got {len(citations)}.",
                path="citations",
            )
        )

    if requirement.required_summary_mode and summary.get("mode") != requirement.required_summary_mode:
        findings.append(
            ResearchQualityFinding(
                code="summary_mode_mismatch",
                message=f"Expected summary mode {requirement.required_summary_mode!r}, got {summary.get('mode')!r}.",
                path="summary_synthesis.mode",
            )
        )

    if invalid_count > requirement.max_invalid_claims:
        findings.append(
            ResearchQualityFinding(
                code="invalid_claims_exceeded",
                message=f"Expected at most {requirement.max_invalid_claims} invalid-source claims, got {invalid_count}.",
                path="audit.invalid_source_count",
            )
        )

    if requirement.max_unsupported_claim_ratio is not None and unsupported_ratio > requirement.max_unsupported_claim_ratio:
        findings.append(
            ResearchQualityFinding(
                code="unsupported_claim_ratio_exceeded",
                message=(
                    f"Expected unsupported claim ratio <= {requirement.max_unsupported_claim_ratio:.2f}, "
                    f"got {unsupported_ratio:.2f}."
                ),
                path="audit.unsupported_claim_count",
            )
        )

    if requirement.require_context_boundaries:
        _check_context_boundaries(findings, boundaries)

    _check_citations(findings, citations, requirement)
    if requirement.require_semantic_audit_fields:
        _check_semantic_audit_claims(findings, audit)
    if requirement.require_llm_semantic_audit:
        _check_llm_semantic_auditor(findings, audit, requirement)

    passed = not any(finding.severity == "error" for finding in findings)
    return ResearchQualityReport(
        case_id=requirement.case_id,
        passed=passed,
        metrics=metrics,
        findings=findings,
    )


def _check_equals(
    findings: list[ResearchQualityFinding],
    code: str,
    actual: Any,
    expected: str | None,
    path: str,
) -> None:
    if expected is None or actual == expected:
        return
    findings.append(
        ResearchQualityFinding(
            code=f"{code}_mismatch",
            message=f"Expected {path}={expected!r}, got {actual!r}.",
            path=path,
        )
    )


def _check_context_boundaries(findings: list[ResearchQualityFinding], boundaries: Mapping[str, Any]) -> None:
    expected = {
        "citation_evidence": {"paper", "web", "database"},
        "context_only_memory": {"memory"},
        "process_trace": {"tool_logs", "runtime_results", "agent_lifecycle"},
        "model_reasoning": {"model_reasoning"},
    }
    for key, expected_values in expected.items():
        actual_values = set(str(value) for value in _as_sequence(boundaries.get(key)))
        if actual_values != expected_values:
            findings.append(
                ResearchQualityFinding(
                    code="context_boundary_mismatch",
                    message=f"Expected {key}={sorted(expected_values)!r}, got {sorted(actual_values)!r}.",
                    path=f"context_boundaries.{key}",
                )
            )


def _check_citations(
    findings: list[ResearchQualityFinding],
    citations: Sequence[Any],
    requirement: ResearchQualityRequirement,
) -> None:
    for index, citation in enumerate(citations):
        if not isinstance(citation, Mapping):
            findings.append(
                ResearchQualityFinding(
                    code="citation_shape_invalid",
                    message=f"Citation at index {index} is not an object.",
                    path=f"citations[{index}]",
                )
            )
            continue
        source_type = str(citation.get("source_type", ""))
        evidence_scope = str(citation.get("evidence_scope", ""))
        if source_type not in requirement.allowed_source_types:
            findings.append(
                ResearchQualityFinding(
                    code="citation_source_type_invalid",
                    message=f"Citation {citation.get('citation_label') or index} has invalid source_type={source_type!r}.",
                    path=f"citations[{index}].source_type",
                )
            )
        if evidence_scope not in requirement.allowed_evidence_scopes:
            findings.append(
                ResearchQualityFinding(
                    code="citation_scope_invalid",
                    message=f"Citation {citation.get('citation_label') or index} has invalid evidence_scope={evidence_scope!r}.",
                    path=f"citations[{index}].evidence_scope",
                )
            )
        if requirement.require_original_evidence_citations and not citation.get("evidence_id"):
            findings.append(
                ResearchQualityFinding(
                    code="citation_missing_evidence_id",
                    message=f"Citation {citation.get('citation_label') or index} is missing original evidence_id.",
                    path=f"citations[{index}].evidence_id",
                )
            )
        _check_citation_traceability(findings, citation, index)


def _check_citation_traceability(
    findings: list[ResearchQualityFinding],
    citation: Mapping[str, Any],
    index: int,
) -> None:
    required_identity = ("paper_id", "title", "section", "chunk_id")
    for field_name in required_identity:
        if not str(citation.get(field_name) or "").strip():
            findings.append(
                ResearchQualityFinding(
                    code=f"citation_{field_name}_missing",
                    message=f"Citation {citation.get('citation_label') or index} is missing {field_name}.",
                    path=f"citations[{index}].{field_name}",
                )
            )
    if not str(citation.get("quote") or "").strip():
        findings.append(
            ResearchQualityFinding(
                code="citation_quote_missing",
                message=f"Citation {citation.get('citation_label') or index} is missing a quote/snippet.",
                path=f"citations[{index}].quote",
            )
        )


def _check_semantic_audit_claims(findings: list[ResearchQualityFinding], audit: Mapping[str, Any]) -> None:
    claims = _as_sequence(audit.get("claims"))
    if _as_int(audit.get("claim_count")) > 0 and not claims:
        findings.append(
            ResearchQualityFinding(
                code="semantic_audit_claims_missing",
                message="Audit reports claims but does not include claim-level semantic audit records.",
                path="audit.claims",
            )
        )
        return

    allowed_support_status = {
        "supported",
        "partial",
        "unsupported",
        "overreach",
        "source_mismatch",
        "insufficient_evidence",
    }
    for index, claim in enumerate(claims):
        if not isinstance(claim, Mapping):
            findings.append(
                ResearchQualityFinding(
                    code="semantic_audit_claim_shape_invalid",
                    message=f"Audit claim at index {index} is not an object.",
                    path=f"audit.claims[{index}]",
                )
            )
            continue
        if not str(claim.get("claim_id") or "").strip():
            findings.append(
                ResearchQualityFinding(
                    code="semantic_audit_claim_id_missing",
                    message=f"Audit claim at index {index} is missing claim_id.",
                    path=f"audit.claims[{index}].claim_id",
                )
            )
        support_status = str(claim.get("support_status") or "")
        if support_status not in allowed_support_status:
            findings.append(
                ResearchQualityFinding(
                    code="semantic_audit_support_status_invalid",
                    message=f"Audit claim {claim.get('claim_id') or index} has invalid support_status={support_status!r}.",
                    path=f"audit.claims[{index}].support_status",
                )
            )
        for score_field in ("semantic_relevance_score", "source_quality_score"):
            score = claim.get(score_field)
            if not isinstance(score, (int, float)):
                findings.append(
                    ResearchQualityFinding(
                        code="semantic_audit_score_missing",
                        message=f"Audit claim {claim.get('claim_id') or index} is missing numeric {score_field}.",
                        path=f"audit.claims[{index}].{score_field}",
                    )
                )
            elif score < 0 or score > 1:
                findings.append(
                    ResearchQualityFinding(
                        code="semantic_audit_score_out_of_range",
                        message=f"Audit claim {claim.get('claim_id') or index} has {score_field} outside [0, 1].",
                        path=f"audit.claims[{index}].{score_field}",
                    )
                )
        if support_status != "insufficient_evidence" and not _as_sequence(claim.get("cited_evidence")):
            findings.append(
                ResearchQualityFinding(
                    code="semantic_audit_cited_evidence_missing",
                    message=f"Audit claim {claim.get('claim_id') or index} is missing cited_evidence.",
                    path=f"audit.claims[{index}].cited_evidence",
                )
            )


def _check_llm_semantic_auditor(
    findings: list[ResearchQualityFinding],
    audit: Mapping[str, Any],
    requirement: ResearchQualityRequirement,
) -> None:
    metadata = _as_mapping(audit.get("semantic_auditor"))
    mode = str(metadata.get("mode") or "")
    if not metadata:
        findings.append(
            ResearchQualityFinding(
                code="llm_semantic_auditor_missing",
                message="Audit payload is missing semantic_auditor metadata required by this case.",
                path="audit.semantic_auditor",
            )
        )
        return
    if mode not in requirement.allowed_semantic_auditor_modes:
        findings.append(
            ResearchQualityFinding(
                code="llm_semantic_auditor_mode_invalid",
                message=f"Expected semantic auditor mode in {sorted(requirement.allowed_semantic_auditor_modes)!r}, got {mode!r}.",
                path="audit.semantic_auditor.mode",
            )
        )
    for index, claim in enumerate(_as_sequence(audit.get("claims"))):
        if not isinstance(claim, Mapping):
            continue
        if not str(claim.get("deterministic_support_status") or "").strip():
            findings.append(
                ResearchQualityFinding(
                    code="llm_semantic_audit_deterministic_status_missing",
                    message=f"Audit claim {claim.get('claim_id') or index} is missing deterministic_support_status.",
                    path=f"audit.claims[{index}].deterministic_support_status",
                )
            )
        if not str(claim.get("llm_support_status") or "").strip():
            findings.append(
                ResearchQualityFinding(
                    code="llm_semantic_audit_status_missing",
                    message=f"Audit claim {claim.get('claim_id') or index} is missing llm_support_status.",
                    path=f"audit.claims[{index}].llm_support_status",
                )
            )
        if not str(claim.get("llm_rationale") or "").strip():
            findings.append(
                ResearchQualityFinding(
                    code="llm_semantic_audit_rationale_missing",
                    message=f"Audit claim {claim.get('claim_id') or index} is missing llm_rationale.",
                    path=f"audit.claims[{index}].llm_rationale",
                )
            )


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _as_sequence(value: Any) -> Sequence[Any]:
    return value if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)) else []


def _as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
