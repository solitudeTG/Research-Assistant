---
id: EV-008
doc_kind: evidence
scope: project
feature_refs:
  - docs/features/F017-llm-section-summary-global-synthesis.md
created: 2026-06-30
updated: 2026-06-30
---

# EV-008: F017 LLM Section Summary to Global Synthesis Verification

## Supports Claim

本 Evidence 支撑 F017 的完成声明：单篇整篇论文总结可以在 F016 的分节证据扫读之后调用 LLM section/global synthesis，生成更像研究者综合后的回答，同时 citation 仍只来自原始 paper evidence；当 LLM synthesis 失败时，会退回 deterministic F016 summary。

## Verification Scope

覆盖范围：

- backend answering orchestration：whole-paper route、注入式 synthesizer、LLM 失败回退、citation boundary。
- route/trace contract：会话研究回答接口把 `summary_synthesis` 写入 metadata，并在 LLM 综合完成时使用真实 trace 文案。
- frontend contract：API type、message metadata type、ActivityPanel 能展示 `summary_synthesis` 的轻量过程元数据。
- full backend regression、frontend type-check/build。
- live API：在本地已启动服务上，用真实会话和已索引论文触发整篇论文中文总结，确认返回 `llm_section_global`。

未覆盖范围：

- 没有把真实浏览器截图作为验收依据；本轮 live API 已验证后端与模型链路，UI 侧用 contract/type/build 覆盖。
- 没有实现多论文 Research Synthesis、多 Agent workflow 或 LLM Router 扩展，这些属于 F014/Future Enhancement。
- 没有评估真实 LLM 输出质量的长期指标，只验证边界、fallback 和一次真实链路可用性。

## Checks

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; pytest ScienceClaw/backend/tests/test_research_answering.py -k "injected_llm_synthesizer or falls_back_when_llm_synthesizer_fails" -q --basetemp=.pytest_tmp\f017-red
```

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant\ScienceClaw'; pytest ScienceClaw/backend/tests/test_research_answering.py -q --basetemp=.pytest_tmp\f017-answering
```

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant;E:\Self-Project\Research-Assistant\ScienceClaw'; pytest ScienceClaw/backend/tests/test_research_answering.py ScienceClaw/backend/tests/test_research_session_routes.py -k "research_answer or whole_paper_summary" ScienceClaw/backend/tests/test_research_frontend_contracts.py -q --basetemp=.pytest_tmp\f017-focused
```

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant;E:\Self-Project\Research-Assistant\ScienceClaw'; pytest ScienceClaw/backend/tests -q --basetemp=.pytest_tmp\f017-full
```

```powershell
npm.cmd run type-check
```

```powershell
npm.cmd run build
```

```powershell
docker compose restart backend frontend; docker compose ps
```

```powershell
curl.exe -s -X POST "http://localhost:12001/api/v1/sessions/mMKV5kKCEEcPKbxYQeUH7k/research/answer" -H "Authorization: Bearer <local-token>" -H "Content-Type: application/json" --data-binary "@.pytest_tmp\f017-live-request.json"
```

```powershell
python C:\Users\HUAWEI\.codex\skills\using-agentmentor\scripts\knowledge_check.py --root E:\Self-Project\Research-Assistant --docs-path docs --strict --feature-index F017-llm-section-summary-global-synthesis
```

## Commands

```powershell
npm.cmd run type-check
```

```powershell
$env:PYTHONPATH='E:\Self-Project\Research-Assistant;E:\Self-Project\Research-Assistant\ScienceClaw'; pytest ScienceClaw/backend/tests/test_research_answering.py ScienceClaw/backend/tests/test_research_session_routes.py -k "whole_paper_summary or langchain_whole_paper or model_config or research_answer" -q --basetemp=.pytest_tmp\f017-final-verify
```

```powershell
python -X utf8 -c "<local live-session event check for session XKMcEkESLvRXve64QyFvcP>"
```

```powershell
python C:\Users\HUAWEI\.codex\plugins\cache\personal\agentmentor\0.2.0+codex.20260604093000\skills\using-agentmentor\scripts\knowledge_check.py --root E:\Self-Project\Research-Assistant --docs-path docs --strict
```

## Results

Pass.

- RED check: 2 个新增测试先按预期失败，失败原因是 `answer_research_question` 尚不支持 `whole_paper_synthesizer` 参数。
- Focused answering: `19 passed`。
- Focused route/frontend contract: `26 passed, 84 deselected`。
- Full backend tests: `195 passed`。
- Frontend type-check: pass。
- Frontend build: pass；保留既有 warning，包括 Browserslist 过旧、CSS minifying warning 和 chunk size warning。
- Live API: pass。响应中 `summary_synthesis.mode=llm_section_global`，`intermediate_boundary=context_only`，`citation_source=original_evidence`，`section_count=15`，`citation_count=15`，`task_route.route=whole_paper_summary`。
- AgentMentor validation: pass after this Evidence and F017 Feature were updated.

## Artifacts

- Live request: `.pytest_tmp\f017-live-request.json`
- Live response: `.pytest_tmp\f017-live-response.json`
- Feature: [F017 LLM Section Summary to Global Synthesis](../features/F017-llm-section-summary-global-synthesis.md)
- Key implementation files:
  - `ScienceClaw/backend/research_assistant/answering.py`
  - `ScienceClaw/backend/route/sessions.py`
  - `ScienceClaw/frontend/src/components/ActivityPanel.vue`

## Limitations

本 Evidence 不能证明长期真实模型输出质量稳定，也不能证明所有论文结构都能被完美分节。它证明的是 F017 的工程边界已经成立：LLM synthesis 发生在 evidence admission 之后，intermediate summaries 是 context-only，citation records 保持原始证据，失败可恢复。

## Notes

F017 有意不把 generated section summaries 作为 citation，也不把它们持久化到 Project RAG。这个边界延续 F004/F015：generated summary 可以帮助组织回答，但不能替代 paper/web/database evidence 的 source identity。
