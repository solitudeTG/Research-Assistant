import pytest

from backend.research_assistant.audit import audit_evidence_claims, audit_evidence_claims_with_semantic_auditor
from backend.research_assistant.answering import ResearchCitation


def test_audit_evidence_claims_approves_claims_backed_by_paper_citations():
    audit = audit_evidence_claims(
        answer_content="Based on uploaded paper evidence:\n1. Hybrid retrieval improves recall. [paper-1:Results:4]",
        citations=[
            ResearchCitation(
                evidence_id=17,
                chunk_id="chunk-17",
                paper_id="paper-1",
                title="Hybrid Retrieval",
                section="Results",
                page_start=4,
                page_end=4,
                quote="Hybrid retrieval improves recall.",
                citation_label="[paper-1:Results:4]",
            )
        ],
    )

    assert audit.status == "approved"
    assert audit.claim_count == 1
    assert audit.approved_claim_count == 1
    assert audit.claims[0].status == "approved"
    assert audit.claims[0].evidence_ids == [17]
    assert audit.claims[0].support_score == 1.0
    assert audit.boundaries["citation_evidence"] == ["paper", "web", "database"]
    assert audit.boundaries["context_only"] == ["memory", "model_reasoning", "process_trace", "tool_logs"]


def test_audit_evidence_claims_rejects_context_only_sources_as_citation_evidence():
    audit = audit_evidence_claims(
        answer_content="Based on uploaded paper evidence:\n1. Prior memory says hybrid retrieval improves recall. [memory-1]",
        citations=[
            ResearchCitation(
                evidence_id=91,
                chunk_id="memory-1",
                paper_id="memory",
                title="Session memory",
                section="Memory",
                page_start=None,
                page_end=None,
                quote="Prior memory says hybrid retrieval improves recall.",
                citation_label="[memory-1]",
                source_type="memory",
            )
        ],
    )

    assert audit.status == "invalid_source"
    assert audit.invalid_source_count == 1
    assert audit.claims[0].status == "invalid_source"
    assert "memory" in audit.claims[0].notes[0]


def test_audit_evidence_claims_scopes_invalid_sources_to_cited_claim_label():
    audit = audit_evidence_claims(
        answer_content=(
            "Based on uploaded paper evidence:\n"
            "1. Hybrid retrieval improves recall. [paper-1:Results:4]\n"
            "2. Prior memory says hybrid retrieval improves recall. [memory-1]"
        ),
        citations=[
            ResearchCitation(
                evidence_id=17,
                chunk_id="chunk-17",
                paper_id="paper-1",
                title="Hybrid Retrieval",
                section="Results",
                page_start=4,
                page_end=4,
                quote="Hybrid retrieval improves recall.",
                citation_label="[paper-1:Results:4]",
            ),
            ResearchCitation(
                evidence_id=91,
                chunk_id="memory-1",
                paper_id="memory",
                title="Session memory",
                section="Memory",
                page_start=None,
                page_end=None,
                quote="Prior memory says hybrid retrieval improves recall.",
                citation_label="[memory-1]",
                source_type="memory",
            ),
        ],
    )

    assert audit.status == "invalid_source"
    assert [claim.status for claim in audit.claims] == ["approved", "invalid_source"]
    assert audit.claims[0].evidence_ids == [17]
    assert audit.claims[0].support_score == 1.0
    assert audit.claims[1].evidence_ids == [91]
    assert audit.invalid_source_count == 1


def test_audit_evidence_claims_accepts_web_and_database_citation_evidence():
    audit = audit_evidence_claims(
        answer_content=(
            "Based on uploaded paper evidence:\n"
            "1. Registry data shows a reproducible benchmark result. [db-1]\n"
            "2. The project page documents the benchmark protocol. [web-1]"
        ),
        citations=[
            ResearchCitation(
                evidence_id=101,
                chunk_id="db-row-1",
                paper_id="database-source",
                title="Benchmark Registry",
                section="Rows",
                page_start=None,
                page_end=None,
                quote="Registry data shows a reproducible benchmark result.",
                citation_label="[db-1]",
                source_type="database",
            ),
            ResearchCitation(
                evidence_id=102,
                chunk_id="web-page-1",
                paper_id="web-source",
                title="Benchmark Protocol",
                section="Protocol",
                page_start=None,
                page_end=None,
                quote="The project page documents the benchmark protocol.",
                citation_label="[web-1]",
                source_type="web",
            ),
        ],
    )

    assert audit.status == "approved"
    assert audit.approved_claim_count == 2
    assert audit.invalid_source_count == 0
    assert [claim.evidence_ids for claim in audit.claims] == [[101], [102]]


def test_audit_evidence_claims_approves_claim_supported_by_multiple_citations():
    audit = audit_evidence_claims(
        answer_content=(
            "Based on citation evidence:\n"
            "1. Hybrid retrieval combines lexical matching and vector similarity. "
            "[paper-1:Methods:2] [db-1]"
        ),
        citations=[
            ResearchCitation(
                evidence_id=17,
                chunk_id="chunk-17",
                paper_id="paper-1",
                title="Hybrid Retrieval",
                section="Methods",
                page_start=2,
                page_end=2,
                quote="Hybrid retrieval combines lexical matching.",
                citation_label="[paper-1:Methods:2]",
            ),
            ResearchCitation(
                evidence_id=101,
                chunk_id="db-row-1",
                paper_id="database-source",
                title="Benchmark Registry",
                section="Rows",
                page_start=None,
                page_end=None,
                quote="Hybrid retrieval uses vector similarity.",
                citation_label="[db-1]",
                source_type="database",
            ),
        ],
    )

    assert audit.status == "approved"
    assert audit.claims[0].status == "approved"
    assert audit.claims[0].evidence_ids == [17, 101]
    assert audit.claims[0].support_score == 1.0
    assert "Multiple cited evidence records jointly support this claim." in audit.claims[0].notes


def test_audit_evidence_claims_rejects_claim_without_explicit_citation_label():
    audit = audit_evidence_claims(
        answer_content=(
            "Based on uploaded paper evidence:\n"
            "1. Hybrid retrieval improves recall. [paper-1:Results:4]\n"
            "2. Unlabeled database result is reproducible."
        ),
        citations=[
            ResearchCitation(
                evidence_id=17,
                chunk_id="chunk-17",
                paper_id="paper-1",
                title="Hybrid Retrieval",
                section="Results",
                page_start=4,
                page_end=4,
                quote="Hybrid retrieval improves recall.",
                citation_label="[paper-1:Results:4]",
            ),
            ResearchCitation(
                evidence_id=101,
                chunk_id="db-row-1",
                paper_id="database-source",
                title="Benchmark Registry",
                section="Rows",
                page_start=None,
                page_end=None,
                quote="Unlabeled database result is reproducible.",
                citation_label="[db-1]",
                source_type="database",
            ),
        ],
    )

    assert audit.status == "partial"
    assert [claim.status for claim in audit.claims] == ["approved", "unsupported"]
    assert audit.claims[0].evidence_ids == [17]
    assert audit.claims[1].evidence_ids == []
    assert "No explicit citation label was attached to this claim." in audit.claims[1].notes


def test_audit_evidence_claims_keeps_nearest_evidence_on_unlabeled_claim():
    audit = audit_evidence_claims(
        answer_content=(
            "Based on uploaded paper evidence:\n"
            "1. Hybrid retrieval improves recall. [paper-1:Results:4]\n"
            "2. Hybrid retrieval improves recall."
        ),
        citations=[
            ResearchCitation(
                evidence_id=17,
                chunk_id="chunk-17",
                paper_id="paper-1",
                title="Hybrid Retrieval",
                section="Results",
                page_start=4,
                page_end=4,
                quote="Hybrid retrieval improves recall.",
                citation_label="[paper-1:Results:4]",
            ),
        ],
    )

    claim = audit.to_dict()["claims"][1]

    assert claim["support_status"] == "unsupported"
    assert claim["finding_code"] == "semantic_support_missing"
    assert claim["semantic_relevance_score"] == 1.0
    assert claim["source_quality_score"] == 1.0
    assert claim["cited_evidence"][0]["evidence_id"] == 17


def test_audit_evidence_claims_marks_answer_without_citations_as_unsupported():
    audit = audit_evidence_claims(
        answer_content="No citation evidence was found for this question.",
        citations=[],
    )

    assert audit.status == "unsupported"
    assert audit.claim_count == 1
    assert audit.unsupported_claim_count == 1
    assert audit.claims[0].status == "unsupported"
    assert audit.claims[0].support_score == 0.0


def test_audit_evidence_claims_exposes_nearest_citation_support_score_for_unsupported_claim():
    audit = audit_evidence_claims(
        answer_content="Hybrid retrieval proves clinical benefit.",
        citations=[
            ResearchCitation(
                evidence_id=17,
                chunk_id="chunk-17",
                paper_id="paper-1",
                title="Hybrid Retrieval",
                section="Results",
                page_start=4,
                page_end=4,
                quote="Hybrid retrieval improves recall.",
                citation_label="[paper-1:Results:4]",
            )
        ],
    )

    assert audit.status == "unsupported"
    assert audit.claims[0].status == "unsupported"
    assert 0 < audit.claims[0].support_score < 1
    assert "Nearest citation evidence: 17" in audit.claims[0].notes[0]


def test_audit_evidence_claims_rejects_overclaim_even_with_valid_citation_label():
    audit = audit_evidence_claims(
        answer_content=(
            "Based on uploaded paper evidence:\n"
            "1. Hybrid retrieval improves recall. This proves clinical benefit. [paper-1:Results:4]"
        ),
        citations=[
            ResearchCitation(
                evidence_id=17,
                chunk_id="chunk-17",
                paper_id="paper-1",
                title="Hybrid Retrieval",
                section="Results",
                page_start=4,
                page_end=4,
                quote="Hybrid retrieval improves recall.",
                citation_label="[paper-1:Results:4]",
            )
        ],
    )

    assert audit.status == "unsupported"
    assert audit.claims[0].status == "unsupported"
    assert audit.claims[0].evidence_ids == []
    assert 0 < audit.claims[0].support_score < 1
    assert "No attached citation quote directly supports this claim." in audit.claims[0].notes[-1]


def test_audit_evidence_claims_ignores_markdown_structure_lines():
    audit = audit_evidence_claims(
        answer_content=(
            "**Global synthesis:**\n"
            "- **Research problem:** Hybrid retrieval improves recall. [paper-1:Results:4]"
        ),
        citations=[
            ResearchCitation(
                evidence_id=17,
                chunk_id="chunk-17",
                paper_id="paper-1",
                title="Hybrid Retrieval",
                section="Results",
                page_start=4,
                page_end=4,
                quote="Hybrid retrieval improves recall.",
                citation_label="[paper-1:Results:4]",
            )
        ],
    )

    assert audit.claim_count == 1
    assert audit.claims[0].claim_text == "- **Research problem:** Hybrid retrieval improves recall. [paper-1:Results:4]"
    assert audit.claims[0].status == "approved"


def test_audit_evidence_claims_marks_cited_synthesis_with_incomplete_support_as_partial():
    audit = audit_evidence_claims(
        answer_content=(
            "- **Method:** The paper introduces a hybrid retrieval workflow that combines "
            "lexical matching with vector search to improve recall and keep citations auditable. "
            "[paper-1:Methods:2]"
        ),
        citations=[
            ResearchCitation(
                evidence_id=17,
                chunk_id="chunk-17",
                paper_id="paper-1",
                title="Hybrid Retrieval",
                section="Methods",
                page_start=2,
                page_end=2,
                quote="Hybrid retrieval combines lexical matching and vector search to improve recall.",
                citation_label="[paper-1:Methods:2]",
            )
        ],
    )

    assert audit.status == "partial"
    assert audit.claim_count == 1
    assert audit.approved_claim_count == 0
    assert audit.partial_claim_count == 1
    assert audit.unsupported_claim_count == 0
    assert audit.claims[0].status == "partial"
    assert audit.claims[0].evidence_ids == [17]
    assert 0 < audit.claims[0].support_score < 1
    assert "Cited evidence partially supports this synthesized claim." in audit.claims[0].notes


def test_semantic_audit_claims_expose_support_status_scores_evidence_and_finding_codes():
    audit = audit_evidence_claims(
        answer_content=(
            "1. Hybrid retrieval improves recall. [paper-1:Results:4]\n"
            "2. Hybrid retrieval proves clinical safety outcomes. [paper-1:Results:4]\n"
            "3. Prior memory proves the same claim. [memory-1]"
        ),
        citations=[
            ResearchCitation(
                evidence_id=17,
                chunk_id="chunk-17",
                paper_id="paper-1",
                title="Hybrid Retrieval",
                section="Results",
                page_start=4,
                page_end=4,
                quote="Hybrid retrieval improves recall.",
                citation_label="[paper-1:Results:4]",
            ),
            ResearchCitation(
                evidence_id=91,
                chunk_id="memory-1",
                paper_id="memory",
                title="Session memory",
                section="Memory",
                page_start=None,
                page_end=None,
                quote="Prior memory proves the same claim.",
                citation_label="[memory-1]",
                source_type="memory",
            ),
        ],
    )

    payload = audit.to_dict()
    claims = payload["claims"]

    assert claims[0]["claim_id"] == "claim-1"
    assert claims[0]["support_status"] == "supported"
    assert claims[0]["semantic_relevance_score"] == 1.0
    assert claims[0]["source_quality_score"] == 1.0
    assert claims[0]["finding_code"] is None
    assert claims[0]["cited_evidence"][0] == {
        "evidence_id": 17,
        "source_type": "paper",
        "paper_id": "paper-1",
        "title": "Hybrid Retrieval",
        "section": "Results",
        "page_start": 4,
        "page_end": 4,
        "chunk_id": "chunk-17",
        "quote": "Hybrid retrieval improves recall.",
    }

    assert claims[1]["support_status"] == "unsupported"
    assert claims[1]["finding_code"] == "semantic_support_mismatch"
    assert "No attached citation quote directly supports this claim." in claims[1]["rationale"]

    assert claims[2]["support_status"] == "source_mismatch"
    assert claims[2]["finding_code"] == "context_only_source_used_as_citation"
    assert claims[2]["source_quality_score"] == 0.0


def test_semantic_audit_marks_no_citation_answer_as_insufficient_evidence_refusal():
    audit = audit_evidence_claims(
        answer_content="Insufficient citation evidence was found for this question. I cannot answer it as a cited research claim yet.",
        citations=[],
    )

    claim = audit.to_dict()["claims"][0]

    assert claim["support_status"] == "insufficient_evidence"
    assert claim["finding_code"] == "insufficient_evidence_should_refuse"


@pytest.mark.asyncio
async def test_llm_semantic_auditor_overlays_overreach_without_replacing_floor():
    class FakeAuditor:
        async def audit_claims(self, *, deterministic_audit, citations):
            return [
                {
                    "claim_id": "claim-1",
                    "support_status": "overreach",
                    "finding_code": "llm_overreach",
                    "rationale": "The quote discusses beamforming performance, not clinical patient outcomes.",
                }
            ]

    audit = await audit_evidence_claims_with_semantic_auditor(
        answer_content="1. LEO beamforming proves clinical safety outcomes. [paper-1:Results:4]",
        citations=[
            ResearchCitation(
                evidence_id=17,
                chunk_id="chunk-17",
                paper_id="paper-1",
                title="LEO Beamforming",
                section="Results",
                page_start=4,
                page_end=4,
                quote="LEO beamforming improves satellite communication throughput.",
                citation_label="[paper-1:Results:4]",
            )
        ],
        auditor=FakeAuditor(),
        model="fake-auditor",
    )

    payload = audit.to_dict()
    claim = payload["claims"][0]

    assert payload["semantic_auditor"]["mode"] == "llm_enhanced"
    assert payload["semantic_auditor"]["model"] == "fake-auditor"
    assert payload["semantic_auditor"]["overreach_count"] == 1
    assert claim["support_status"] == "overreach"
    assert claim["finding_code"] == "llm_overreach"
    assert claim["deterministic_support_status"] == "unsupported"
    assert claim["llm_support_status"] == "overreach"
    assert "clinical patient outcomes" in claim["llm_rationale"]


@pytest.mark.asyncio
async def test_llm_semantic_auditor_invalid_json_safely_degrades_to_deterministic():
    class BadAuditor:
        async def audit_claims(self, *, deterministic_audit, citations):
            return [{"claim_id": "claim-1", "support_status": "invented"}]

    audit = await audit_evidence_claims_with_semantic_auditor(
        answer_content="1. Hybrid retrieval improves recall. [paper-1:Results:4]",
        citations=[
            ResearchCitation(
                evidence_id=17,
                chunk_id="chunk-17",
                paper_id="paper-1",
                title="Hybrid Retrieval",
                section="Results",
                page_start=4,
                page_end=4,
                quote="Hybrid retrieval improves recall.",
                citation_label="[paper-1:Results:4]",
            )
        ],
        auditor=BadAuditor(),
        model="fake-auditor",
    )

    payload = audit.to_dict()

    assert audit.status == "approved"
    assert payload["claims"][0]["support_status"] == "supported"
    assert payload["semantic_auditor"]["mode"] == "llm_failed"
    assert payload["semantic_auditor"]["llm_auditor_status"].startswith("invalid_output")


@pytest.mark.asyncio
async def test_llm_semantic_auditor_normalizes_non_llm_finding_code():
    class FakeAuditor:
        async def audit_claims(self, *, deterministic_audit, citations):
            return [
                {
                    "claim_id": "claim-1",
                    "support_status": "insufficient_evidence",
                    "finding_code": "insufficient_evidence_should_refuse",
                    "rationale": "There is not enough cited evidence to support the claim.",
                }
            ]

    audit = await audit_evidence_claims_with_semantic_auditor(
        answer_content=(
            "Insufficient citation evidence was found for this question. "
            "I cannot answer it as a cited research claim yet."
        ),
        citations=[],
        auditor=FakeAuditor(),
        model="fake-auditor",
    )

    payload = audit.to_dict()
    claim = payload["claims"][0]

    assert payload["semantic_auditor"]["mode"] == "llm_enhanced"
    assert claim["support_status"] == "insufficient_evidence"
    assert claim["finding_code"] == "llm_insufficient_evidence"
    assert claim["deterministic_support_status"] == "insufficient_evidence"
    assert claim["llm_support_status"] == "insufficient_evidence"
