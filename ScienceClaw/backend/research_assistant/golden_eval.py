from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal, Mapping

from backend.research_assistant.evaluation import (
    ResearchQualityReport,
    ResearchQualityRequirement,
    evaluate_research_answer,
)


GoldenEvalTaskType = Literal[
    "whole_paper_summary",
    "evidence_qa",
    "no_evidence_or_insufficient_evidence",
    "multi_paper_synthesis",
    "literature_review",
]
GoldenEvalMode = Literal["payload", "live_ui"]


@dataclass(frozen=True)
class GoldenEvalThresholds:
    min_citation_count: int = 1
    max_citation_count: int | None = None
    max_unsupported_claim_ratio: float | None = 0.5
    max_invalid_claims: int = 0
    required_summary_mode: str | None = None
    allowed_admission_decisions: list[str] | None = None
    min_distinct_cited_papers: int | None = None
    expected_support_statuses: list[str] | None = None
    expected_finding_codes: list[str] | None = None
    require_llm_semantic_audit: bool = False
    allowed_semantic_auditor_modes: list[str] | None = None
    min_evidence_matrix_papers: int | None = None
    min_evidence_matrix_themes: int | None = None
    min_theme_paper_cells: int | None = None
    min_evidence_linked_cells: int | None = None
    required_report_sections: list[str] | None = None


@dataclass(frozen=True)
class GoldenEvalRequiredOutputs:
    answer: bool = True
    report: bool = False
    markdown_summary: bool = True


@dataclass(frozen=True)
class GoldenEvalCase:
    case_id: str
    task_type: GoldenEvalTaskType
    mode: GoldenEvalMode
    paper_paths: list[str]
    question: str
    quality_thresholds: GoldenEvalThresholds = field(default_factory=GoldenEvalThresholds)
    required_outputs: GoldenEvalRequiredOutputs = field(default_factory=GoldenEvalRequiredOutputs)
    answer_payload_path: str | None = None
    report_payload_path: str | None = None

    def to_quality_requirement(self) -> ResearchQualityRequirement:
        expected_route = {
            "whole_paper_summary": "whole_paper_summary",
            "evidence_qa": "evidence_qa",
            "no_evidence_or_insufficient_evidence": "evidence_qa",
            "multi_paper_synthesis": "evidence_qa",
            "literature_review": "evidence_qa",
        }[self.task_type]
        expected_admission = "accepted"
        if self.task_type == "no_evidence_or_insufficient_evidence":
            expected_admission = None
        return ResearchQualityRequirement(
            case_id=self.case_id,
            expected_route=expected_route,
            expected_admission=expected_admission,
            min_citation_count=self.quality_thresholds.min_citation_count,
            required_summary_mode=self.quality_thresholds.required_summary_mode,
            max_invalid_claims=self.quality_thresholds.max_invalid_claims,
            max_unsupported_claim_ratio=self.quality_thresholds.max_unsupported_claim_ratio,
            require_llm_semantic_audit=self.quality_thresholds.require_llm_semantic_audit,
            allowed_semantic_auditor_modes=set(self.quality_thresholds.allowed_semantic_auditor_modes or ["llm_enhanced"]),
            min_evidence_matrix_papers=self.quality_thresholds.min_evidence_matrix_papers,
            min_evidence_matrix_themes=self.quality_thresholds.min_evidence_matrix_themes,
            min_theme_paper_cells=self.quality_thresholds.min_theme_paper_cells,
            min_evidence_linked_cells=self.quality_thresholds.min_evidence_linked_cells,
            required_report_sections=set(self.quality_thresholds.required_report_sections or []),
        )


@dataclass(frozen=True)
class GoldenEvalCaseResult:
    case_id: str
    task_type: str
    mode: str
    passed: bool
    quality: dict[str, Any]
    answer_payload_path: str | None = None
    report_payload_path: str | None = None
    answer_payload: dict[str, Any] | None = None
    report_payload: dict[str, Any] | None = None
    owner_module_hints: list[str] = field(default_factory=list)
    failure_summary_path: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GoldenEvalRunResult:
    run_id: str
    mode: str
    cases: list[GoldenEvalCaseResult]

    @property
    def case_count(self) -> int:
        return len(self.cases)

    @property
    def passed_count(self) -> int:
        return sum(1 for case in self.cases if case.passed)

    @property
    def failed_count(self) -> int:
        return self.case_count - self.passed_count

    @property
    def passed(self) -> bool:
        return self.failed_count == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "mode": self.mode,
            "case_count": self.case_count,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "passed": self.passed,
            "cases": [case.to_dict() for case in self.cases],
        }


def load_golden_cases(path: str | Path) -> list[GoldenEvalCase]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    raw_cases = payload.get("cases") if isinstance(payload, Mapping) else None
    if not isinstance(raw_cases, list):
        raise ValueError("golden cases file must contain a cases array")
    return [_parse_case(raw_case) for raw_case in raw_cases]


def evaluate_payload_cases(
    cases: list[GoldenEvalCase],
    *,
    root: str | Path,
    payload_dir: str | Path | None = None,
    run_id: str | None = None,
) -> GoldenEvalRunResult:
    root_path = Path(root)
    payload_path = Path(payload_dir) if payload_dir else None
    results: list[GoldenEvalCaseResult] = []
    for case in cases:
        try:
            if case.mode != "payload":
                continue
            if not case.answer_payload_path:
                raise ValueError("payload case is missing answer_payload_path")
            preflight_findings = _payload_case_preflight_findings(case, root_path, payload_path)
            answer_path = _resolve_payload_path(root_path, payload_path, case.answer_payload_path)
            answer_payload = json.loads(answer_path.read_text(encoding="utf-8"))
            quality = evaluate_research_answer(answer_payload, case.to_quality_requirement())
            quality_dict = _quality_dict_with_case_checks(case, answer_payload, quality, extra_findings=preflight_findings)
            report_path = _resolve_payload_path(root_path, payload_path, case.report_payload_path) if case.report_payload_path else None
            results.append(
                GoldenEvalCaseResult(
                    case_id=case.case_id,
                    task_type=case.task_type,
                    mode=case.mode,
                    passed=bool(quality_dict.get("passed")),
                    quality=quality_dict,
                    answer_payload_path=str(answer_path),
                    report_payload_path=str(report_path) if report_path else None,
                    owner_module_hints=owner_module_hints_for_quality(quality_dict),
                )
            )
        except Exception as exc:  # Batch eval must preserve failed cases.
            quality_dict = _exception_quality(case, exc)
            results.append(
                GoldenEvalCaseResult(
                    case_id=case.case_id,
                    task_type=case.task_type,
                    mode=case.mode,
                    passed=False,
                    quality=quality_dict,
                    owner_module_hints=owner_module_hints_for_quality(quality_dict),
                    error=str(exc),
                )
            )
    return GoldenEvalRunResult(run_id=run_id or f"golden-{uuid.uuid4().hex[:8]}", mode="payload", cases=results)


def evaluate_live_ui_case(
    case: GoldenEvalCase,
    *,
    ui_result: Any,
    run_id: str | None = None,
) -> GoldenEvalRunResult:
    assert_live_golden_eval_result(ui_result, require_report=case.required_outputs.report)
    quality = evaluate_research_answer(ui_result.answer_payload, case.to_quality_requirement())
    quality_dict = _quality_dict_with_case_checks(case, ui_result.answer_payload, quality)
    result = GoldenEvalCaseResult(
        case_id=case.case_id,
        task_type=case.task_type,
        mode="live_ui",
        passed=bool(quality_dict.get("passed")),
        quality=quality_dict,
        answer_payload=ui_result.answer_payload,
        report_payload=ui_result.report_payload,
        owner_module_hints=owner_module_hints_for_quality(quality_dict),
    )
    return GoldenEvalRunResult(run_id=run_id or f"live-ui-{uuid.uuid4().hex[:8]}", mode="live-ui", cases=[result])


def write_golden_eval_outputs(run_result: GoldenEvalRunResult, output_dir: str | Path) -> None:
    output_path = Path(output_dir)
    cases_path = output_path / "cases"
    cases_path.mkdir(parents=True, exist_ok=True)
    serialized_cases: list[dict[str, Any]] = []
    for case in run_result.cases:
        case_dict = case.to_dict()
        quality_path = cases_path / f"{case.case_id}.quality.json"
        quality_path.write_text(
            json.dumps(case.quality, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        if not case.passed:
            failure_path = cases_path / f"{case.case_id}.failure.md"
            failure_path.write_text(render_case_failure_summary(case), encoding="utf-8")
            case_dict["failure_summary_path"] = str(failure_path)
        if case.answer_payload_path:
            source = Path(case.answer_payload_path)
            if source.exists():
                answer_path = cases_path / f"{case.case_id}.answer.json"
                shutil.copyfile(source, answer_path)
                case_dict["answer_payload_path"] = str(answer_path)
        elif case.answer_payload is not None:
            answer_path = cases_path / f"{case.case_id}.answer.json"
            answer_path.write_text(
                json.dumps(case.answer_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            case_dict["answer_payload_path"] = str(answer_path)
        if case_dict.get("answer_payload_path"):
            case_dict["answer_payload"] = None
        if case.report_payload_path:
            source = Path(case.report_payload_path)
            if source.exists():
                report_path = cases_path / f"{case.case_id}.report.json"
                shutil.copyfile(source, report_path)
                case_dict["report_payload_path"] = str(report_path)
        elif case.report_payload is not None:
            report_path = cases_path / f"{case.case_id}.report.json"
            report_path.write_text(
                json.dumps(case.report_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            case_dict["report_payload_path"] = str(report_path)
        if case_dict.get("report_payload_path"):
            case_dict["report_payload"] = None
        serialized_cases.append(case_dict)
    serialized_result = {
        "run_id": run_result.run_id,
        "mode": run_result.mode,
        "case_count": run_result.case_count,
        "passed_count": run_result.passed_count,
        "failed_count": run_result.failed_count,
        "passed": run_result.passed,
        "cases": serialized_cases,
    }
    (output_path / "results.json").write_text(
        json.dumps(serialized_result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_path / "summary.md").write_text(render_markdown_summary(run_result), encoding="utf-8")


def render_markdown_summary(run_result: GoldenEvalRunResult) -> str:
    lines = [
        "# Research Golden Eval Summary",
        "",
        f"- Run: `{run_result.run_id}`",
        f"- Mode: `{run_result.mode}`",
        f"- Cases: {run_result.case_count}",
        f"- Passed: {run_result.passed_count}",
        f"- Failed: {run_result.failed_count}",
        "",
        "## Cases",
        "",
    ]
    for case in run_result.cases:
        status = "PASS" if case.passed else "FAIL"
        lines.extend(
            [
                f"### {case.case_id}: {status}",
                "",
                f"- Task type: `{case.task_type}`",
                f"- Mode: `{case.mode}`",
            ]
        )
        if case.error:
            lines.append(f"- Error: {case.error}")
        findings = case.quality.get("findings", []) if isinstance(case.quality, Mapping) else []
        if findings:
            lines.append("- Findings:")
            for finding in findings:
                code = finding.get("code", "unknown") if isinstance(finding, Mapping) else str(finding)
                message = finding.get("message", "") if isinstance(finding, Mapping) else ""
                lines.append(f"  - `{code}`: {message} -> {module_hint_for_finding(code)}")
        if case.owner_module_hints:
            lines.append(f"- Owner module hints: {', '.join(case.owner_module_hints)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def module_hint_for_finding(code: str) -> str:
    if code in {"citation_count_too_low", "citation_count_too_high", "admission_mismatch"}:
        return "Check F005 retrieval / F011 admission."
    if code in {"route_mismatch"}:
        return "Check F013 routing."
    if code in {"unsupported_claim_ratio_exceeded", "invalid_claims_exceeded"}:
        return "Check F006 Evidence Audit / F018 calibration / F019 thresholds."
    if code.startswith("llm_semantic_"):
        return "Check F023 LLM semantic auditor."
    if code.startswith("semantic_"):
        return "Check F006 Evidence Audit / F018 calibration / F022/F023 semantic audit."
    if code in {"summary_mode_mismatch"}:
        return "Check F017 synthesis."
    if code in {"multi_paper_citation_coverage_too_low"}:
        return "Check F005 retrieval / F011 admission / F017 synthesis."
    if code.startswith("evidence_matrix_") or code.startswith("literature_review_"):
        return "Check F024 evidence matrix literature review."
    if code in {"admission_not_insufficient"}:
        return "Check F011 admission."
    if code in {"multi_agent_lifecycle_missing"}:
        return "Check F020 multi-agent lifecycle."
    if code in {"case_exception", "paper_fixture_missing", "required_answer_missing", "required_report_missing"}:
        return "Check F019 golden eval harness."
    if code.startswith("citation_") or code.startswith("context_boundary"):
        return "Check F004/F006 citation boundary and audit."
    return "Inspect the owning research workflow."


def owner_module_hints_for_quality(quality: Mapping[str, Any]) -> list[str]:
    findings = quality.get("findings", [])
    hints: set[str] = set()
    for finding in findings if isinstance(findings, list) else []:
        if not isinstance(finding, Mapping):
            continue
        for hint in _owner_modules_for_finding(str(finding.get("code", ""))):
            hints.add(hint)
    return sorted(hints)


def render_case_failure_summary(case: GoldenEvalCaseResult) -> str:
    lines = [
        f"# {case.case_id} Failure Summary",
        "",
        f"- Task type: `{case.task_type}`",
        f"- Mode: `{case.mode}`",
    ]
    if case.error:
        lines.append(f"- Error: {case.error}")
    if case.owner_module_hints:
        lines.append(f"- Owner module hints: {', '.join(case.owner_module_hints)}")
    findings = case.quality.get("findings", []) if isinstance(case.quality, Mapping) else []
    if findings:
        lines.extend(["", "## Findings", ""])
        for finding in findings:
            if not isinstance(finding, Mapping):
                continue
            lines.append(f"- `{finding.get('code', 'unknown')}`: {finding.get('message', '')}")
            modules = finding.get("owner_module_hints") or []
            if modules:
                lines.append(f"  Owner hints: {', '.join(str(module) for module in modules)}")
    return "\n".join(lines).rstrip() + "\n"


def assert_live_golden_eval_result(ui_result: Any, *, require_report: bool) -> None:
    if not getattr(ui_result, "answer_payload", None):
        raise AssertionError("live golden eval result is missing answer payload")
    answer_payload = ui_result.answer_payload
    if not answer_payload.get("citations"):
        raise AssertionError("live golden eval answer payload has no citations")
    if not answer_payload.get("audit"):
        raise AssertionError("live golden eval answer payload has no audit metadata")
    if not answer_payload.get("context_boundaries"):
        raise AssertionError("live golden eval answer payload has no context boundaries")
    if require_report:
        if not getattr(ui_result, "report_payload", None):
            raise AssertionError("live golden eval result is missing report payload")
        round_files = getattr(ui_result, "round_files", [])
        if not any(str(name).endswith(".evidence.json") for name in round_files):
            raise AssertionError("live golden eval result is missing report evidence sidecar")


def _parse_case(raw_case: Any) -> GoldenEvalCase:
    if not isinstance(raw_case, Mapping):
        raise ValueError("golden case must be an object")
    thresholds = raw_case.get("quality_thresholds") or {}
    outputs = raw_case.get("required_outputs") or {}
    return GoldenEvalCase(
        case_id=_required_str(raw_case, "case_id"),
        task_type=_required_str(raw_case, "task_type"),  # type: ignore[arg-type]
        mode=_required_str(raw_case, "mode"),  # type: ignore[arg-type]
        paper_paths=[str(path) for path in raw_case.get("paper_paths", [])],
        question=_required_str(raw_case, "question"),
        answer_payload_path=raw_case.get("answer_payload_path"),
        report_payload_path=raw_case.get("report_payload_path"),
        quality_thresholds=GoldenEvalThresholds(
            min_citation_count=int(thresholds.get("min_citation_count", 1)),
            max_citation_count=_optional_int(thresholds.get("max_citation_count")),
            max_unsupported_claim_ratio=thresholds.get("max_unsupported_claim_ratio", 0.5),
            max_invalid_claims=int(thresholds.get("max_invalid_claims", 0)),
            required_summary_mode=thresholds.get("required_summary_mode"),
            allowed_admission_decisions=_optional_str_list(thresholds.get("allowed_admission_decisions")),
            min_distinct_cited_papers=_optional_int(thresholds.get("min_distinct_cited_papers")),
            expected_support_statuses=_optional_str_list(thresholds.get("expected_support_statuses")),
            expected_finding_codes=_optional_str_list(thresholds.get("expected_finding_codes")),
            require_llm_semantic_audit=bool(thresholds.get("require_llm_semantic_audit", False)),
            allowed_semantic_auditor_modes=_optional_str_list(thresholds.get("allowed_semantic_auditor_modes")),
            min_evidence_matrix_papers=_optional_int(thresholds.get("min_evidence_matrix_papers")),
            min_evidence_matrix_themes=_optional_int(thresholds.get("min_evidence_matrix_themes")),
            min_theme_paper_cells=_optional_int(thresholds.get("min_theme_paper_cells")),
            min_evidence_linked_cells=_optional_int(thresholds.get("min_evidence_linked_cells")),
            required_report_sections=_optional_str_list(thresholds.get("required_report_sections")),
        ),
        required_outputs=GoldenEvalRequiredOutputs(
            answer=bool(outputs.get("answer", True)),
            report=bool(outputs.get("report", False)),
            markdown_summary=bool(outputs.get("markdown_summary", True)),
        ),
    )


def _required_str(mapping: Mapping[str, Any], key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"golden case missing required string field {key}")
    return value


def _resolve_payload_path(root: Path, payload_dir: Path | None, answer_payload_path: str) -> Path:
    raw_path = Path(answer_payload_path)
    if raw_path.is_absolute():
        return raw_path.resolve()
    candidates = [root / raw_path]
    if payload_dir is not None:
        candidates.append(payload_dir / raw_path.name)
        candidates.append(payload_dir / raw_path)
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return candidates[0].resolve()


def _resolve_case_file_path(root: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path.resolve()
    candidates = [
        root / path,
        root.parent / path,
        root.parent.parent / path,
        Path.cwd() / path,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return candidates[0].resolve()


def _payload_case_preflight_findings(
    case: GoldenEvalCase,
    root: Path,
    payload_dir: Path | None,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if case.required_outputs.answer and not case.answer_payload_path:
        findings.append(
            _finding_dict(
                "required_answer_missing",
                "Payload case requires an answer artifact but has no answer_payload_path.",
                "answer_payload_path",
            )
        )
    if case.required_outputs.report:
        if not case.report_payload_path:
            findings.append(
                _finding_dict(
                    "required_report_missing",
                    "Payload case requires a report artifact but has no report_payload_path.",
                    "report_payload_path",
                )
            )
        else:
            report_path = _resolve_payload_path(root, payload_dir, case.report_payload_path)
            if not report_path.exists():
                findings.append(
                    _finding_dict(
                        "required_report_missing",
                        f"Required report artifact does not exist: {report_path}.",
                        "report_payload_path",
                    )
                )
    for index, paper_path in enumerate(case.paper_paths):
        resolved_path = _resolve_case_file_path(root, paper_path)
        if not resolved_path.exists():
            findings.append(
                _finding_dict(
                    "paper_fixture_missing",
                    f"Declared real paper fixture does not exist: {resolved_path}.",
                    f"paper_paths[{index}]",
                )
            )
    return findings


def _quality_dict_with_case_checks(
    case: GoldenEvalCase,
    answer_payload: Mapping[str, Any],
    quality: ResearchQualityReport,
    *,
    extra_findings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    quality_dict = quality.to_dict()
    findings = list(quality_dict.get("findings", []))
    findings.extend(extra_findings or [])
    thresholds = case.quality_thresholds
    citations = _as_list(answer_payload.get("citations"))
    admission = _as_mapping(answer_payload.get("evidence_admission")).get("decision")

    if thresholds.max_citation_count is not None and len(citations) > thresholds.max_citation_count:
        findings.append(
            _finding_dict(
                "citation_count_too_high",
                f"Expected at most {thresholds.max_citation_count} citations, got {len(citations)}.",
                "citations",
            )
        )
    if thresholds.allowed_admission_decisions and admission not in thresholds.allowed_admission_decisions:
        findings.append(
            _finding_dict(
                "admission_not_insufficient",
                f"Expected admission decision in {thresholds.allowed_admission_decisions!r}, got {admission!r}.",
                "evidence_admission.decision",
            )
        )
    if thresholds.min_distinct_cited_papers is not None:
        distinct_papers = _distinct_cited_papers(citations)
        quality_dict.setdefault("metrics", {})["distinct_cited_paper_count"] = len(distinct_papers)
        quality_dict["metrics"]["distinct_cited_papers"] = sorted(distinct_papers)
        if len(distinct_papers) < thresholds.min_distinct_cited_papers:
            findings.append(
                _finding_dict(
                    "multi_paper_citation_coverage_too_low",
                    f"Expected citations from at least {thresholds.min_distinct_cited_papers} papers, got {len(distinct_papers)}.",
                    "citations",
                )
            )
    if thresholds.expected_support_statuses:
        actual_statuses = set(_as_list(quality_dict.get("metrics", {}).get("semantic_support_statuses")))
        missing_statuses = sorted(set(thresholds.expected_support_statuses) - actual_statuses)
        if missing_statuses:
            findings.append(
                _finding_dict(
                    "semantic_support_status_missing",
                    f"Expected semantic support statuses {missing_statuses!r} in audit claims.",
                    "audit.claims.support_status",
                )
            )
    if thresholds.expected_finding_codes:
        actual_codes = set(_as_list(quality_dict.get("metrics", {}).get("semantic_finding_codes")))
        missing_codes = sorted(set(thresholds.expected_finding_codes) - actual_codes)
        if missing_codes:
            findings.append(
                _finding_dict(
                    "semantic_finding_code_missing",
                    f"Expected semantic finding codes {missing_codes!r} in audit claims.",
                    "audit.claims.finding_code",
                )
            )

    decorated_findings = [_decorate_finding(finding) for finding in findings]
    quality_dict["findings"] = decorated_findings
    quality_dict["owner_module_hints"] = owner_module_hints_for_quality(quality_dict)
    quality_dict["passed"] = not any(finding.get("severity", "error") == "error" for finding in decorated_findings)
    return quality_dict


def _exception_quality(case: GoldenEvalCase, exc: Exception) -> dict[str, Any]:
    finding = _decorate_finding(_finding_dict("case_exception", str(exc), "case"))
    return {
        "case_id": case.case_id,
        "passed": False,
        "metrics": {},
        "findings": [finding],
        "owner_module_hints": owner_module_hints_for_quality({"findings": [finding]}),
    }


def _finding_dict(code: str, message: str, path: str) -> dict[str, Any]:
    return {"code": code, "message": message, "severity": "error", "path": path}


def _decorate_finding(finding: Any) -> dict[str, Any]:
    if isinstance(finding, Mapping):
        decorated = dict(finding)
    else:
        decorated = _finding_dict(str(finding), "", "")
    modules = _owner_modules_for_finding(str(decorated.get("code", "")))
    decorated["owner_module_hints"] = modules
    decorated["owner_module_hint"] = module_hint_for_finding(str(decorated.get("code", "")))
    return decorated


def _owner_modules_for_finding(code: str) -> list[str]:
    if code in {"citation_count_too_low", "citation_count_too_high", "admission_mismatch"}:
        return ["F005 retrieval", "F011 admission"]
    if code == "route_mismatch":
        return ["F013 routing"]
    if code in {"unsupported_claim_ratio_exceeded", "invalid_claims_exceeded"}:
        return ["F006 audit", "F018 calibration", "F019 golden eval"]
    if code.startswith("llm_semantic_"):
        return ["F023 LLM semantic auditor"]
    if code.startswith("semantic_"):
        return ["F006 audit", "F018 calibration", "F022 semantic audit", "F023 LLM semantic auditor"]
    if code == "summary_mode_mismatch":
        return ["F017 synthesis"]
    if code == "multi_paper_citation_coverage_too_low":
        return ["F005 retrieval", "F011 admission", "F017 synthesis"]
    if code.startswith("evidence_matrix_") or code.startswith("literature_review_"):
        return ["F024 evidence matrix literature review"]
    if code == "admission_not_insufficient":
        return ["F011 admission"]
    if code == "multi_agent_lifecycle_missing":
        return ["F020 multi-agent"]
    if code in {"case_exception", "paper_fixture_missing", "required_answer_missing", "required_report_missing"}:
        return ["F019 golden eval"]
    if code.startswith("citation_") or code.startswith("context_boundary"):
        return ["F004 citation boundary", "F006 audit"]
    return ["research workflow"]


def _distinct_cited_papers(citations: list[Any]) -> set[str]:
    papers: set[str] = set()
    for citation in citations:
        if not isinstance(citation, Mapping):
            continue
        paper_id = citation.get("paper_id")
        source_identity = citation.get("source_identity")
        if not paper_id and isinstance(source_identity, Mapping):
            paper_id = source_identity.get("paper_id") or source_identity.get("doi")
        if paper_id:
            papers.add(str(paper_id))
    return papers


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _optional_str_list(value: Any) -> list[str] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError("expected a string array")
    return [str(item) for item in value]


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}
