from backend.research_assistant.admission import (
    MIN_EVIDENCE_RELEVANCE_SCORE,
    admit_evidence_hits,
    should_skip_research_retrieval,
)
from backend.research_assistant.retrieval import EvidenceHit


def _hit(*, evidence_id: int, rank_score: float) -> EvidenceHit:
    return EvidenceHit(
        evidence_id=evidence_id,
        chunk_id=f"chunk-{evidence_id}",
        paper_id="paper-1",
        title="Evidence Gate",
        source_type="paper",
        section="Method",
        page_start=1,
        page_end=1,
        quote="Evidence must be relevant enough to cite.",
        rank_score=rank_score,
    )


def test_should_skip_research_retrieval_for_obvious_non_evidence_turns():
    assert should_skip_research_retrieval("谢谢") is True
    assert should_skip_research_retrieval("thanks!") is True
    assert should_skip_research_retrieval("继续") is True
    assert should_skip_research_retrieval("rewrite this paragraph") is True
    assert should_skip_research_retrieval("What does the paper conclude?") is False


def test_admit_evidence_hits_accepts_relevant_candidates():
    result = admit_evidence_hits([_hit(evidence_id=1, rank_score=MIN_EVIDENCE_RELEVANCE_SCORE + 0.01)])

    assert result.decision == "accepted"
    assert result.accepted_count == 1
    assert result.rejected_count == 0
    assert result.accepted_hits[0].evidence_id == 1
    assert result.to_dict()["threshold"] == MIN_EVIDENCE_RELEVANCE_SCORE


def test_admit_evidence_hits_rejects_weak_candidates():
    result = admit_evidence_hits([
        _hit(evidence_id=1, rank_score=MIN_EVIDENCE_RELEVANCE_SCORE / 10),
        _hit(evidence_id=2, rank_score=0.0),
    ])

    assert result.decision == "insufficient"
    assert result.accepted_count == 0
    assert result.rejected_count == 2
    assert result.highest_score == MIN_EVIDENCE_RELEVANCE_SCORE / 10
    assert result.accepted_hits == []
