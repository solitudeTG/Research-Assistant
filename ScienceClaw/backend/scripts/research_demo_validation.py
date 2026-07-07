from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal, Mapping
from urllib.request import Request, urlopen


StepStatus = Literal["pass", "fail", "skipped", "blocked"]
OverallStatus = Literal["pass", "fail", "blocked", "partial"]
CommandRunner = Callable[[list[str], Path, int, Path], "CommandResult"]


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


@dataclass
class StepResult:
    name: str
    status: StepStatus
    command: list[str] = field(default_factory=list)
    duration_ms: int = 0
    output_path: str = ""
    key_metrics: dict[str, Any] = field(default_factory=dict)
    failure_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DemoValidationRunner:
    def __init__(
        self,
        *,
        repo_root: Path,
        output_dir: Path,
        command_runner: CommandRunner | None = None,
        timeout_ms: int = 600_000,
    ) -> None:
        self.repo_root = repo_root
        self.output_dir = output_dir
        self.timeout_ms = timeout_ms
        self.command_runner = command_runner or run_subprocess_command

    def run_command_step(
        self,
        name: str,
        command: list[str],
        output_path: Path,
        *,
        blocked_on_failure: bool = False,
        timeout_ms: int | None = None,
    ) -> StepResult:
        output_path.mkdir(parents=True, exist_ok=True)
        started = time.perf_counter()
        result = self.command_runner(command, self.repo_root, timeout_ms or self.timeout_ms, output_path)
        duration_ms = int((time.perf_counter() - started) * 1000)
        (output_path / "stdout.txt").write_text(result.stdout, encoding="utf-8", errors="replace")
        (output_path / "stderr.txt").write_text(result.stderr, encoding="utf-8", errors="replace")
        status: StepStatus = "pass" if result.returncode == 0 else "blocked" if blocked_on_failure else "fail"
        reason = None if result.returncode == 0 else _compact_failure_reason(result)
        metrics = _metrics_for_step(name, output_path)
        return StepResult(
            name=name,
            status=status,
            command=command,
            duration_ms=duration_ms,
            output_path=str(output_path),
            key_metrics=metrics,
            failure_reason=reason,
        )


def main() -> int:
    args = _parse_args()
    repo_root = Path(args.repo_root).resolve() if args.repo_root else _repo_root_from_script()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    _ensure_output_tree(output_dir, include_case_c=args.llm_case_c != "skip")

    run_id = f"f025-{uuid.uuid4().hex[:8]}"
    started_at = _utc_now()
    runner = DemoValidationRunner(repo_root=repo_root, output_dir=output_dir, timeout_ms=args.timeout_ms)
    steps: list[StepResult] = []
    commands: list[dict[str, Any]] = []
    case_c_summary: dict[str, Any] | None = None

    env_step, environment = environment_precheck(repo_root, output_dir / "environment")
    steps.append(env_step)
    corpus_step, corpus = check_f024_corpus(repo_root, Path(args.f024_corpus_dir) if args.f024_corpus_dir else None)
    steps.append(corpus_step)

    if args.mode in {"quick", "full"}:
        focused = runner.run_command_step(
            "focused-tests",
            _focused_tests_command(args.focused_basetemp),
            output_dir / "focused-tests",
        )
        steps.append(focused)
        commands.append({"name": focused.name, "command": focused.command})

        golden = runner.run_command_step(
            "golden-eval",
            [
                sys.executable,
                str(repo_root / "ScienceClaw" / "backend" / "scripts" / "research_golden_eval.py"),
                "--cases",
                str(repo_root / "docs" / "evals" / "research_golden_cases.json"),
                "--payload-dir",
                str(repo_root / "docs" / "evals" / "payloads"),
                "--output-dir",
                str(output_dir / "golden-eval"),
            ],
            output_dir / "golden-eval",
        )
        steps.append(golden)
        commands.append({"name": golden.name, "command": golden.command})

    if args.mode in {"live", "full"}:
        health = live_health_step(args.frontend_url, args.api_base_url, output_dir / "live-ui-smoke")
        steps.append(health)

        smoke = runner.run_command_step(
            "live-ui-smoke",
            [
                sys.executable,
                str(repo_root / "ScienceClaw" / "backend" / "scripts" / "research_ui_e2e.py"),
                "--frontend-url",
                args.frontend_url,
                "--api-base-url",
                args.api_base_url,
                "--output-dir",
                str(output_dir / "live-ui-smoke"),
                "--timeout-ms",
                str(args.timeout_ms),
            ],
            output_dir / "live-ui-smoke",
            blocked_on_failure=args.require_live_ui,
        )
        steps.append(smoke)
        commands.append({"name": smoke.name, "command": smoke.command})

        case_c_step, case_c_summary = run_case_c(args, runner, repo_root, output_dir)
        steps.append(case_c_step)
        if case_c_step.command:
            commands.append({"name": case_c_step.name, "command": case_c_step.command})

        case_d = runner.run_command_step(
            "case-d-literature-review-7paper",
            [
                sys.executable,
                str(repo_root / "ScienceClaw" / "backend" / "scripts" / "research_ui_e2e.py"),
                "--frontend-url",
                args.frontend_url,
                "--api-base-url",
                args.api_base_url,
                "--literature-review",
                "--paper-dir",
                str((Path(args.f024_corpus_dir) if args.f024_corpus_dir else repo_root / "paper_data" / "f024_7paper_corpus").resolve()),
                "--min-paper-count",
                "7",
                "--question",
                "Build a literature review across these papers. Compare the main methods, evidence strength, agreements, disagreements, limitations, and open research gaps. Include an evidence matrix.",
                "--output-dir",
                str(output_dir / "case-d-literature-review-7paper"),
                "--timeout-ms",
                str(args.timeout_ms),
            ],
            output_dir / "case-d-literature-review-7paper",
            blocked_on_failure=args.require_7paper_review,
        )
        steps.append(case_d)
        commands.append({"name": case_d.name, "command": case_d.command})

    completed_at = _utc_now()
    results = build_results(
        run_id=run_id,
        mode=args.mode,
        started_at=started_at,
        completed_at=completed_at,
        steps=steps,
        frontend_url=args.frontend_url,
        api_base_url=args.api_base_url,
        corpus=corpus,
        environment=environment,
        llm_case_c_policy=args.llm_case_c,
        case_c=case_c_summary,
    )
    write_outputs(output_dir, results, commands=commands, environment=environment)
    print(f"F025 demo validation summary: {output_dir / 'summary.md'}")
    print(f"overall_status={results['overall_status']}")
    return 0 if results["overall_status"] in {"pass", "partial"} else 1


def run_subprocess_command(command: list[str], cwd: Path, timeout_ms: int, output_dir: Path) -> CommandResult:
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            check=False,
            capture_output=True,
            text=True,
            timeout=max(1, timeout_ms / 1000),
        )
        return CommandResult(completed.returncode, completed.stdout or "", completed.stderr or "")
    except subprocess.TimeoutExpired as exc:
        return CommandResult(124, exc.stdout or "", f"Timed out after {timeout_ms} ms\n{exc.stderr or ''}")


def environment_precheck(repo_root: Path, output_path: Path) -> tuple[StepResult, dict[str, Any]]:
    output_path.mkdir(parents=True, exist_ok=True)
    environment = {
        "python": sys.version,
        "executable": sys.executable,
        "platform": platform.platform(),
        "repo_root": str(repo_root),
        "pythonpath": os.environ.get("PYTHONPATH", ""),
        "required_paths": {
            "golden_cases": str(repo_root / "docs" / "evals" / "research_golden_cases.json"),
            "research_golden_eval": str(repo_root / "ScienceClaw" / "backend" / "scripts" / "research_golden_eval.py"),
            "research_ui_e2e": str(repo_root / "ScienceClaw" / "backend" / "scripts" / "research_ui_e2e.py"),
        },
    }
    missing = [path for path in environment["required_paths"].values() if not Path(path).exists()]
    (output_path / "environment.json").write_text(json.dumps(environment, ensure_ascii=False, indent=2), encoding="utf-8")
    return (
        StepResult(
            name="environment-precheck",
            status="fail" if missing else "pass",
            output_path=str(output_path),
            key_metrics={"missing_required_paths": missing},
            failure_reason=f"Missing required paths: {missing}" if missing else None,
        ),
        environment,
    )


def check_f024_corpus(repo_root: Path, corpus_dir: Path | None = None) -> tuple[StepResult, dict[str, Any]]:
    corpus_path = (corpus_dir or repo_root / "paper_data" / "f024_7paper_corpus").resolve()
    manifest_path = corpus_path / "manifest.json"
    pdfs = sorted(corpus_path.glob("*.pdf")) if corpus_path.exists() else []
    manifest: dict[str, Any] = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    papers = manifest.get("papers") if isinstance(manifest.get("papers"), list) else []
    source_urls = [paper.get("source_url") for paper in papers if isinstance(paper, Mapping) and paper.get("source_url")]
    corpus = {
        "f024_corpus_path": str(corpus_path),
        "paper_count": len(pdfs),
        "manifest_path": str(manifest_path),
        "source_urls": source_urls,
    }
    reason = None
    if not corpus_path.is_dir():
        reason = f"F024 corpus directory missing: {corpus_path}"
    elif not manifest_path.is_file():
        reason = f"F024 manifest missing: {manifest_path}"
    elif len(pdfs) < 7:
        reason = f"F024 corpus requires at least 7 PDFs, found {len(pdfs)}."
    elif len(papers) < 7:
        reason = f"F024 manifest requires at least 7 papers, found {len(papers)}."
    return (
        StepResult(
            name="corpus-fixture-check",
            status="fail" if reason else "pass",
            output_path=str(corpus_path),
            key_metrics={"paper_count": len(pdfs), "manifest_paper_count": len(papers)},
            failure_reason=reason,
        ),
        corpus,
    )


def live_health_step(frontend_url: str, api_base_url: str, output_path: Path) -> StepResult:
    output_path.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    status = "pass"
    reason = None
    metrics: dict[str, Any] = {"frontend_url": frontend_url, "api_base_url": api_base_url}
    try:
        request = Request(f"{api_base_url.rstrip('/')}/auth/status", headers={"User-Agent": "research-demo-validation"})
        with urlopen(request, timeout=10) as response:
            metrics["health_status"] = response.status
            if response.status >= 400:
                status = "blocked"
                reason = f"Health check returned HTTP {response.status}"
    except Exception as exc:
        status = "blocked"
        reason = str(exc)
        metrics["health_status"] = "unavailable"
    return StepResult(
        name="live-ui-health-check",
        status=status,  # type: ignore[arg-type]
        command=["GET", f"{api_base_url.rstrip('/')}/auth/status"],
        duration_ms=int((time.perf_counter() - started) * 1000),
        output_path=str(output_path),
        key_metrics=metrics,
        failure_reason=reason,
    )


def run_case_c(
    args: argparse.Namespace,
    runner: DemoValidationRunner,
    repo_root: Path,
    output_dir: Path,
) -> tuple[StepResult, dict[str, Any] | None]:
    case_c_dir = output_dir / "case-c-semantic-auditor"
    if args.llm_case_c == "skip":
        return (
            StepResult(
                name="case-c-semantic-auditor",
                status="skipped",
                output_path=str(case_c_dir),
                failure_reason="--llm-case-c=skip; live LLM semantic auditor not verified.",
            ),
            {"status": "skipped", "failure_reason": "--llm-case-c=skip"},
        )
    if args.reuse_existing_llm_artifact:
        return reuse_llm_artifact_step(Path(args.reuse_existing_llm_artifact))
    command = [
        sys.executable,
        str(repo_root / "ScienceClaw" / "backend" / "scripts" / "research_ui_e2e.py"),
        "--frontend-url",
        args.frontend_url,
        "--api-base-url",
        args.api_base_url,
        "--paper-path",
        str(repo_root / "paper_data" / "Space-Time_Beamforming_for_LEO_Satellite_Communications_Enabling_Extremely_Narrow_Beams(1).pdf"),
        "--question",
        "Do these LEO beamforming papers prove clinical safety outcomes for medical patients?",
        "--semantic-overreach",
        "--output-dir",
        str(case_c_dir),
        "--timeout-ms",
        str(args.timeout_ms),
    ]
    step = runner.run_command_step(
        "case-c-semantic-auditor",
        command,
        case_c_dir,
        blocked_on_failure=args.llm_case_c in {"optional", "required"},
    )
    case_c = parse_case_c(case_c_dir)
    if step.status == "blocked" and args.llm_case_c == "required":
        step.failure_reason = step.failure_reason or "Required LLM Case C blocked."
    return step, case_c


def reuse_llm_artifact_step(artifact_dir: Path) -> tuple[StepResult, dict[str, Any]]:
    case_c = parse_case_c(artifact_dir)
    mode = case_c.get("semantic_auditor_mode")
    status: StepStatus = "pass" if mode == "llm_enhanced" else "blocked"
    case_c["status"] = status
    case_c.setdefault("artifact_paths", {})["reused_results_path"] = str((artifact_dir / "results.json").resolve())
    return (
        StepResult(
            name="case-c-semantic-auditor",
            status=status,
            command=[],
            output_path=str(artifact_dir),
            key_metrics={"semantic_auditor_mode": mode, "session_id": case_c.get("session_id")},
            failure_reason=None if status == "pass" else f"Reused artifact is not llm_enhanced: {mode}",
        ),
        case_c,
    )


def parse_case_c(output_path: Path) -> dict[str, Any]:
    results = _read_json(output_path / "results.json")
    answer_path = output_path / "case-c-answer.json"
    artifact_paths = results.get("artifact_paths") if isinstance(results.get("artifact_paths"), dict) else {}
    if not answer_path.exists() and artifact_paths.get("answer_payload_path"):
        answer_path = Path(str(artifact_paths["answer_payload_path"]))
    answer = _read_json(answer_path)
    auditor = ((answer.get("audit") or {}).get("semantic_auditor") or {}) if isinstance(answer, Mapping) else {}
    claims = ((answer.get("audit") or {}).get("claims") or []) if isinstance(answer, Mapping) else []
    return {
        "status": "pass" if auditor.get("mode") == "llm_enhanced" else "blocked",
        "session_id": results.get("session_id"),
        "semantic_auditor_mode": auditor.get("mode"),
        "model": auditor.get("model"),
        "finding_codes": sorted({claim.get("finding_code") for claim in claims if isinstance(claim, Mapping) and claim.get("finding_code")}),
        "artifact_paths": {
            "results_path": str((output_path / "results.json").resolve()),
            "answer_path": str(answer_path.resolve()) if answer_path.exists() else "",
        },
    }


def parse_case_d(output_path: Path) -> dict[str, Any]:
    results = _read_json(output_path / "results.json")
    metrics = results.get("evidence_matrix_metrics") if isinstance(results.get("evidence_matrix_metrics"), dict) else {}
    artifacts = results.get("artifact_paths") if isinstance(results.get("artifact_paths"), dict) else {}
    quality = results.get("quality_reports") if isinstance(results.get("quality_reports"), dict) else {}
    return {
        "status": "pass" if (quality.get("literature_review") or {}).get("passed") else "fail",
        "session_id": results.get("session_id"),
        "paper_count": metrics.get("paper_count", 0),
        "theme_count": metrics.get("theme_count", 0),
        "linked_cell_count": metrics.get("linked_cell_count", 0),
        "citation_count": results.get("citation_count", 0),
        "report_artifact_path": artifacts.get("literature_review_path") or artifacts.get("report_payload_path"),
        "matrix_artifact_path": artifacts.get("evidence_matrix_path"),
    }


def build_results(
    *,
    run_id: str,
    mode: str,
    started_at: str,
    completed_at: str,
    steps: list[StepResult],
    frontend_url: str = "",
    api_base_url: str = "",
    corpus: dict[str, Any] | None = None,
    environment: dict[str, Any] | None = None,
    golden_eval: dict[str, Any] | None = None,
    llm_case_c_policy: str = "optional",
    case_c: dict[str, Any] | None = None,
) -> dict[str, Any]:
    golden = golden_eval or _golden_eval_from_steps(steps)
    live_ui_step = _find_step(steps, "live-ui-health-check")
    case_c_step = _find_step(steps, "case-c-semantic-auditor")
    case_d_step = _find_step(steps, "case-d-literature-review-7paper")
    result = {
        "run_id": run_id,
        "started_at": started_at,
        "completed_at": completed_at,
        "mode": mode,
        "overall_status": _overall_status(steps, llm_case_c_policy=llm_case_c_policy),
        "steps": [step.to_dict() for step in steps],
        "golden_eval": golden,
        "focused_tests": _focused_tests_from_steps(steps),
        "live_ui": {
            "frontend_url": frontend_url,
            "api_base_url": api_base_url,
            "health_status": (live_ui_step.key_metrics.get("health_status") if live_ui_step else "not_run"),
        },
        "case_c": case_c
        or {
            "status": case_c_step.status if case_c_step else "skipped",
            **(case_c_step.key_metrics if case_c_step else {}),
            "failure_reason": case_c_step.failure_reason if case_c_step else "not run",
        },
        "case_d": parse_case_d(Path(case_d_step.output_path)) if case_d_step and Path(case_d_step.output_path, "results.json").exists() else {"status": case_d_step.status if case_d_step else "skipped"},
        "corpus": corpus or {},
        "environment": environment or {},
    }
    return result


def write_outputs(output_dir: Path, results: dict[str, Any], *, commands: list[dict[str, Any]], environment: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "commands.json").write_text(json.dumps(commands, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "environment.json").write_text(json.dumps(environment, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "summary.md").write_text(render_summary(results, commands), encoding="utf-8")


def render_summary(results: dict[str, Any], commands: list[dict[str, Any]]) -> str:
    case_c = results.get("case_c") or {}
    case_d = results.get("case_d") or {}
    golden = results.get("golden_eval") or {}
    golden_passed = golden.get("failed", golden.get("failed_count", 0)) == 0 if golden else None
    lines = [
        "# F025 Reproducible Demo Validation Summary",
        "",
        f"- Overall: `{results.get('overall_status')}`",
        f"- Mode: `{results.get('mode')}`",
        f"- Golden eval: `{golden_passed}` ({golden.get('passed_count', golden.get('passed', 0))}/{golden.get('case_count', '?')})",
        f"- Case C LLM semantic auditor: `{case_c.get('status')}` mode=`{case_c.get('semantic_auditor_mode')}`",
        f"- Case D 7-paper review: `{case_d.get('status')}` session=`{case_d.get('session_id')}` papers={case_d.get('paper_count', 0)} themes={case_d.get('theme_count', 0)} linked_cells={case_d.get('linked_cell_count', 0)}",
        "",
        "## Core Capability Coverage",
        "",
        "- citation-grounded QA",
        "- insufficient evidence refusal",
        "- semantic mismatch / overreach",
        "- LLM semantic auditor",
        "- 7-paper Evidence Matrix Literature Review",
        "",
        "## Commands",
        "",
    ]
    for command in commands:
        lines.append(f"- `{command.get('name')}`: `{' '.join(str(part) for part in command.get('command', []))}`")
    lines.extend(["", "## Key Artifacts", ""])
    lines.append("- `results.json`")
    lines.append("- `commands.json`")
    lines.append("- `environment.json`")
    for step in results.get("steps", []):
        if step.get("output_path"):
            lines.append(f"- `{step.get('name')}`: `{step.get('output_path')}`")
    skipped_or_blocked = [
        step for step in results.get("steps", []) if step.get("status") in {"skipped", "blocked"} or step.get("failure_reason")
    ]
    if skipped_or_blocked:
        lines.extend(["", "## Skipped / Blocked / Failed", ""])
        for step in skipped_or_blocked:
            lines.append(f"- `{step.get('name')}`: `{step.get('status')}` - {step.get('failure_reason') or 'see step output'}")
    return "\n".join(lines).rstrip() + "\n"


def _metrics_for_step(name: str, output_path: Path) -> dict[str, Any]:
    if name == "golden-eval":
        return _golden_metrics(output_path)
    if name == "case-c-semantic-auditor":
        return {key: value for key, value in parse_case_c(output_path).items() if key != "artifact_paths"} if (output_path / "results.json").exists() else {}
    if name == "case-d-literature-review-7paper":
        return parse_case_d(output_path) if (output_path / "results.json").exists() else {}
    if name == "live-ui-smoke" and (output_path / "results.json").exists():
        data = _read_json(output_path / "results.json")
        return {"session_id": data.get("session_id"), "citation_count": data.get("citation_count")}
    return {}


def _golden_metrics(output_path: Path) -> dict[str, Any]:
    data = _read_json(output_path / "results.json")
    return {
        "case_count": data.get("case_count", 0),
        "passed": data.get("passed_count", 0),
        "failed": data.get("failed_count", 0),
    }


def _golden_eval_from_steps(steps: list[StepResult]) -> dict[str, Any]:
    step = _find_step(steps, "golden-eval")
    metrics = step.key_metrics if step else {}
    return {
        "case_count": metrics.get("case_count", 0),
        "passed": metrics.get("passed", 0),
        "failed": metrics.get("failed", 0),
        "passed_count": metrics.get("passed", 0),
        "failed_count": metrics.get("failed", 0),
    }


def _focused_tests_from_steps(steps: list[StepResult]) -> dict[str, Any]:
    step = _find_step(steps, "focused-tests")
    if not step:
        return {"passed": None, "failed": None}
    text = ""
    stdout_path = Path(step.output_path) / "stdout.txt"
    if stdout_path.exists():
        text = stdout_path.read_text(encoding="utf-8", errors="replace")
    return {"passed": _parse_pytest_count(text, "passed"), "failed": _parse_pytest_count(text, "failed")}


def _parse_pytest_count(text: str, label: str) -> int | None:
    import re

    match = re.search(rf"(\d+)\s+{label}", text)
    return int(match.group(1)) if match else None


def _overall_status(steps: list[StepResult], *, llm_case_c_policy: str) -> OverallStatus:
    if any(step.status == "fail" for step in steps):
        return "fail"
    blocked_steps = [step for step in steps if step.status == "blocked"]
    if blocked_steps:
        if any(step.name != "case-c-semantic-auditor" for step in blocked_steps):
            return "blocked"
        if llm_case_c_policy == "optional":
            return "partial"
        return "blocked"
    return "pass"


def _find_step(steps: list[StepResult], name: str) -> StepResult | None:
    return next((step for step in steps if step.name == name), None)


def _compact_failure_reason(result: CommandResult) -> str:
    combined = "\n".join(part for part in [result.stderr, result.stdout] if part).strip()
    return combined[-2000:] if combined else f"Command exited with {result.returncode}"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _focused_tests_command(basetemp: str | None) -> list[str]:
    return [
        sys.executable,
        "-m",
        "pytest",
        str(Path("ScienceClaw") / "backend" / "tests"),
        "-k",
        "research_golden_eval or research_ui_e2e_script or demo_validation or research_evaluation",
        "-q",
        "--basetemp",
        basetemp or str(Path(".pytest_tmp") / "f025-focused"),
    ]


def _ensure_output_tree(output_dir: Path, *, include_case_c: bool) -> None:
    for name in [
        "golden-eval",
        "focused-tests",
        "live-ui-smoke",
        "case-d-literature-review-7paper",
        "artifacts",
    ]:
        (output_dir / name).mkdir(parents=True, exist_ok=True)
    if include_case_c:
        (output_dir / "case-c-semantic-auditor").mkdir(parents=True, exist_ok=True)


def _repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[3]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run F025 one-command Research Assistant demo validation chain.")
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--frontend-url", default="http://127.0.0.1:5180")
    parser.add_argument("--api-base-url", default="http://127.0.0.1:5180/api/v1")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--mode", choices=("quick", "live", "full"), default="quick")
    parser.add_argument("--require-live-ui", action="store_true")
    parser.add_argument("--require-7paper-review", action="store_true")
    parser.add_argument("--llm-case-c", choices=("required", "optional", "skip"), default="optional")
    parser.add_argument("--reuse-existing-llm-artifact", default=None)
    parser.add_argument("--timeout-ms", type=int, default=600_000)
    parser.add_argument("--f024-corpus-dir", default=None)
    parser.add_argument("--focused-basetemp", default=None)
    return parser.parse_args()


if __name__ == "__main__":
    sys.exit(main())
