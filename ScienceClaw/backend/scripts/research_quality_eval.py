from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from backend.research_assistant.evaluation import (
    evaluate_research_answer,
    evidence_qa_quality_gate,
    non_evidence_turn_quality_gate,
    whole_paper_summary_quality_gate,
)


def main() -> int:
    args = _parse_args()
    payload = json.loads(Path(args.answer_json).read_text(encoding="utf-8"))
    requirement = _requirement_for_case(args.case)
    report = evaluate_research_answer(payload, requirement)
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    return 0 if report.passed else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a Research Assistant answer JSON against citation-quality gates."
    )
    parser.add_argument("answer_json", help="Path to a JSON file containing ResearchAnswer.to_dict() output.")
    parser.add_argument(
        "--case",
        choices=("whole_paper_summary", "evidence_qa", "non_evidence_turn"),
        default="whole_paper_summary",
    )
    return parser.parse_args()


def _requirement_for_case(case: str):
    if case == "whole_paper_summary":
        return whole_paper_summary_quality_gate()
    if case == "evidence_qa":
        return evidence_qa_quality_gate()
    if case == "non_evidence_turn":
        return non_evidence_turn_quality_gate()
    raise ValueError(f"Unsupported quality case: {case}")


if __name__ == "__main__":
    sys.exit(main())
