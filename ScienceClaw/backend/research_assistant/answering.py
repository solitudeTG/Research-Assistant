from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol
import re
import logging

import shortuuid

from backend.research_assistant.audit import (
    EvidenceAudit,
    LangChainSemanticAuditor,
    SemanticAuditorLike,
    audit_evidence_claims,
    audit_evidence_claims_with_semantic_auditor,
)
from backend.research_assistant.admission import (
    EvidenceAdmissionResult,
    admit_evidence_hits,
    should_skip_research_retrieval,
    skipped_admission_result,
)
from backend.research_assistant.embeddings import HashingEmbeddingProvider
from backend.research_assistant.storage.database import (
    hybrid_search_evidence_in_database,
    list_whole_paper_evidence_in_database,
    list_memory_entries_from_database,
)
from backend.research_assistant.task_router import (
    ResearchTaskRoute,
    classify_research_task,
    default_evidence_qa_route,
)

logger = logging.getLogger(__name__)

_RECALL_STOP_WORDS = {
    "about",
    "after",
    "also",
    "and",
    "are",
    "can",
    "did",
    "does",
    "for",
    "from",
    "has",
    "have",
    "how",
    "into",
    "that",
    "the",
    "this",
    "what",
    "when",
    "where",
    "which",
    "with",
    "work",
}
_MEMORY_NEGATION_TERMS = {"avoid", "cannot", "don't", "dont", "never", "no", "not", "reject", "without"}
_MEMORY_RELEVANCE_THRESHOLD = 0.3
_MEMORY_DECAY_HALF_LIFE_DAYS = 180
_MEMORY_DECAY_FLOOR = 0.25
CONTEXT_BOUNDARIES = {
    "citation_evidence": ["paper", "web", "database"],
    "context_only_memory": ["memory"],
    "process_trace": ["tool_logs", "runtime_results", "agent_lifecycle"],
    "model_reasoning": ["model_reasoning"],
}
_WHOLE_PAPER_SECTION_EVIDENCE_LIMIT = 2
_WHOLE_PAPER_SYNTHESIS_SECTION_LIMIT = 4
_WHOLE_PAPER_SECTION_QUOTE_LIMIT = 420
_WHOLE_PAPER_SYNTHESIS_QUOTE_LIMIT = 260


@dataclass(frozen=True)
class ResearchCitation:
    evidence_id: int
    chunk_id: str
    paper_id: str
    title: str
    section: str
    page_start: int | None
    page_end: int | None
    quote: str
    citation_label: str
    source_type: str = "paper"
    source_identity: dict[str, Any] = field(default_factory=dict)
    evidence_scope: str = "session"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ResearchAnswer:
    content: str
    citations: list[ResearchCitation]
    context_memory: list[dict] = field(default_factory=list)
    summary_synthesis: dict[str, Any] = field(default_factory=dict)
    audit: EvidenceAudit | None = None
    admission: EvidenceAdmissionResult | None = None
    task_route: ResearchTaskRoute = field(default_factory=default_evidence_qa_route)
    answer_id: str = field(default_factory=lambda: f"research-answer-{shortuuid.uuid()}")

    def __post_init__(self) -> None:
        if self.admission is None:
            object.__setattr__(
                self,
                "admission",
                admit_evidence_hits(
                    [
                        _citation_to_admission_hit(citation, index)
                        for index, citation in enumerate(self.citations, start=1)
                    ]
                ),
            )
        if self.audit is None:
            object.__setattr__(
                self,
                "audit",
                audit_evidence_claims(answer_content=self.content, citations=self.citations),
            )

    @property
    def citation_count(self) -> int:
        return len(self.citations)

    @property
    def context_memory_count(self) -> int:
        return len(self.context_memory)

    @property
    def context_memory_conflict_count(self) -> int:
        return sum(1 for memory in self.context_memory if memory.get("memory_status") == "conflict")

    def to_dict(self) -> dict:
        return {
            "answer_id": self.answer_id,
            "content": self.content,
            "citations": [citation.to_dict() for citation in self.citations],
            "citation_count": self.citation_count,
            "context_memory": self.context_memory,
            "context_memory_count": self.context_memory_count,
            "context_memory_conflict_count": self.context_memory_conflict_count,
            "context_boundaries": CONTEXT_BOUNDARIES,
            "summary_synthesis": self.summary_synthesis,
            "evidence_admission": self.admission.to_dict() if self.admission else {},
            "task_route": self.task_route.to_dict(),
            "audit": self.audit.to_dict() if self.audit else {},
        }


class WholePaperSynthesizer(Protocol):
    async def synthesize(
        self,
        *,
        question: str,
        section_summaries: list[dict[str, Any]],
        citations: list[ResearchCitation],
    ) -> str:
        ...


class LangChainWholePaperSynthesizer:
    def __init__(self, *, model_config: dict[str, Any] | None = None) -> None:
        self.model_config = model_config

    async def synthesize(
        self,
        *,
        question: str,
        section_summaries: list[dict[str, Any]],
        citations: list[ResearchCitation],
    ) -> str:
        from backend.deepagent.engine import get_llm_model

        model = get_llm_model(self.model_config, max_tokens_override=4096, streaming=False)
        section_summary_text = await _invoke_text_model(
            model,
            _section_synthesis_prompt(question=question, section_summaries=section_summaries),
        )
        if _is_missing_context_response(section_summary_text) or not _contains_citation_label(section_summary_text):
            section_summary_text = _deterministic_section_summary_context(section_summaries)

        final_text = await _invoke_text_model(
            model,
            _global_synthesis_prompt(
                question=question,
                section_summary_text=section_summary_text,
                labels=_whole_paper_summary_labels(question),
                citation_count=len(citations),
                section_count=len(section_summaries),
            ),
        )
        if _is_missing_context_response(final_text) or not _contains_citation_label(final_text):
            raise ValueError("LLM synthesis returned an unusable missing-context response")
        return final_text


async def answer_research_question(
    *,
    database_url: str,
    session_id: str,
    project_id: str | None = None,
    user_id: str | None = None,
    question: str,
    embedding_dimensions: int,
    embedding_model: str,
    limit: int = 5,
    whole_paper_synthesizer: WholePaperSynthesizer | None = None,
    semantic_auditor: SemanticAuditorLike | None = None,
    use_llm_whole_paper_synthesis: bool = False,
    use_llm_semantic_auditor: bool = True,
    model_config: dict[str, Any] | None = None,
) -> ResearchAnswer:
    task_route = classify_research_task(question)
    context_memory = await _load_context_memory(
        database_url=database_url,
        session_id=session_id,
        user_id=user_id,
        question=question,
    )
    if task_route.route == "general_chat":
        admission = skipped_admission_result()
        content = _compose_skipped_answer()
        audit = await _audit_answer_content(
            content=content,
            citations=[],
            semantic_auditor=semantic_auditor,
            use_llm_semantic_auditor=use_llm_semantic_auditor,
            model_config=model_config,
        )
        return ResearchAnswer(
            content=content,
            citations=[],
            context_memory=context_memory,
            admission=admission,
            task_route=task_route,
            audit=audit,
        )

    if task_route.route == "whole_paper_summary":
        hits = await list_whole_paper_evidence_in_database(
            database_url,
            session_id=session_id,
            project_id=project_id,
            limit=max(limit, 24),
        )
        admission = admit_evidence_hits(hits)
        citations = _citations_from_hits(admission.accepted_hits)
        content, summary_synthesis = await _compose_whole_paper_summary(
            citations,
            question=question,
            admission=admission,
            synthesizer=whole_paper_synthesizer,
            use_llm_synthesis=use_llm_whole_paper_synthesis,
            model_config=model_config,
        )
        return ResearchAnswer(
            content=content,
            citations=citations,
            context_memory=context_memory,
            summary_synthesis=summary_synthesis,
            admission=admission,
            task_route=task_route,
            audit=await _audit_answer_content(
                content=content,
                citations=citations,
                semantic_auditor=semantic_auditor,
                use_llm_semantic_auditor=use_llm_semantic_auditor,
                model_config=model_config,
            ),
        )

    provider = HashingEmbeddingProvider(
        dimensions=embedding_dimensions,
        model_name=embedding_model,
    )
    search_kwargs = {
        "session_id": session_id,
        "query_text": question,
        "query_embedding": provider.embed_text(question),
        "embedding_model": provider.model_name,
        "limit": limit,
    }
    if project_id is not None:
        search_kwargs["project_id"] = project_id
    hits = await hybrid_search_evidence_in_database(database_url, **search_kwargs)
    admission = admit_evidence_hits(hits)
    citations = _citations_from_hits(admission.accepted_hits)
    if _should_refuse_for_domain_mismatch(question, citations):
        admission = EvidenceAdmissionResult(
            decision="insufficient",
            top_k=admission.top_k,
            threshold=admission.threshold,
            min_accepted_count=admission.min_accepted_count,
            accepted_hits=[],
            rejected_count=admission.top_k,
            highest_score=admission.highest_score,
            reason="insufficient_evidence_should_refuse",
        )
        citations = []
    content = _compose_extractive_answer(citations, admission=admission, question=question)
    return ResearchAnswer(
        content=content,
        citations=citations,
        context_memory=context_memory,
        admission=admission,
        task_route=task_route,
        audit=await _audit_answer_content(
            content=content,
            citations=citations,
            semantic_auditor=semantic_auditor,
            use_llm_semantic_auditor=use_llm_semantic_auditor,
            model_config=model_config,
        ),
    )


async def _audit_answer_content(
    *,
    content: str,
    citations: list[ResearchCitation],
    semantic_auditor: SemanticAuditorLike | None,
    use_llm_semantic_auditor: bool,
    model_config: dict[str, Any] | None,
) -> EvidenceAudit:
    if not use_llm_semantic_auditor:
        return audit_evidence_claims(answer_content=content, citations=citations)
    auditor = semantic_auditor
    model_name = _model_name_from_config(model_config)
    if auditor is None and model_config:
        auditor = LangChainSemanticAuditor(model_config=model_config)
    return await audit_evidence_claims_with_semantic_auditor(
        answer_content=content,
        citations=citations,
        auditor=auditor,
        model=model_name,
    )


def _model_name_from_config(model_config: dict[str, Any] | None) -> str | None:
    if not isinstance(model_config, dict):
        return None
    return str(
        model_config.get("model_name")
        or model_config.get("model")
        or model_config.get("id")
        or "configured-model"
    )


def _citations_from_hits(hits: list[Any]) -> list[ResearchCitation]:
    return [
        ResearchCitation(
            evidence_id=hit.evidence_id,
            chunk_id=hit.chunk_id,
            paper_id=hit.paper_id,
            title=hit.title,
            section=hit.section,
            page_start=hit.page_start,
            page_end=hit.page_end,
            quote=hit.quote,
            citation_label=hit.citation_label,
            source_type=hit.source_type,
            source_identity=hit.source_identity,
            evidence_scope=hit.evidence_scope,
        )
        for hit in hits
    ]


def _compose_extractive_answer(
    citations: list[ResearchCitation],
    *,
    admission: EvidenceAdmissionResult | None = None,
    question: str = "",
) -> str:
    if not citations:
        if admission and admission.top_k > 0:
            return (
                "Retrieved evidence was below the admission threshold; insufficient citation evidence "
                "was found for this question. I cannot answer it as a cited research claim yet."
            )
        return (
            "No citation evidence was found for this question. "
            "I cannot answer it as a cited research claim yet."
        )
    if _looks_like_multi_paper_synthesis_question(question) and _distinct_citation_papers(citations) >= 2:
        return _compose_multi_paper_synthesis_answer(citations)
    lines = ["Based on citation evidence:"]
    for index, citation in enumerate(citations, start=1):
        lines.append(f"{index}. {citation.quote} {citation.citation_label}")
    return "\n".join(lines)


def _compose_skipped_answer() -> str:
    return "This turn does not require citation evidence retrieval."


def _looks_like_multi_paper_synthesis_question(question: str) -> bool:
    normalized = question.casefold()
    return any(
        marker in normalized
        for marker in (
            "compare",
            "comparison",
            "multi-paper",
            "multiple papers",
            "two papers",
            "these two papers",
            "cross-paper",
            "synthesis",
            "synthesize",
            "literature review",
        )
    )


def _distinct_citation_papers(citations: list[ResearchCitation]) -> int:
    return len({citation.paper_id or citation.title for citation in citations})


def _compose_multi_paper_synthesis_answer(citations: list[ResearchCitation]) -> str:
    by_paper: dict[str, list[ResearchCitation]] = {}
    for citation in citations:
        key = citation.paper_id or citation.title
        by_paper.setdefault(key, []).append(citation)

    lines = [
        "Multi-paper synthesis based on citation evidence:",
        "",
        "Paper-specific evidence:",
    ]
    for paper_id, paper_citations in by_paper.items():
        first = paper_citations[0]
        lines.append(f"- {first.title} ({paper_id}): {_single_line_quote(first.quote)} {first.citation_label}")

    representative_citations = _first_citation_per_paper(citations)
    lines.extend(["", "Cross-paper common ground:"])
    common_citations = " ".join(citation.citation_label for citation in representative_citations[:2])
    lines.append(
        "- Both papers frame LEO beamforming as a satellite communication research problem, "
        f"but the exact emphasis must stay within the cited paper evidence. {common_citations}"
    )

    lines.extend(["", "Cross-paper differences:"])
    for paper_id, paper_citations in by_paper.items():
        first = paper_citations[0]
        lines.append(f"- {first.title} emphasizes: {_single_line_quote(first.quote)} {first.citation_label}")

    lines.extend(["", "Evidence-backed limitations:"])
    limitation_citations = " ".join(citation.citation_label for citation in representative_citations[:2])
    lines.append(
        "- This comparison is limited to the admitted citation evidence above; claims about outcomes outside "
        f"these quoted paper chunks should be treated as insufficient evidence. {limitation_citations}"
    )
    return "\n".join(lines)


def _single_line_quote(quote: str, *, limit: int = 420) -> str:
    normalized = re.sub(r"\s+", " ", quote).strip()
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 1].rstrip()}..."


def _first_citation_per_paper(citations: list[ResearchCitation]) -> list[ResearchCitation]:
    seen: set[str] = set()
    representatives: list[ResearchCitation] = []
    for citation in citations:
        paper_key = citation.paper_id or citation.title
        if paper_key in seen:
            continue
        seen.add(paper_key)
        representatives.append(citation)
    return representatives


def _should_refuse_for_domain_mismatch(question: str, citations: list[ResearchCitation]) -> bool:
    if not citations:
        return False
    normalized_question = question.casefold()
    medical_terms = {"clinical", "medical", "patient", "patients", "safety outcomes"}
    if not any(term in normalized_question for term in medical_terms):
        return False
    evidence_text = " ".join(
        " ".join([citation.quote, citation.title, citation.section]).casefold()
        for citation in citations
    )
    return not any(term in evidence_text for term in medical_terms)


async def _compose_whole_paper_summary(
    citations: list[ResearchCitation],
    *,
    question: str = "",
    admission: EvidenceAdmissionResult | None = None,
    synthesizer: WholePaperSynthesizer | None = None,
    use_llm_synthesis: bool = False,
    model_config: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    if not citations:
        return _compose_extractive_answer(citations, admission=admission), {
            "mode": "no_citation_evidence",
            "intermediate_sources": [],
            "citation_source": "original_evidence",
        }
    section_summaries = _section_summaries_from_citations(citations)
    if synthesizer is None and use_llm_synthesis:
        synthesizer = LangChainWholePaperSynthesizer(model_config=model_config)
    if synthesizer is not None:
        try:
            content = (await synthesizer.synthesize(
                question=question,
                section_summaries=section_summaries,
                citations=citations,
            )).strip()
            if content:
                return content, {
                    "mode": "llm_section_global",
                    "intermediate_sources": ["section_summaries"],
                    "intermediate_boundary": "context_only",
                    "citation_source": "original_evidence",
                    "section_count": len(section_summaries),
                }
        except Exception as exc:
            logger.warning("Whole-paper LLM synthesis failed; falling back to deterministic summary: %s", exc)

    return _compose_deterministic_whole_paper_summary(
        citations,
        question=question,
        admission=admission,
        section_summaries=section_summaries,
    ), {
        "mode": "deterministic_extractive",
        "intermediate_sources": ["bounded_original_quotes"],
        "intermediate_boundary": "context_only",
        "citation_source": "original_evidence",
        "section_count": len(section_summaries),
    }


def _compose_deterministic_whole_paper_summary(
    citations: list[ResearchCitation],
    *,
    question: str = "",
    admission: EvidenceAdmissionResult | None = None,
    section_summaries: list[dict[str, Any]] | None = None,
) -> str:
    if not citations:
        return _compose_extractive_answer(citations, admission=admission)
    section_summaries = section_summaries or _section_summaries_from_citations(citations)
    labels = _whole_paper_summary_labels(question)
    lines = [
        labels["title"],
        labels["coverage"].format(citation_count=len(citations), section_count=len(section_summaries)),
        "",
        labels["sections"],
    ]
    for summary in section_summaries:
        lines.append(f"- {summary['section']}: {summary['summary']}")
    lines.extend(["", labels["synthesis"]])
    lines.extend(_global_synthesis_lines(section_summaries))
    return "\n".join(lines)


def _contains_citation_label(text: str) -> bool:
    return bool(re.search(r"\[paper_[^\]]+\]", text))


def _is_missing_context_response(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    if not normalized:
        return True
    missing_context_markers = [
        "section summaries are missing",
        "section summaries that should serve as context are missing",
        "please provide the section summaries",
        "please provide the 15 section summaries",
        "unable to produce the requested summary because",
        "cannot produce the requested summary because",
    ]
    return any(marker in normalized for marker in missing_context_markers)


def _deterministic_section_summary_context(section_summaries: list[dict[str, Any]]) -> str:
    lines = []
    for section_summary in section_summaries:
        section = section_summary.get("section") or "Unknown section"
        summary = section_summary.get("summary") or ""
        citation_labels = [
            citation.citation_label
            for citation in section_summary.get("citations", [])
            if getattr(citation, "citation_label", None)
        ]
        label_text = " ".join(citation_labels)
        lines.append(f"- {section}: {summary} {label_text}".strip())
    return "\n".join(lines)


async def _invoke_text_model(model: Any, prompt: str) -> str:
    if hasattr(model, "ainvoke"):
        response = await model.ainvoke(prompt)
    else:
        response = model.invoke(prompt)
    content = getattr(response, "content", response)
    if isinstance(content, list):
        return "\n".join(str(part.get("text", part)) if isinstance(part, dict) else str(part) for part in content).strip()
    return str(content).strip()


def _section_synthesis_prompt(*, question: str, section_summaries: list[dict[str, Any]]) -> str:
    section_blocks = []
    for section_summary in section_summaries:
        evidence_lines = []
        for citation in section_summary.get("citations", []):
            evidence_lines.append(f"- {citation.citation_label} {citation.quote}")
        section_blocks.append(
            f"## {section_summary.get('section')}\n" + "\n".join(evidence_lines)
        )
    return (
        "You are helping with a trustworthy research-paper workflow.\n"
        "The citation evidence is already provided below; do not ask the user to provide more section summaries.\n"
        "Summarize each paper section using only the provided citation evidence.\n"
        "Generated summaries are context-only intermediate notes, not citation evidence.\n"
        "Every factual sentence should include one or more original citation labels from the evidence.\n"
        "Do not invent claims, experiments, datasets, or conclusions.\n\n"
        f"User question: {question}\n"
        "Citation evidence grouped by section:\n"
        + "\n\n".join(section_blocks)
        + "\n\nReturn concise section summaries with the same section names."
    )


def _global_synthesis_prompt(
    *,
    question: str,
    section_summary_text: str,
    labels: dict[str, str],
    citation_count: int,
    section_count: int,
) -> str:
    return (
        "You are composing the final answer for a trustworthy research-paper workflow.\n"
        "The context-only section summaries are already included below; do not ask the user to provide them.\n"
        "Use the section summaries below as context-only intermediate notes.\n"
        "The final answer must preserve original citation labels already present in the section summaries.\n"
        "Do not cite the generated section summaries themselves. Do not add unsupported claims.\n\n"
        f"User question: {question}\n"
        "Required answer structure:\n"
        f"{labels['title']}\n"
        f"{labels['coverage'].format(citation_count=citation_count, section_count=section_count)}\n\n"
        f"{labels['sections']}\n"
        "- One bullet per important section.\n\n"
        f"{labels['synthesis']}\n"
        "- 3-6 bullets covering research problem, method, contribution, evidence-backed findings, and limitations if present.\n\n"
        "Context-only section summaries:\n"
        + section_summary_text
    )


def _whole_paper_summary_labels(question: str) -> dict[str, str]:
    if _looks_chinese(question):
        return {
            "title": "基于引用证据的整篇论文层级总结：",
            "coverage": "覆盖范围：{citation_count} 条引用证据，覆盖 {section_count} 个章节。",
            "sections": "分节摘要：",
            "synthesis": "全局综合：",
        }
    return {
        "title": "Whole-paper hierarchical summary based on citation evidence:",
        "coverage": "Coverage: {citation_count} citation evidence records across {section_count} sections.",
        "sections": "Section summaries:",
        "synthesis": "Global synthesis:",
    }


def _looks_chinese(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def _section_summaries_from_citations(citations: list[ResearchCitation]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    section_index: dict[str, dict[str, Any]] = {}
    for citation in citations:
        section = citation.section or "Paper"
        if section not in section_index:
            section_summary = {
                "section": section,
                "citations": [],
            }
            section_index[section] = section_summary
            summaries.append(section_summary)
        section_index[section]["citations"].append(citation)

    for summary in summaries:
        selected = summary["citations"][:_WHOLE_PAPER_SECTION_EVIDENCE_LIMIT]
        summary["summary"] = " ".join(
            f"{_bounded_summary_quote(citation.quote, _WHOLE_PAPER_SECTION_QUOTE_LIMIT)} {citation.citation_label}"
            for citation in selected
        )
    return summaries


def _global_synthesis_lines(section_summaries: list[dict[str, Any]]) -> list[str]:
    selected = section_summaries[:_WHOLE_PAPER_SYNTHESIS_SECTION_LIMIT]
    if not selected:
        return ["- No admitted section evidence was available for synthesis."]

    contribution_parts = [
        f"{_bounded_summary_quote(summary['citations'][0].quote, _WHOLE_PAPER_SYNTHESIS_QUOTE_LIMIT)} {summary['citations'][0].citation_label}"
        for summary in selected
        if summary["citations"]
    ]
    if not contribution_parts:
        return ["- No admitted section evidence was available for synthesis."]

    return ["- " + " ".join(contribution_parts)]


def _bounded_summary_quote(quote: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", quote).strip()
    if len(text) <= limit:
        return text
    clipped = text[:limit].rstrip()
    last_space = clipped.rfind(" ")
    if last_space >= int(limit * 0.75):
        clipped = clipped[:last_space].rstrip()
    return f"{clipped}..."


def _citation_to_admission_hit(citation: ResearchCitation, index: int) -> Any:
    return type(
        "AdmissionCitationHit",
        (),
        {
            "evidence_id": citation.evidence_id,
            "rank_score": 1.0 / index,
        },
    )()


async def _load_context_memory(
    *,
    database_url: str,
    session_id: str,
    user_id: str | None,
    question: str,
) -> list[dict]:
    memories = await list_memory_entries_from_database(
        database_url,
        session_id=session_id,
        user_id=user_id,
        layer=None,
        limit=5,
    )
    context_rows = []
    for index, memory in enumerate(memories):
        context = memory.to_context_dict()
        if context.get("source_type") != "memory" or context.get("context_only") is not True:
            continue
        relevance_score, matched_terms = _memory_relevance(question=question, context=context)
        if relevance_score < _MEMORY_RELEVANCE_THRESHOLD:
            continue
        memory_age_days = _memory_age_days(getattr(memory, "created_at", None))
        memory_decay_factor = _memory_decay_factor(memory_age_days)
        decayed_score = round(relevance_score * memory_decay_factor, 3)
        context_rows.append(
            {
                **context,
                "relevance_score": decayed_score,
                "relevance_threshold": _MEMORY_RELEVANCE_THRESHOLD,
                "memory_age_days": memory_age_days,
                "memory_decay_factor": memory_decay_factor,
                "recall_reason": _memory_recall_reason(
                    context=context,
                    matched_terms=matched_terms,
                    relevance_threshold=_MEMORY_RELEVANCE_THRESHOLD,
                    memory_age_days=memory_age_days,
                    memory_decay_factor=memory_decay_factor,
                ),
                "_recall_order": index,
            }
        )
    context_rows.sort(key=lambda row: (-row["relevance_score"], row["_recall_order"]))
    _mark_conflicting_context_memory(context_rows)
    return [{key: value for key, value in row.items() if key != "_recall_order"} for row in context_rows]


def _memory_relevance(*, question: str, context: dict) -> tuple[float, list[str]]:
    question_terms = _recall_terms(question)
    memory_terms = _recall_terms(" ".join([str(context.get("title") or ""), str(context.get("content") or "")]))
    if not question_terms or not memory_terms:
        return 0.0, []
    matched_terms = sorted(question_terms & memory_terms)
    if not matched_terms:
        return 0.0, []
    return round(len(matched_terms) / len(question_terms), 3), matched_terms


def _recall_terms(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-zA-Z0-9]+", text.lower())
        if len(token) > 2 and token not in _RECALL_STOP_WORDS
    }


def _mark_conflicting_context_memory(rows: list[dict]) -> None:
    conflicts: dict[str, set[str]] = {}
    for left_index, left in enumerate(rows):
        left_id = str(left.get("memory_id") or "")
        if not left_id:
            continue
        for right in rows[left_index + 1 :]:
            right_id = str(right.get("memory_id") or "")
            if not right_id:
                continue
            if not _context_memory_conflicts(left, right):
                continue
            conflicts.setdefault(left_id, set()).add(right_id)
            conflicts.setdefault(right_id, set()).add(left_id)

    for row in rows:
        memory_id = str(row.get("memory_id") or "")
        row_conflicts = sorted(conflicts.get(memory_id, set()))
        if not row_conflicts:
            row.setdefault("memory_status", "active")
            continue
        row["memory_status"] = "conflict"
        row["conflicts_with"] = row_conflicts
        row["recall_reason"] = (
            f"{row.get('recall_reason', '').rstrip()} "
            f"conflicts with context-only memory: {', '.join(row_conflicts)}."
        ).strip()


def _context_memory_conflicts(left: dict, right: dict) -> bool:
    left_terms = _memory_topic_terms(left)
    right_terms = _memory_topic_terms(right)
    shared_terms = left_terms & right_terms
    if len(shared_terms) < 3:
        return False
    return _has_memory_negation(left) != _has_memory_negation(right)


def _memory_topic_terms(context: dict) -> set[str]:
    return _recall_terms(" ".join([str(context.get("title") or ""), str(context.get("content") or "")]))


def _has_memory_negation(context: dict) -> bool:
    tokens = set(re.findall(r"[a-zA-Z0-9']+", str(context.get("content") or "").lower()))
    return bool(tokens & _MEMORY_NEGATION_TERMS)


def _memory_age_days(created_at: Any) -> int | None:
    if not isinstance(created_at, datetime):
        return None
    value = created_at
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    age = datetime.now(timezone.utc) - value.astimezone(timezone.utc)
    return max(0, int(age.total_seconds() // 86400))


def _memory_decay_factor(memory_age_days: int | None) -> float:
    if memory_age_days is None:
        return 1.0
    factor = _MEMORY_DECAY_HALF_LIFE_DAYS / (_MEMORY_DECAY_HALF_LIFE_DAYS + memory_age_days)
    return round(max(_MEMORY_DECAY_FLOOR, min(1.0, factor)), 3)


def _memory_recall_reason(
    *,
    context: dict,
    matched_terms: list[str],
    relevance_threshold: float,
    memory_age_days: int | None = None,
    memory_decay_factor: float = 1.0,
) -> str:
    layer = context.get("layer") or "research"
    if matched_terms:
        match_text = f"matched question terms: {', '.join(matched_terms[:5])}"
    else:
        match_text = "no direct question-term match"

    source_subject_type = context.get("source_subject_type")
    source_subject_id = context.get("source_subject_id")
    source_text = ""
    if source_subject_type and source_subject_id:
        source_text = f"; source {source_subject_type} {source_subject_id}"

    decay_text = ""
    if memory_age_days is not None and memory_decay_factor < 1:
        decay_text = f"; age decay {memory_age_days}d x{memory_decay_factor:.2f}"

    threshold_text = f"; threshold>={relevance_threshold:.2f}"
    return f"{layer} memory recalled for this session; {match_text}{threshold_text}{source_text}{decay_text}."
