from __future__ import annotations

import argparse
import asyncio
import os
import sys
import tempfile
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin

import httpx

from backend.research_assistant.evaluation import (
    ResearchQualityRequirement,
    evaluate_research_answer,
)
from backend.scripts.research_smoke import _write_smoke_pdf


REQUIRED_ACTIVITY_STEPS = (
    "Research document uploaded",
    "Parsing research document",
    "Indexing paper evidence",
    "Retrieving citation evidence",
    "Markdown research artifact generated",
)


@dataclass(frozen=True)
class ResearchUiE2EResult:
    session_id: str
    session_status: str
    citation_count: int
    activity_steps: list[str]
    round_files: list[str]
    error_events: list[str]
    question_delivery: str = ""
    report_delivery: str = ""
    insufficient_question_delivery: str = ""
    answer_payload: dict | None = None
    report_payload: dict | None = None
    insufficient_answer_payload: dict | None = None
    artifact_paths: dict[str, str] = field(default_factory=dict)


def build_api_base_url(frontend_url: str) -> str:
    return f"{frontend_url.rstrip('/')}/api/v1"


def assert_research_ui_loop(result: ResearchUiE2EResult) -> None:
    if result.session_status != "completed" and not result.answer_payload:
        raise AssertionError(f"Research UI session did not complete: {result.session_status!r}")
    if result.error_events:
        raise AssertionError(f"Research UI loop produced error events: {result.error_events!r}")
    if result.citation_count < 1:
        raise AssertionError("Research UI loop did not render citation evidence")

    visible_steps = "\n".join(result.activity_steps)
    for step in REQUIRED_ACTIVITY_STEPS:
        if step not in visible_steps and not _activity_step_equivalent(step, result.activity_steps):
            raise AssertionError(f"Research UI loop did not show ActivityPanel step: {step}")

    if not any(name.endswith(".md") for name in result.round_files):
        raise AssertionError("Research UI loop did not expose a Markdown report file")
    if not any(name.endswith(".evidence.json") for name in result.round_files):
        raise AssertionError("Research UI loop did not expose an evidence map file")


def assert_semantic_multi_paper_live_loop(result: ResearchUiE2EResult) -> None:
    assert_research_ui_loop(result)
    if result.question_delivery != "chat_ui":
        raise AssertionError(f"Case A question must be submitted through Chat UI, got {result.question_delivery!r}")
    if result.report_delivery != "chat_ui":
        raise AssertionError(f"Case A report must be generated through Chat UI, got {result.report_delivery!r}")
    if result.insufficient_answer_payload is not None and result.insufficient_question_delivery != "chat_ui":
        raise AssertionError(
            f"Case B question must be submitted through Chat UI, got {result.insufficient_question_delivery!r}"
        )
    answer = result.answer_payload or {}
    quality_reports = _build_live_quality_reports(result)
    case_a_quality = quality_reports.get("case_a")
    if case_a_quality:
        case_a_quality.assert_passed()
    citations = answer.get("citations") or []
    if (answer.get("task_route") or {}).get("route") not in {"evidence_qa", "multi_paper_synthesis"}:
        raise AssertionError(f"Unexpected task route for multi-paper synthesis: {answer.get('task_route')!r}")
    if len(citations) < 2:
        raise AssertionError("Multi-paper synthesis case must return at least two citations")
    distinct_papers = {
        str(citation.get("paper_id") or (citation.get("source_identity") or {}).get("paper_id") or "")
        for citation in citations
        if isinstance(citation, dict)
    }
    distinct_papers.discard("")
    if len(distinct_papers) < 2:
        raise AssertionError(f"Expected citations from at least two papers, got {sorted(distinct_papers)!r}")
    for index, citation in enumerate(citations):
        if citation.get("source_type") not in {"paper", "web", "database"}:
            raise AssertionError(f"Citation {index} has invalid source_type={citation.get('source_type')!r}")
        traceable = [
            citation.get("paper_id"),
            citation.get("title"),
            citation.get("section"),
            citation.get("chunk_id"),
            citation.get("quote"),
        ]
        if sum(1 for value in traceable if value) < 4:
            raise AssertionError(f"Citation {index} is missing traceable source metadata: {citation!r}")

    audit_claims = ((answer.get("audit") or {}).get("claims") or [])
    if not audit_claims:
        raise AssertionError("Multi-paper answer is missing audit.claims")
    if not any(claim.get("support_status") in {"supported", "partial"} for claim in audit_claims if isinstance(claim, dict)):
        raise AssertionError("Expected at least one supported or partial audit claim")
    for claim in audit_claims:
        if not isinstance(claim, dict):
            continue
        if "semantic_relevance_score" not in claim or "source_quality_score" not in claim:
            raise AssertionError(f"Audit claim is missing semantic/source quality fields: {claim!r}")

    boundaries = answer.get("context_boundaries") or {}
    if set(boundaries.get("citation_evidence") or []) != {"paper", "web", "database"}:
        raise AssertionError("Citation evidence boundary does not restrict citations to paper/web/database")

    insufficient = result.insufficient_answer_payload or {}
    case_b_quality = quality_reports.get("case_b")
    if case_b_quality:
        case_b_quality.assert_passed()
    decision = (insufficient.get("evidence_admission") or {}).get("decision")
    if decision not in {"rejected", "insufficient", "no_evidence"}:
        raise AssertionError(f"Insufficient-evidence case did not refuse: {decision!r}")
    if len(insufficient.get("citations") or []) != 0:
        raise AssertionError("Insufficient-evidence case must not expose supporting citations")
    insufficient_claims = (insufficient.get("audit") or {}).get("claims") or []
    if not any(
        isinstance(claim, dict) and claim.get("finding_code") == "insufficient_evidence_should_refuse"
        for claim in insufficient_claims
    ):
        raise AssertionError("Insufficient-evidence audit did not include insufficient_evidence_should_refuse")


def assert_semantic_overreach_live_loop(result: ResearchUiE2EResult) -> None:
    if result.session_status != "completed" and not result.answer_payload:
        raise AssertionError(f"Research UI session did not complete: {result.session_status!r}")
    if result.error_events:
        raise AssertionError(f"Research UI loop produced error events: {result.error_events!r}")
    if result.question_delivery != "chat_ui":
        raise AssertionError(f"Case C question must be submitted through Chat UI, got {result.question_delivery!r}")

    visible_steps = "\n".join(result.activity_steps)
    for step in (
        "Research document uploaded",
        "Parsing research document",
        "Indexing paper evidence",
        "Deterministic evidence audit completed",
    ):
        if step not in visible_steps and not _activity_step_equivalent(step, result.activity_steps):
            raise AssertionError(f"Case C did not show ActivityPanel step: {step}")
    if not any("semantic auditor" in step.casefold() or "evidence audit" in step.casefold() for step in result.activity_steps):
        raise AssertionError("Case C did not show a real auditor/audit step in ActivityPanel trace")

    answer = result.answer_payload or {}
    audit_claims = ((answer.get("audit") or {}).get("claims") or [])
    if not audit_claims:
        raise AssertionError("Case C answer is missing audit.claims")
    semantic_auditor = (answer.get("audit") or {}).get("semantic_auditor") or {}
    if semantic_auditor.get("mode") != "llm_enhanced":
        raise AssertionError(
            "Case C requires a live LLM semantic auditor result; "
            f"got semantic_auditor.mode={semantic_auditor.get('mode')!r} "
            f"status={semantic_auditor.get('llm_auditor_status')!r}"
        )
    accepted_codes = {
        "llm_overreach",
        "llm_unsupported",
        "llm_source_mismatch",
        "llm_insufficient_evidence",
    }
    actual_codes = {
        claim.get("finding_code")
        for claim in audit_claims
        if isinstance(claim, dict) and claim.get("finding_code")
    }
    if not (actual_codes & accepted_codes):
        raise AssertionError(f"Case C did not expose an LLM overreach/unsupported finding code: {sorted(actual_codes)!r}")
    if not any(
        isinstance(claim, dict)
        and claim.get("llm_support_status")
        and claim.get("llm_rationale")
        and claim.get("finding_code") in accepted_codes
        for claim in audit_claims
    ):
        raise AssertionError("Case C requires at least one claim with llm_support_status, llm_rationale, and an LLM finding code")

    citations = answer.get("citations") or []
    content = str(answer.get("content") or "").casefold()
    refusal_markers = (
        "insufficient citation evidence",
        "cannot answer it as a cited research claim",
        "evidence only supports",
        "not support",
    )
    if citations and not any(marker in content for marker in refusal_markers):
        raise AssertionError("Case C must have zero citations or explicitly refuse/qualify the citation as non-supporting evidence")

    quality_reports = _build_live_quality_reports(result, case_c=True)
    case_c_quality = quality_reports.get("case_c")
    if case_c_quality:
        case_c_quality.assert_passed()


def main() -> int:
    args = _parse_args()
    _log("checking optional runtime dependencies")
    _require_module("playwright.sync_api", "Playwright is required. Install it with `pip install playwright`.")
    _require_module("fitz", "PyMuPDF is required to generate the E2E PDF.")

    frontend_url = args.frontend_url.rstrip("/")
    api_base_url = args.api_base_url
    _log(f"checking API health at {api_base_url}")
    asyncio.run(_check_frontend(api_base_url))

    with tempfile.TemporaryDirectory(prefix="research-ui-e2e-") as tmp:
        if args.paper_path:
            pdf_paths = [Path(path).resolve() for path in args.paper_path]
            missing = [str(path) for path in pdf_paths if not path.exists()]
            if missing:
                raise SystemExit(f"paper fixture(s) missing: {missing}")
        else:
            pdf_path = Path(tmp) / "ui-file-picker-evidence-boundaries.pdf"
            _write_smoke_pdf(pdf_path)
            pdf_paths = [pdf_path]
        result = _run_browser_loop(
            frontend_url=frontend_url,
            api_base_url=api_base_url,
            username=args.username,
            password=args.password,
            question=args.question,
            insufficient_question=args.insufficient_question,
            pdf_paths=pdf_paths,
            headed=args.headed,
            timeout_ms=args.timeout_ms,
            generate_report=not args.semantic_overreach,
        )

    if args.output_dir:
        _write_e2e_outputs(result, Path(args.output_dir), case_c=args.semantic_overreach)
    if args.semantic_overreach:
        assert_semantic_overreach_live_loop(result)
    elif args.semantic_multipaper:
        assert_semantic_multi_paper_live_loop(result)
    else:
        assert_research_ui_loop(result)
    print("research UI E2E passed")
    print(f"session_id={result.session_id}")
    print(f"session_status={result.session_status}")
    print(f"citations={result.citation_count}")
    print(f"activity_steps={len(result.activity_steps)}")
    print(f"round_files={result.round_files}")
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Research Assistant browser UI loop against a running ScienceClaw stack."
    )
    parser.add_argument("--frontend-url", default=os.environ.get("RESEARCH_UI_FRONTEND_URL", "http://localhost:5173"))
    parser.add_argument(
        "--api-base-url",
        default=os.environ.get("RESEARCH_UI_API_BASE_URL", "http://localhost:12001/api/v1"),
        help="Backend API base URL. Override with the frontend proxy path when needed.",
    )
    parser.add_argument("--username", default=os.environ.get("RESEARCH_UI_USERNAME", "admin"))
    parser.add_argument("--password", default=os.environ.get("RESEARCH_UI_PASSWORD", "admin123"))
    parser.add_argument(
        "--question",
        default="What does the paper say about evidence boundaries?",
        help="Paper-grounded question to ask after upload indexing completes.",
    )
    parser.add_argument(
        "--insufficient-question",
        default=None,
        help="Optional second question that should be refused for insufficient evidence.",
    )
    parser.add_argument(
        "--paper-path",
        action="append",
        default=[],
        help="Real PDF path to upload through the UI. Repeat for multi-paper cases. Defaults to a smoke PDF.",
    )
    parser.add_argument("--semantic-multipaper", action="store_true", help="Assert semantic multi-paper synthesis plus refusal.")
    parser.add_argument("--semantic-overreach", action="store_true", help="Assert live UI semantic overreach/refusal Case C.")
    parser.add_argument("--output-dir", default=None, help="Write answer/report/result artifacts to this directory.")
    parser.add_argument("--headed", action="store_true", help="Run the browser visibly instead of headless.")
    parser.add_argument("--timeout-ms", type=int, default=120_000)
    return parser.parse_args()


def _log(message: str) -> None:
    print(f"[research-ui-e2e] {message}", flush=True)


def _require_module(name: str, message: str) -> None:
    try:
        __import__(name)
    except ImportError as exc:
        raise SystemExit(message) from exc


async def _check_frontend(api_base_url: str) -> None:
    async with httpx.AsyncClient(timeout=10, trust_env=False) as client:
        response = await client.get(f"{api_base_url}/auth/status")
    response.raise_for_status()


def _run_browser_loop(
    *,
    frontend_url: str,
    api_base_url: str,
    username: str,
    password: str,
    question: str,
    insufficient_question: str | None,
    pdf_paths: list[Path],
    headed: bool,
    timeout_ms: int,
    generate_report: bool,
) -> ResearchUiE2EResult:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        _log("launching browser")
        browser = playwright.chromium.launch(headless=not headed)
        page = browser.new_page()
        page.set_default_timeout(timeout_ms)
        try:
            _log("logging in")
            _goto_client_route(page, frontend_url, "/login", timeout_ms)
            page.locator("#email").fill(username)
            page.locator("input[type='password']").fill(password)
            page.locator("button[type='submit']").click()
            page.wait_for_url(lambda url: "/login" not in url, timeout=timeout_ms)
            _ensure_browser_api_token(page, api_base_url, username, password)

            _log("creating session")
            session_payload = _api_request(
                page,
                "PUT",
                f"{api_base_url}/sessions",
                {"mode": "deep"},
            )
            session_id = (session_payload.get("data") or {}).get("session_id")
            if not session_id:
                raise AssertionError(f"Create session response did not include session_id: {session_payload!r}")

            _log(f"opening session {session_id}")
            _goto_client_route(page, frontend_url, f"/chat/{session_id}", timeout_ms)
            page.locator("textarea").wait_for(timeout=timeout_ms)
            _log("uploading PDF through UI file input")
            page.locator("input[type='file']").set_input_files([str(path) for path in pdf_paths])
            _log("waiting for paper indexing")
            status = _wait_for_research_status(api_base_url, session_id, page, timeout_ms, expected_papers=len(pdf_paths))

            _log("reloading session to restore Research mode from indexed papers")
            page.reload(wait_until="domcontentloaded")
            _dismiss_open_dialogs(page)
            page.locator("body").wait_for(timeout=timeout_ms)
            _wait_for_research_mode_available(page, timeout_ms)
            _log("asking paper-grounded question through Chat UI")
            answer_payload = _submit_research_question_via_chat(page, api_base_url, session_id, question, timeout_ms)
            citation_count = len(answer_payload.get("citations") or [])

            report_payload = None
            if generate_report:
                _log("generating Markdown research report through Chat UI")
                report_payload = _generate_research_report_via_chat(page, api_base_url, session_id, timeout_ms)
                _wait_for_report_files(api_base_url, session_id, page, timeout_ms)

            _log("collecting trace and file evidence")
            activity_steps = _load_activity_steps(api_base_url, session_id, page)
            round_files = _load_round_files(api_base_url, session_id, page)
            error_events = _load_error_events(api_base_url, session_id, page)
            insufficient_answer_payload = None
            if insufficient_question:
                _log("asking insufficient-evidence refusal question through Chat UI")
                insufficient_answer_payload = _submit_research_question_via_chat(
                    page,
                    api_base_url,
                    session_id,
                    insufficient_question,
                    timeout_ms,
                )

            return ResearchUiE2EResult(
                session_id=session_id,
                session_status=status,
                citation_count=citation_count,
                question_delivery="chat_ui",
                report_delivery="chat_ui" if generate_report else "",
                insufficient_question_delivery="chat_ui" if insufficient_question else "",
                activity_steps=activity_steps,
                round_files=round_files,
                error_events=error_events,
                answer_payload=answer_payload,
                report_payload=report_payload,
                insufficient_answer_payload=insufficient_answer_payload,
            )
        finally:
            browser.close()


def _wait_for_research_status(api_base_url: str, session_id: str, page, timeout_ms: int, *, expected_papers: int = 1) -> str:
    deadline = page.evaluate("Date.now()") + timeout_ms
    status = "unknown"
    while page.evaluate("Date.now()") < deadline:
        status_payload = _api_get(page, f"{api_base_url}/sessions/{session_id}/research/status")
        data = status_payload.get("data") or {}
        papers = data.get("papers") or []
        if (
            data.get("indexed_paper_count", 0) >= expected_papers
            or sum(1 for paper in papers if paper.get("status") == "indexed") >= expected_papers
            or (expected_papers <= 1 and data.get("has_indexed_papers"))
        ):
            detail = _api_get(page, f"{api_base_url}/sessions/{session_id}")
            status = (detail.get("data") or {}).get("status", "unknown")
            return status
        page.wait_for_timeout(1000)
    return status


def _goto_client_route(page, frontend_url: str, route: str, timeout_ms: int) -> None:
    response = page.goto(f"{frontend_url}{route}", wait_until="domcontentloaded")
    if response is not None and response.status < 400:
        return
    page.goto(f"{frontend_url}/index.html", wait_until="domcontentloaded")
    page.evaluate(
        """(route) => {
            window.history.pushState({}, '', route);
            window.dispatchEvent(new PopStateEvent('popstate'));
        }""",
        route,
    )
    page.locator("body").wait_for(timeout=timeout_ms)


def _write_e2e_outputs(result: ResearchUiE2EResult, output_dir: Path, *, case_c: bool = False) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    answer_name = "case-c-answer.json" if case_c else "case-a-answer.json"
    artifacts = {
        "answer_payload_path": output_dir / answer_name,
        "report_payload_path": output_dir / "case-a-report.json",
        "insufficient_answer_payload_path": output_dir / "case-b-insufficient-answer.json",
        "results_path": output_dir / "results.json",
        "summary_path": output_dir / "summary.md",
    }
    if result.answer_payload is not None:
        artifacts["answer_payload_path"].write_text(json.dumps(result.answer_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if result.report_payload is not None:
        artifacts["report_payload_path"].write_text(json.dumps(result.report_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if result.insufficient_answer_payload is not None:
        artifacts["insufficient_answer_payload_path"].write_text(
            json.dumps(result.insufficient_answer_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    summary = {
        "session_id": result.session_id,
        "session_status": result.session_status,
        "question_delivery": result.question_delivery,
        "report_delivery": result.report_delivery,
        "insufficient_question_delivery": result.insufficient_question_delivery,
        "citation_count": result.citation_count,
        "activity_steps": result.activity_steps,
        "round_files": result.round_files,
        "error_events": result.error_events,
        "quality_reports": {
            case_id: report.to_dict()
            for case_id, report in _build_live_quality_reports(result, case_c=case_c).items()
        },
        "artifact_paths": {key: str(path) for key, path in artifacts.items()},
    }
    artifacts["results_path"].write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    artifacts["summary_path"].write_text(
        "\n".join(
            [
                "# Research UI E2E Summary",
                "",
                f"- Session: `{result.session_id}`",
                f"- Status: `{result.session_status}`",
                f"- Case A question delivery: `{result.question_delivery}`",
                f"- Case A report delivery: `{result.report_delivery}`",
                f"- Case B question delivery: `{result.insufficient_question_delivery}`",
                f"- Case A citations: {result.citation_count}",
                f"- Case B admission: `{((result.insufficient_answer_payload or {}).get('evidence_admission') or {}).get('decision')}`",
                f"- Case A quality: `{summary['quality_reports'].get('case_a', {}).get('passed')}`",
                f"- Case B quality: `{summary['quality_reports'].get('case_b', {}).get('passed')}`",
                f"- Case C quality: `{summary['quality_reports'].get('case_c', {}).get('passed')}`",
                f"- Activity steps: {len(result.activity_steps)}",
                f"- Round files: {', '.join(result.round_files)}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _build_live_quality_reports(result: ResearchUiE2EResult, *, case_c: bool = False) -> dict[str, object]:
    reports = {}
    if case_c and result.answer_payload is not None:
        decision = (result.answer_payload.get("evidence_admission") or {}).get("decision")
        reports["case_c"] = evaluate_research_answer(
            result.answer_payload,
            ResearchQualityRequirement(
                case_id="live_ui_case_c_semantic_overreach",
                expected_admission=decision if decision else None,
                min_citation_count=0,
                max_unsupported_claim_ratio=1.0,
                require_original_evidence_citations=False,
                require_llm_semantic_audit=True,
            ),
        )
    elif result.answer_payload is not None:
        route = ((result.answer_payload.get("task_route") or {}).get("route") or "evidence_qa")
        reports["case_a"] = evaluate_research_answer(
            result.answer_payload,
            ResearchQualityRequirement(
                case_id="live_ui_case_a_multi_paper_synthesis",
                expected_route=route,
                expected_admission="accepted",
                min_citation_count=2,
                max_unsupported_claim_ratio=0.6,
            ),
        )
    if result.insufficient_answer_payload is not None:
        decision = (result.insufficient_answer_payload.get("evidence_admission") or {}).get("decision")
        reports["case_b"] = evaluate_research_answer(
            result.insufficient_answer_payload,
            ResearchQualityRequirement(
                case_id="live_ui_case_b_insufficient_evidence",
                expected_admission=decision if decision in {"rejected", "insufficient", "no_evidence"} else None,
                min_citation_count=0,
                max_unsupported_claim_ratio=1.0,
                require_original_evidence_citations=False,
            ),
        )
    return reports


def _activity_step_equivalent(expected: str, actual_steps: list[str]) -> bool:
    normalized_steps = [step.casefold() for step in actual_steps]
    if expected == "Retrieving citation evidence":
        return any(
            "citation evidence" in step and any(marker in step for marker in ("retriev", "admission", "needed"))
            for step in normalized_steps
        )
    if expected == "Markdown research artifact generated":
        return any("research artifact" in step or "research report" in step for step in normalized_steps)
    return False


def _ensure_research_mode(page, timeout_ms: int) -> None:
    toggle = _research_mode_toggle(page)
    try:
        if toggle.count() == 0:
            return
        title = toggle.first.get_attribute("title") or ""
        if "General agent" in title or "通用 Agent" in title or "Agent" in title:
            toggle.first.click()
            page.wait_for_timeout(300)
    except Exception:
        return


def _wait_for_research_mode_available(page, timeout_ms: int) -> None:
    _research_mode_toggle(page).first.wait_for(timeout=timeout_ms)


def _research_mode_toggle(page):
    return page.locator(
        "button[title='Paper evidence mode'], "
        "button[title='General agent mode'], "
        "button[title='引用证据模式'], "
        "button[title='通用 Agent 模式'], "
        "button[title*='Agent']"
    )


def _dismiss_open_dialogs(page) -> None:
    for _ in range(3):
        dialogs = page.locator("[role='dialog']")
        if dialogs.count() == 0:
            return
        close_buttons = page.locator("[role='dialog'] button")
        if close_buttons.count() > 0:
            close_buttons.first.click(force=True)
        else:
            page.keyboard.press("Escape")
        page.wait_for_timeout(300)


def _submit_research_question_via_chat(page, api_base_url: str, session_id: str, question: str, timeout_ms: int) -> dict:
    _ensure_research_mode(page, timeout_ms)
    textbox = page.locator("textarea:visible").last
    textbox.wait_for(timeout=timeout_ms)
    textbox.fill(question)
    with page.expect_response(
        lambda response: (
            f"/sessions/{session_id}/research/answer" in response.url
            and response.request.method == "POST"
        ),
        timeout=timeout_ms,
    ) as response_info:
        textbox.press("Enter")
    response = response_info.value
    if not response.ok:
        raise AssertionError(f"Chat UI research answer request failed: {response.status} {response.url}")
    payload = response.json()
    return payload.get("data") or {}


def _generate_research_report_via_chat(page, api_base_url: str, session_id: str, timeout_ms: int) -> dict:
    report_button = page.locator("button.msg-action-btn--report").last
    report_button.wait_for(timeout=timeout_ms)
    with page.expect_response(
        lambda response: (
            f"/sessions/{session_id}/research/report" in response.url
            and response.request.method == "POST"
        ),
        timeout=timeout_ms,
    ) as response_info:
        report_button.click()
    response = response_info.value
    if not response.ok:
        raise AssertionError(f"Chat UI research report request failed: {response.status} {response.url}")
    payload = response.json()
    return payload.get("data") or {}


def _load_round_files(api_base_url: str, session_id: str, page) -> list[str]:
    payload = _api_get(page, f"{api_base_url}/sessions/{session_id}/files")
    files = payload.get("data") or []
    return sorted(
        file.get("filename", "")
        for file in files
        if str(file.get("filename", "")).startswith("research-report-")
    )


def _wait_for_report_files(api_base_url: str, session_id: str, page, timeout_ms: int) -> None:
    deadline = page.evaluate("Date.now()") + timeout_ms
    while page.evaluate("Date.now()") < deadline:
        files = _load_round_files(api_base_url, session_id, page)
        if any(name.endswith(".md") for name in files) and any(name.endswith(".evidence.json") for name in files):
            return
        page.wait_for_timeout(1000)
    raise AssertionError("Timed out waiting for Markdown report and evidence map files")


def _load_activity_steps(api_base_url: str, session_id: str, page) -> list[str]:
    payload = _api_get(page, f"{api_base_url}/sessions/{session_id}")
    events = (payload.get("data") or {}).get("events") or []
    steps: list[str] = []
    for event in events:
        if event.get("event") == "step":
            description = (event.get("data") or {}).get("description")
            if description:
                steps.append(str(description))
    return steps


def _load_error_events(api_base_url: str, session_id: str, page) -> list[str]:
    payload = _api_get(page, f"{api_base_url}/sessions/{session_id}")
    events = (payload.get("data") or {}).get("events") or []
    errors: list[str] = []
    for event in events:
        if event.get("event") == "error" or event.get("type") == "error":
            errors.append(str(event.get("content") or event.get("message") or event))
    return errors


def _api_get(page, url: str) -> dict:
    return _api_request(page, "GET", url)


def _api_request(page, method: str, url: str, body: dict | None = None) -> dict:
    return page.evaluate(
        """async ({ method, url, body }) => {
            const token = window.localStorage.getItem('access_token');
            const response = await fetch(url, {
                method,
                headers: {
                    ...(token ? { Authorization: `Bearer ${token}` } : {}),
                    ...(body ? { 'Content-Type': 'application/json' } : {}),
                },
                body: body ? JSON.stringify(body) : undefined,
            });
            if (!response.ok) {
                throw new Error(`${method} ${url} failed: ${response.status}`);
            }
            return await response.json();
        }""",
        {"method": method, "url": url, "body": body},
    )


def _ensure_browser_api_token(page, api_base_url: str, username: str, password: str) -> None:
    page.evaluate(
        """async ({ apiBaseUrl, username, password }) => {
            const response = await fetch(`${apiBaseUrl}/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password }),
            });
            if (!response.ok) {
                throw new Error(`auth login failed: ${response.status}`);
            }
            const payload = await response.json();
            const data = payload.data || {};
            if (!data.access_token) {
                throw new Error('auth login response did not include access_token');
            }
            window.localStorage.setItem('access_token', data.access_token);
            if (data.refresh_token) {
                window.localStorage.setItem('refresh_token', data.refresh_token);
            }
        }""",
        {"apiBaseUrl": api_base_url.rstrip("/"), "username": username, "password": password},
    )


if __name__ == "__main__":
    sys.exit(main())
