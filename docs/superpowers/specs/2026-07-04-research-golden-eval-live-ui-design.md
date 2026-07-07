# Research Golden Eval Live UI Design

## Goal

Build a small, reproducible real-paper quality evaluation loop for Research Assistant that can be demonstrated in interviews and used by future agents before tuning retrieval, synthesis, audit, or multi-agent behavior.

The first version must prove the real product path, not only offline payload validation:

```text
real paper fixtures -> live UI/API answer or report -> Evidence Audit -> F019 quality gate -> JSON + Markdown evaluation report -> AgentMentor Evidence
```

## Vision Anchor

- Source: user approved方案 B and explicitly required real live UI E2E testing.
- User pain point: current Research Assistant has many correct structural pieces, but interview and product credibility depend on proving real papers and real model outputs remain citation-grounded and auditable.
- Desired outcome: a compact golden-eval workflow that shows whether answers/reports preserve citation evidence boundaries, expose unsupported claims, and produce a readable quality report.
- Non-goals: no dashboard, no large benchmark platform, no LLM judge, no DOCX/PDF exporter, no web crawler, no mandatory multi-agent path, no prompt/reranker tuning in this slice.

## Scope

This is an extension of F019. It should not create a new active Feature unless later work broadens beyond quality evaluation. The work should update F019 and link the new Evidence artifact.

The first implementation should include:

- A JSON golden case file under `docs/evals/research_golden_cases.json`.
- A reusable backend module for case loading, threshold mapping, result aggregation, and Markdown summary rendering.
- A CLI runner under `ScienceClaw/backend/scripts/research_golden_eval.py`.
- Focused backend tests for schema parsing, threshold behavior, batch failure isolation, and Markdown diagnostics.
- A live UI E2E mode that drives the existing browser workflow for at least one real-paper case and feeds the resulting answer payload into the quality report.
- A final Evidence record, expected path `docs/evidence/EV-018-f019-golden-eval-live-ui-e2e.md`.

## Golden Case Contract

Each case should be stable and intent-based, not text-snapshot based:

```json
{
  "case_id": "leo_beamforming_summary_001",
  "task_type": "whole_paper_summary",
  "mode": "live_ui",
  "paper_paths": ["paper_data/example.pdf"],
  "question": "总结这篇论文的核心问题、方法和贡献。",
  "quality_thresholds": {
    "min_citation_count": 3,
    "max_unsupported_claim_ratio": 0.5,
    "max_invalid_claims": 0,
    "required_summary_mode": "llm_section_global"
  },
  "required_outputs": {
    "answer": true,
    "report": true,
    "markdown_summary": true
  }
}
```

Allowed `task_type` values for the first version:

- `whole_paper_summary`
- `evidence_qa`
- `no_evidence_or_insufficient_evidence`
- `multi_paper_synthesis`

The first version may support `multi_paper_synthesis` as a case type in reports without requiring a separate multi-agent acceptance claim.

## Runner Behavior

The CLI should support two modes:

- `--mode payload`: evaluate saved answer JSON files. This is fast and deterministic for tests.
- `--mode live-ui`: run against a running frontend/backend stack using Playwright and the existing authenticated browser flow.

The runner should produce one output directory:

```text
workspace/research_eval/<run_id>/
  results.json
  summary.md
  cases/<case_id>.answer.json
  cases/<case_id>.quality.json
  cases/<case_id>.report.json       # when report generation is enabled
```

If one case fails, the batch continues and records that case as failed. The CLI exits non-zero when any required case fails the quality gate or live UI workflow.

## Live UI E2E Acceptance

The live UI path must:

- Log in through the real frontend.
- Create or open a real chat session.
- Upload a real PDF through the visible file input or use an explicitly bound project/library path.
- Wait for indexing.
- Submit a research answer request from the UI/API path used by ChatPage.
- Generate a Markdown report when the case requires it.
- Collect session events, answer metadata, audit metadata, and round files.
- Verify ActivityPanel-relevant trace steps are real events, not fabricated metadata.

Live UI E2E can use existing development credentials and local stack assumptions, but the Evidence document must record the URLs, session ids, commands, and limitations.

## Quality Checks

Every evaluated answer must check:

- citation count
- citation source types
- citation evidence scope
- invalid-source claim count
- unsupported claim ratio
- context boundary manifest
- required summary mode when relevant
- no context-only memory as citation
- no process trace as citation
- no model reasoning as citation

Report-producing cases must also check:

- Markdown report file exists
- evidence sidecar file exists
- partial/no-evidence reports expose limitations or next steps
- report metadata includes reader summary when available

## Testing

Focused tests should cover:

- golden case schema parsing from JSON
- mapping case thresholds into `ResearchQualityRequirement`
- batch aggregation continues after a failed case
- Markdown summary includes pass/fail counts, finding codes, and next-step module hints
- CLI returns non-zero when any required case fails
- live UI assertion rejects missing answer payload, missing audit, missing report sidecar, or missing trace steps

Tests should not call external models by default. Real live UI E2E belongs in manual/evidence commands and can be skipped in unit tests unless the stack is explicitly running.

## Interview Demo Path

The intended demo is:

1. Show one successful whole-paper summary case.
2. Show one insufficient-evidence or partial case.
3. Run or show the golden eval summary.
4. Explain how failures map to F005 retrieval, F006 audit, F017 synthesis, or F020 multi-agent follow-up.

## Acceptance Criteria

- [ ] At least six golden cases exist, with at least three real paper files referenced.
- [ ] A single command can produce `results.json` and `summary.md`.
- [ ] The batch runner records individual case artifacts and continues after failed cases.
- [ ] F019 quality gates are reused rather than duplicated.
- [ ] At least one live UI E2E case is executed and recorded in Evidence.
- [ ] The live UI E2E verifies a real answer/report path and real trace events.
- [ ] The generated summary is suitable for interview demonstration.
- [ ] F019 is updated with the new slice and Evidence link.

## Open Questions

- Whether all six first-version cases should be runnable live UI cases or only one live UI case plus payload cases. The implementation should prefer one live UI smoke plus payload-eval breadth to keep the first slice reliable.
- Whether current `paper_data/` PDFs are sufficient for all three real-paper references. If only two usable PDFs exist, add a generated smoke PDF only for live UI plumbing, but do not count it as a real-paper golden case.
