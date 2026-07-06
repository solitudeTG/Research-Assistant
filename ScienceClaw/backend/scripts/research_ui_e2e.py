from __future__ import annotations

import argparse
import asyncio
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin

import httpx

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
    answer_payload: dict | None = None
    report_payload: dict | None = None


def build_api_base_url(frontend_url: str) -> str:
    return f"{frontend_url.rstrip('/')}/api/v1"


def assert_research_ui_loop(result: ResearchUiE2EResult) -> None:
    if result.session_status != "completed":
        raise AssertionError(f"Research UI session did not complete: {result.session_status!r}")
    if result.error_events:
        raise AssertionError(f"Research UI loop produced error events: {result.error_events!r}")
    if result.citation_count < 1:
        raise AssertionError("Research UI loop did not render citation evidence")

    visible_steps = "\n".join(result.activity_steps)
    for step in REQUIRED_ACTIVITY_STEPS:
        if step not in visible_steps:
            raise AssertionError(f"Research UI loop did not show ActivityPanel step: {step}")

    if not any(name.endswith(".md") for name in result.round_files):
        raise AssertionError("Research UI loop did not expose a Markdown report file")
    if not any(name.endswith(".evidence.json") for name in result.round_files):
        raise AssertionError("Research UI loop did not expose an evidence map file")


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
        pdf_path = Path(tmp) / "ui-file-picker-evidence-boundaries.pdf"
        _write_smoke_pdf(pdf_path)
        result = _run_browser_loop(
            frontend_url=frontend_url,
            api_base_url=api_base_url,
            username=args.username,
            password=args.password,
            question=args.question,
            pdf_path=pdf_path,
            headed=args.headed,
            timeout_ms=args.timeout_ms,
        )

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
    pdf_path: Path,
    headed: bool,
    timeout_ms: int,
) -> ResearchUiE2EResult:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        _log("launching browser")
        browser = playwright.chromium.launch(headless=not headed)
        page = browser.new_page()
        page.set_default_timeout(timeout_ms)
        try:
            _log("logging in")
            page.goto(f"{frontend_url}/login")
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
            page.goto(f"{frontend_url}/chat/{session_id}")
            page.locator("textarea").wait_for(timeout=timeout_ms)
            _log("uploading PDF through UI file input")
            page.locator("input[type='file']").set_input_files(str(pdf_path))
            _log("waiting for paper indexing")
            status = _wait_for_research_status(api_base_url, session_id, page, timeout_ms)

            _log("reloading session to restore Research mode")
            page.reload(wait_until="domcontentloaded")
            _dismiss_open_dialogs(page)
            page.locator("body").wait_for(timeout=timeout_ms)
            _log("requesting paper-grounded research answer")
            answer_response = _api_request(
                page,
                "POST",
                f"{api_base_url}/sessions/{session_id}/research/answer",
                {"question": question, "limit": 5},
            )
            answer_payload = answer_response.get("data") or {}
            citation_count = len(answer_payload.get("citations") or [])

            _log("generating Markdown research report")
            report_response = _api_request(
                page,
                "POST",
                f"{api_base_url}/sessions/{session_id}/research/report",
                {"question": question, "limit": 5},
            )
            _wait_for_report_files(api_base_url, session_id, page, timeout_ms)

            _log("collecting trace and file evidence")
            activity_steps = _load_activity_steps(api_base_url, session_id, page)
            round_files = _load_round_files(api_base_url, session_id, page)
            error_events = _load_error_events(api_base_url, session_id, page)

            return ResearchUiE2EResult(
                session_id=session_id,
                session_status=status,
                citation_count=citation_count,
                activity_steps=activity_steps,
                round_files=round_files,
                error_events=error_events,
                answer_payload=answer_payload,
                report_payload=report_response.get("data"),
            )
        finally:
            browser.close()


def _wait_for_research_status(api_base_url: str, session_id: str, page, timeout_ms: int) -> str:
    deadline = page.evaluate("Date.now()") + timeout_ms
    status = "unknown"
    while page.evaluate("Date.now()") < deadline:
        status_payload = _api_get(page, f"{api_base_url}/sessions/{session_id}/research/status")
        data = status_payload.get("data") or {}
        papers = data.get("papers") or []
        if (
            data.get("has_indexed_papers")
            or data.get("indexed_paper_count", 0) >= 1
            or any(paper.get("status") == "indexed" for paper in papers)
        ):
            detail = _api_get(page, f"{api_base_url}/sessions/{session_id}")
            status = (detail.get("data") or {}).get("status", "unknown")
            return status
        page.wait_for_timeout(1000)
    return status


def _ensure_research_mode(page, timeout_ms: int) -> None:
    toggle = page.locator("button[title='Paper evidence mode'], button[title='General agent mode']")
    toggle.wait_for(timeout=timeout_ms)
    title = toggle.first.get_attribute("title")
    if title == "General agent mode":
        toggle.first.click()
        page.locator("button[title='Paper evidence mode']").wait_for(timeout=timeout_ms)


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
