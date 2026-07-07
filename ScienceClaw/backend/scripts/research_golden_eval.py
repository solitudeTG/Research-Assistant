from __future__ import annotations

import argparse
import sys
from pathlib import Path

from backend.research_assistant.golden_eval import (
    evaluate_live_ui_case,
    evaluate_payload_cases,
    load_golden_cases,
    write_golden_eval_outputs,
)
from backend.scripts.research_ui_e2e import _run_browser_loop


def main() -> int:
    args = _parse_args()
    cases_path = Path(args.cases)
    cases = load_golden_cases(cases_path)
    output_dir = Path(args.output_dir or args.output)
    if args.mode == "payload":
        run_result = evaluate_payload_cases(cases, root=cases_path.parent, payload_dir=args.payload_dir)
    else:
        run_result = _run_live_ui_eval(args, cases)
    write_golden_eval_outputs(run_result, output_dir)
    print(f"Research golden eval summary: {output_dir / 'summary.md'}")
    print(f"cases={run_result.case_count} passed={run_result.passed_count} failed={run_result.failed_count}")
    return 0 if run_result.passed else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Research Assistant golden quality evaluation cases.")
    parser.add_argument("--cases", required=True, help="Path to research golden cases JSON.")
    parser.add_argument("--mode", choices=("payload", "live-ui"), default="payload")
    parser.add_argument("--output", help="Output directory for results.json and summary.md.")
    parser.add_argument("--output-dir", help="Alias for --output.")
    parser.add_argument("--payload-dir", help="Optional directory containing payload answer JSON files.")
    parser.add_argument("--frontend-url", default="http://localhost:5173")
    parser.add_argument("--api-base-url", default="http://localhost:12001/api/v1")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="admin123")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--timeout-ms", type=int, default=120_000)
    args = parser.parse_args()
    if not args.output and not args.output_dir:
        parser.error("one of --output or --output-dir is required")
    return args


def _run_live_ui_eval(args: argparse.Namespace, cases):
    live_cases = [case for case in cases if case.mode == "live_ui"]
    if not live_cases:
        raise SystemExit("live-ui mode requires at least one case with mode='live_ui'")
    case = live_cases[0]
    if not case.paper_paths:
        raise SystemExit(f"{case.case_id}: live-ui case requires at least one paper path")
    pdf_path = Path(case.paper_paths[0]).resolve()
    if not pdf_path.exists():
        raise SystemExit(f"{case.case_id}: paper path does not exist: {pdf_path}")
    ui_result = _run_browser_loop(
        frontend_url=args.frontend_url.rstrip("/"),
        api_base_url=args.api_base_url.rstrip("/"),
        username=args.username,
        password=args.password,
        question=case.question,
        pdf_path=pdf_path,
        headed=args.headed,
        timeout_ms=args.timeout_ms,
    )
    return evaluate_live_ui_case(case, ui_result=ui_result)


if __name__ == "__main__":
    sys.exit(main())
