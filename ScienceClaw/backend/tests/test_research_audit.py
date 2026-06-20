from backend.research_assistant.audit import audit_evidence_claims
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
    assert audit.boundaries["citation_evidence"] == ["paper"]
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


def test_audit_evidence_claims_marks_answer_without_citations_as_unsupported():
    audit = audit_evidence_claims(
        answer_content="No citation evidence was found in the uploaded papers for this question.",
        citations=[],
    )

    assert audit.status == "unsupported"
    assert audit.claim_count == 1
    assert audit.unsupported_claim_count == 1
    assert audit.claims[0].status == "unsupported"
