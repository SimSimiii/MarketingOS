"""From a page on the open web to a fact a campaign may argue from.

This is the chain the proof hunter exists for, and each link is checked here
because breaking any one of them turns the feature into a list nobody can use:

    a hunt finds a quotation -> the user approves it -> it becomes ledger
    evidence -> the gaps are re-derived -> the preflight stops calling the
    campaign unprovable

The last link is the one that pays for the whole thing. The run that prompted
this work reported `attributions: 0` and "No customer names, quotes or case
studies found", and no rewrite has ever added a proof the material did not
contain.
"""

import pytest

from app.knowledge.artifacts import BusinessProfile, KnowledgeArtifacts
from app.knowledge.compiler import find_gaps
from app.knowledge.ledger import Evidence, EvidenceKind, EvidenceLedger
from app.market.proof import ProofCandidate, ProofHunter, ProofKind, next_evidence_id
from app.market.store import merge_proof
from app.marketing.preflight import assess
from tests.market.conftest import ScriptedProvider

QUOTE = "We switched to orqAgent and cut our review time from two days to twenty minutes."


def candidate(**overrides: object) -> ProofCandidate:
    values: dict = {
        "kind": ProofKind.TESTIMONIAL,
        "claim": "Ramp cut review time from two days to twenty minutes",
        "verbatim": QUOTE,
        "url": "https://ramp.example/engineering/agents",
        "attributed_to": "Ramp",
        "venue": "a customer's engineering blog",
        "confidence": 0.8,
    }
    values.update(overrides)
    return ProofCandidate(**values)


def bare_artifacts() -> KnowledgeArtifacts:
    """A business with plenty of facts about itself and nothing anybody else
    has said - the exact posture of the run that scored 4/10."""
    artifacts = KnowledgeArtifacts(
        business=BusinessProfile(company_name="orqAgent", what_it_does="agent orchestration"),
        evidence=EvidenceLedger(
            entries=[
                Evidence(
                    id="E1",
                    kind=EvidenceKind.METRIC,
                    claim="25 models across 9 providers",
                    verbatim="25 models across 9 providers.",
                ),
                Evidence(
                    id="E2",
                    kind=EvidenceKind.PRICE,
                    claim="1,500 free credits, no card",
                    verbatim="Start with 1,500 free credits. No card required.",
                ),
            ]
        ),
    )
    artifacts.gaps = find_gaps(artifacts)
    return artifacts


# --------------------------------------------------------------- the hunt


@pytest.mark.asyncio
async def test_a_hunt_keeps_only_what_it_can_quote_and_source(
    provider: ScriptedProvider, session
) -> None:
    """A candidate with no quotation licenses nothing, and one with no URL
    cannot be judged - the queue asks "is this sentence really on that page",
    and both halves have to be there."""
    provider.push(
        "proof_hunt",
        {
            "candidates": [
                {
                    "kind": "testimonial",
                    "claim": "Ramp cut review time",
                    "verbatim": QUOTE,
                    "url": "https://ramp.example/engineering/agents",
                    "attributed_to": "Ramp",
                    "venue": "a customer's engineering blog",
                    "confidence": 0.8,
                    "caveat": "the post is about their whole stack, not only this product",
                },
                {"kind": "mention", "claim": "people like it", "url": "https://x.example"},
                {"kind": "review", "claim": "good reviews", "verbatim": "Great tool."},
            ],
            "searched": ['"orqAgent" review'],
        },
    )

    hunt = await ProofHunter(session).hunt(BusinessProfile(company_name="orqAgent"))

    assert len(hunt.candidates) == 1
    assert hunt.candidates[0].attributed_to == "Ramp"
    assert hunt.candidates[0].caveat, "the caveat is what makes approval a ten-second decision"
    assert hunt.searched


@pytest.mark.asyncio
async def test_an_empty_hunt_is_a_finding(provider: ScriptedProvider, session) -> None:
    provider.push(
        "proof_hunt",
        {
            "candidates": [],
            "searched": ['"orqAgent"', "orqAgent review", "orqAgent alternatives"],
            "note": "Nothing outside their own site mentions this company yet.",
        },
    )

    hunt = await ProofHunter(session).hunt(BusinessProfile(company_name="orqAgent"))

    assert hunt.candidates == []
    assert hunt.note
    assert len(hunt.searched) == 3


# ------------------------------------------------------------- the chain


def test_approving_a_proof_closes_the_gap_that_blocked_the_campaign() -> None:
    artifacts = bare_artifacts()

    # Before: the compiler's own verdict on this business.
    assert any(gap.id == "G-proof" for gap in artifacts.gaps.unanswered)
    posture = assess(artifacts)
    assert not posture.has_proof
    assert "cannot be believed on someone else's word" in posture.summary()

    merged = merge_proof(artifacts, [candidate().as_evidence("P1")])

    # After: the gap is gone because it is derived, not patched.
    assert not any(gap.id == "G-proof" for gap in merged.gaps.unanswered)
    after = assess(merged)
    assert after.has_proof
    assert "third-party proof point(s) available to spend" in after.summary()
    # And the strategist is now told to spend it rather than to argue around
    # a hole.
    assert "[P1]" in after.render_for_strategy()


def test_an_approved_proof_is_licensed_by_the_evidence_gate() -> None:
    """The point of carrying the verbatim quotation: once approved, copy may
    use the words in it and the gate will not send them back."""
    from app.knowledge.corpus import SourceCorpus
    from app.knowledge.ledger import EvidenceIndex

    merged = merge_proof(bare_artifacts(), [candidate().as_evidence("P1")])
    index = EvidenceIndex(merged.evidence, SourceCorpus().text)

    assert not index.unsupported(
        "Ramp cut their review time from two days to twenty minutes."
    )
    # And a number nobody vouched for is still refused.
    assert index.unsupported("Ramp cut their review time by 94%.")


def test_proof_ids_never_collide_with_the_compilers() -> None:
    """The compiler renumbers E1..En on every recompile. An approved proof
    filed into that sequence would be silently reassigned to a different fact
    the next time the user uploads a page, and a shipped email's citation
    would start pointing somewhere else."""
    assert next_evidence_id(set()) == "P1"
    assert next_evidence_id({"E1", "E2", "P1"}) == "P2"
    assert next_evidence_id({"P1", "P3"}) == "P2"


def test_merging_is_idempotent_and_does_not_mutate_the_stored_set() -> None:
    """Artifacts are the compiler's output. A run reusing them must not find
    them changed under it by a decision made in the UI."""
    artifacts = bare_artifacts()
    evidence = candidate().as_evidence("P1")

    once = merge_proof(artifacts, [evidence])
    twice = merge_proof(once, [evidence])

    assert len(artifacts.evidence.entries) == 2, "the original is untouched"
    assert len(once.evidence.entries) == 3
    assert len(twice.evidence.entries) == 3


def test_a_found_proof_is_never_recorded_as_strong() -> None:
    """It is a sentence somebody else wrote on a page neither party controls.
    Strong is for a specific fact the company states and is accountable for."""
    from app.knowledge.ledger import EvidenceStrength

    assert candidate(confidence=0.95).as_evidence("P1").strength is EvidenceStrength.MODERATE
    assert candidate(confidence=0.4).as_evidence("P1").strength is EvidenceStrength.WEAK


def test_a_candidate_without_a_quote_is_not_usable() -> None:
    assert candidate().usable
    assert not candidate(verbatim="").usable
    assert not candidate(url="").usable
    assert not candidate(claim="  ").usable


def test_a_bare_domain_is_normalized_to_a_url() -> None:
    assert candidate(url="g2.com/products/orqagent").url.startswith("https://")
