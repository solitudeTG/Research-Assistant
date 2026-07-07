---
id: EV-017
doc_kind: evidence
status: valid
owner: solitudeTG
scope: feature
feature_refs:
  - docs/features/F020-multi-agent-subagent-registry.md
created: 2026-07-03
feature: F020
---

# EV-017: F020 Closure Live UI E2E

## Supports Claim

F020 的五个收口项已经形成可运行、可治理、可追踪的第一代多 Agent 科研能力：

- Reader Worker 能读取真实上传的多材料 citation evidence，并输出 `context_only` envelope。
- Auditor Agent 保留规则审计底线，并输出带语义审计 metadata 的 `process_trace` envelope。
- Research Agents 页面能治理 custom Agent：编辑后进入 draft/disabled，validation 通过后发布为 enabled/passed；`general-purpose` 作为 system built-in 只读展示。
- Chat 中的复杂科研回答路径会真实记录 Reader/Auditor lifecycle，并在 Registry recent-run 中可见。

## Verification Scope

- Frontend: `http://localhost:5173/chat/research-agents` and `http://localhost:5173/chat/{session_id}`
- Backend: Docker service `research-assistant-backend-1`, API `http://127.0.0.1:12001/api/v1`
- Browser: in-app live browser against the real Vite UI.
- Data: two real uploaded `.txt` research materials indexed as session-scoped paper evidence.
- Model environment: local Docker backend using current `.env` model setting.

## Checks

1. Created a real deep session through the backend API.
2. Uploaded two real research materials and verified they indexed as paper evidence.
3. Opened the live `Research Agents` page and verified system/custom type split.
4. Edited `paper_reader_worker` in the live page and verified edit produced draft/disabled plus rollback metadata.
5. Ran the live validation example and verified `paper_reader_worker` became enabled/passed.
6. Submitted a complex research prompt through the live Chat composer.
7. Queried live session events for Reader/Auditor lifecycle metadata.
8. Queried Registry recent-run APIs and verified the live page rendered the new Reader/Auditor run ids.
9. Ran focused backend tests and frontend type-check.

## Live Data Setup

Created deep session:

- Session: `oXoEzhTAgyTSe9WRRAt9aG`

Uploaded and indexed two research materials:

- `.tmp/live-e2e/leobeam-handover-a.txt`
  - Title: `LEO Beam Handover With Predictive Satellite Selection`
  - Paper id: `paper_9c42be98da9768ff`
- `.tmp/live-e2e/leobeam-handover-b.txt`
  - Title: `Adaptive Multi-Beam Resource Allocation for LEO Research Links`
  - Paper id: `paper_0bed6b8c63705ffc`

Research status returned:

```json
{
  "session_id": "oXoEzhTAgyTSe9WRRAt9aG",
  "paper_count": 2,
  "chunk_count": 6,
  "has_indexed_papers": true
}
```

## Live UI Checks

### Research Agents Registry

Opened `http://localhost:5173/chat/research-agents` in the live browser.

Observed:

- `general-purpose`: `系统内置`, `只读`, `系统托管`, `citation_evidence=false`
- `research_auditor`: `用户自定义`, `可编辑`, `已通过`
- `paper_reader_worker`: `用户自定义`, `可编辑`

Custom Agent governance path verified on `paper_reader_worker`:

1. Opened edit form in the real page.
2. Updated description text.
3. Saved changes.
4. Agent remained `草稿` / `已停用`; metadata showed `rollback_snapshot`.
5. Clicked `运行验证`.
6. Validation example showed minimal envelope with:
   - `status=completed`
   - `agent=paper_reader_worker`
   - `boundary=context_only`
   - `citation_evidence=false`
7. Published state became `已启用` / `已通过`.

### Complex Chat Journey

Submitted through the live Chat composer:

```text
请再次基于当前会话的两篇 LEO 材料做一个复杂科研综述，并显式执行证据边界审计：
- 先区分 predictive handover 与 adaptive multi-beam allocation 各自能证明什么；
- 给出三条结论，每条标注 citation evidence 范围；
- 指出不能由材料直接推出的结论；
- 需要 Reader Worker 读取材料，Auditor Agent 审核边界。
```

The visible Chat result showed:

- `引用证据 5`
- `证据审计 partial`
- `approved=5`
- `unsupported=11`
- `上下文边界`
- `citation=paper,web,database`
- `trace=tool_logs,runtime_results,agent_lifecycle`

## Runtime Evidence

Recent Reader Worker run:

```json
{
  "task_id": "research-answer-8XPv8PHgDkngqMA9T3obQi:paper_reader_worker",
  "parent_workflow_id": "research-answer-8XPv8PHgDkngqMA9T3obQi",
  "status": "completed",
  "output_boundary": "context_only",
  "citation_evidence": false,
  "evidence_ref_count": 5
}
```

Recent Auditor Agent run:

```json
{
  "task_id": "research-answer-8XPv8PHgDkngqMA9T3obQi:research_auditor",
  "parent_workflow_id": "research-answer-8XPv8PHgDkngqMA9T3obQi",
  "status": "completed",
  "output_boundary": "process_trace",
  "citation_evidence": false,
  "evidence_ref_count": 0
}
```

Session lifecycle events contained:

```json
[
  {
    "description": "Reader Worker summarized citation evidence",
    "status": "completed",
    "lifecycle": {
      "agent_name": "paper_reader_worker",
      "agent_role": "reader",
      "output_boundary": "context_only",
      "citation_evidence": false,
      "evidence_ref_count": 5,
      "retrieval_scope": "session"
    }
  },
  {
    "description": "Auditor Agent reviewed citation evidence boundaries",
    "status": "completed",
    "lifecycle": {
      "agent_name": "research_auditor",
      "agent_role": "auditor",
      "output_boundary": "process_trace",
      "citation_evidence": false,
      "evidence_ref_count": 0,
      "retrieval_scope": "session"
    }
  }
]
```

Registry recent-run preview showed both new task ids in the real page:

- `research-answer-8XPv8PHgDkngqMA9T3obQi:paper_reader_worker`
- `research-answer-8XPv8PHgDkngqMA9T3obQi:research_auditor`

## Results

Pass.

- Real multi-material session had `paper_count=2`, `chunk_count=6`, and `has_indexed_papers=true`.
- Live custom Agent edit/validation publish flow worked in the Registry page.
- The complex Chat journey produced citation evidence, an audit block, context boundary text, and two persisted subagent runs.
- Reader Worker run used `output_boundary=context_only` and `citation_evidence=false`.
- Auditor Agent run used `output_boundary=process_trace` and `citation_evidence=false`.
- Registry recent-run preview displayed both new live run ids.

## Regression Found And Fixed

Live UI revealed that the paper-grounded `research/answer` route could complete citation retrieval and audit without recording a new Reader/Auditor lifecycle. This meant the Chat journey could look research-complete while bypassing the F020 subagent contract.

Fix:

- Added `research/answer` lifecycle recording after citation answer generation.
- Reader Worker now receives answer citations as a real material package and records a `context_only` run.
- Auditor Agent now receives answer content and citations and records a `process_trace` run.
- Both runs are persisted to Registry recent-run storage and emitted as session step events with `subagent_lifecycle` metadata.

## Verification Commands

Focused checks:

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'
python -m pytest ScienceClaw\backend\tests\test_research_session_routes.py::test_research_answer_persists_audit_result -q
python -m pytest ScienceClaw\backend\tests\test_research_subagents.py ScienceClaw\backend\tests\test_research_repository.py::test_list_subagent_definitions_auto_disables_unvalidated_legacy_custom_rows ScienceClaw\backend\tests\test_research_session_routes.py::test_research_answer_persists_audit_result ScienceClaw\backend\tests\test_research_session_routes.py::test_update_research_agent_route_rejects_edit_and_enable_in_one_step ScienceClaw\backend\tests\test_research_agents_frontend_contract.py -q
npm.cmd run type-check
```

Results:

- Focused route test: `1 passed`
- Focused F020 closure suite: `19 passed`
- Frontend type-check: passed

## Artifacts

- Feature: `docs/features/F020-multi-agent-subagent-registry.md`
- Live session: `oXoEzhTAgyTSe9WRRAt9aG`
- Reader run: `research-answer-8XPv8PHgDkngqMA9T3obQi:paper_reader_worker`
- Auditor run: `research-answer-8XPv8PHgDkngqMA9T3obQi:research_auditor`
- Uploaded local materials:
  - `.tmp/live-e2e/leobeam-handover-a.txt`
  - `.tmp/live-e2e/leobeam-handover-b.txt`
- Focused test result: `76 passed, 417 warnings`
- Frontend result: `npm.cmd run type-check` passed
- Diff hygiene: `git diff --check` passed

## Limitations

- The semantic Auditor layer is currently implemented as an LLM-ready conservative fallback on top of the deterministic floor; it does not yet call a separate external LLM in unit tests.
- The screenshot capture API was unavailable in the current in-app browser wrapper, so this evidence relies on structured live UI observations plus API lifecycle records.
- `paper_reader_worker` and `research_auditor` remain non-citation process/context agents; only original paper/web/database evidence can become citation evidence.

## Notes

This evidence intentionally records the answer-route gap found during live UI testing. The fix keeps citation retrieval and deterministic audit behavior intact while adding real subagent lifecycle persistence for the F020 contract.
