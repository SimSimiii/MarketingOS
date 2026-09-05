"""The claim contract: what one campaign may spend, and what it may not.

Every test here is scripted-provider free and calls no model. The contract is
arithmetic over persisted facts on purpose - if any of this needed a model to
decide it, an operator could not re-derive a row by hand.
"""

from uuid import uuid4

from app.knowledge.artifacts import Objection
from app.knowledge.ledger import Evidence, EvidenceKind, EvidenceLedger
from app.market.audience_research import AudienceProblem, AudienceResearch
from app.market.capabilities import (
    CapabilityEvidence,
    CapabilityState,
    ClaimVisibility,
    ProductCapability,
    ProductCapabilityProfile,
    ProductClaim,
    ScopeBoundary,
)
from app.market.claims import ClaimAxis
from app.market.positioning import AxisReading, PositioningMap, Territory
from app.market.relevance import (
    CampaignReadiness,
    CampaignRecommendation,
    ClaimContract,
    ContractClaim,
    FitVerdict,
    ObjectionProposal,
    ProblemFit,
    RankedRelevanceItem,
    RankedRelevanceProposal,
    RecommendationState,
    RelevanceBand,
    RelevanceDossier,
    RelevanceProposal,
    build_claim_contract,
    claim_identity,
    normalize_dossier,
    recommend_campaign,
)
from app.marketing.intelligence import (
    AudienceResolution,
    CampaignIntelligence,
    CampaignIntelligenceTrace,
    DossierPosture,
)

# --- fixtures -----------------------------------------------------------------
#
# One ledger row per behaviour under test: a relevant fact, a contested price,
# two facts the dossier ranked WITHHOLD, and one true fact nothing ever ranked.


def ledger() -> EvidenceLedger:
    return EvidenceLedger(
        entries=[
            Evidence(
                id="E-relevant",
                kind=EvidenceKind.METRIC,
                claim="Cuts warranty triage from 40 minutes to 9 seconds",
                verbatim="Warranty triage fell from 40 minutes to 9 seconds.",
                source="case study",
            ),
            Evidence(
                id="E-price",
                kind=EvidenceKind.PRICE,
                claim="Pro is $29 per month",
                verbatim="Pro is $29 per month.",
                source="pricing",
            ),
            Evidence(
                id="E-models",
                kind=EvidenceKind.FEATURE,
                claim="25 models across 9 providers",
                verbatim="25 models across 9 providers.",
                source="docs",
            ),
            Evidence(
                id="E-latency",
                kind=EvidenceKind.METRIC,
                claim="Median latency is 200ms",
                verbatim="Median latency is 200ms.",
                source="docs",
            ),
            Evidence(
                id="E-unranked",
                kind=EvidenceKind.FEATURE,
                claim="There is a dark mode",
                verbatim="There is a dark mode.",
                source="site",
            ),
        ]
    )


def ranked() -> list[RankedRelevanceItem]:
    return [
        RankedRelevanceItem(
            evidence_id="E-relevant",
            band=RelevanceBand.LEAD,
            why="Direct fit for the morning hour this audience loses.",
            problem_ids=["P1"],
            territory=Territory.OPEN,
        ),
        RankedRelevanceItem(
            evidence_id="E-price",
            band=RelevanceBand.SUPPORT,
            why="Price is the second question they ask.",
            problem_ids=["P1"],
            territory=Territory.CONTESTED,
        ),
        RankedRelevanceItem(
            evidence_id="E-models",
            band=RelevanceBand.WITHHOLD,
            why="Breadth reads as unfocused to this buyer.",
            problem_ids=["P1"],
            territory=Territory.OPEN,
        ),
        RankedRelevanceItem(
            evidence_id="E-latency",
            band=RelevanceBand.WITHHOLD,
            why="Milliseconds are not the unit this buyer feels.",
            problem_ids=["P1"],
            territory=Territory.OPEN,
        ),
    ]


def fits() -> list[ProblemFit]:
    return [
        ProblemFit(
            problem_id="P1",
            verdict=FitVerdict.SOLVED,
            evidence_ids=["E-relevant"],
            why="The metric is the problem, measured.",
        )
    ]


def claims() -> list[ProductClaim]:
    """One customer-visible claim per ledger row.

    This mirrors what `derive_capability_profile` actually produces, which is
    the whole reason the allowed set used to be the entire ledger.
    """
    return [
        ProductClaim(
            text=entry.claim,
            visibility=ClaimVisibility.CUSTOMER,
            evidence_ids=[entry.id],
            reason="Licensed by the current Evidence Ledger.",
        )
        for entry in ledger().entries
    ]


def profile(
    *,
    product_claims: list[ProductClaim] | None = None,
    capabilities: list[ProductCapability] | None = None,
    constraints: list[ScopeBoundary] | None = None,
) -> ProductCapabilityProfile:
    return ProductCapabilityProfile(
        knowledge_id=uuid4(),
        knowledge_version=1,
        capabilities=capabilities or [],
        constraints=constraints or [],
        claims=claims() if product_claims is None else product_claims,
    )


def contract(**kwargs) -> ClaimContract:
    return build_claim_contract(
        profile=kwargs.pop("profile", None) or profile(**kwargs),
        ledger=ledger(),
        ranked=ranked(),
        fits=fits(),
    )


def research() -> AudienceResearch:
    return AudienceResearch(
        audience_name="Repair shops answering warranty requests",
        candidate_kind="adjacent",
        problems=[
            AudienceProblem(
                id="P1",
                statement="Repeat warranty questions consume the first hour of the day.",
                cost="one hour every morning",
            )
        ],
    )


def positioning() -> PositioningMap:
    return PositioningMap(
        readings=[
            AxisReading(axis=ClaimAxis.SPEED, territory=Territory.OPEN),
            AxisReading(axis=ClaimAxis.PRICE, territory=Territory.CONTESTED),
        ],
        rivals_profiled=2,
    )


def texts(rows: list[ContractClaim]) -> set[str]:
    return {row.text for row in rows}


# --- 1. forbidden beats allowed ----------------------------------------------


def test_a_claim_that_is_both_allowed_and_forbidden_resolves_as_forbidden_only():
    """The same fact arriving down two paths must land in exactly one set.

    Here the ledger licenses "cuts warranty triage..." as a customer claim
    while the capability that fact establishes was never verified. Both are
    true statements about the input; only one of them may reach a writer.
    """
    result = contract(
        capabilities=[
            ProductCapability(
                id="triage_automation",
                label="automated warranty triage",
                state=CapabilityState.UNKNOWN,
                evidence=[
                    CapabilityEvidence(
                        evidence_id="E-relevant",
                        claim="Cuts warranty triage from 40 minutes to 9 seconds",
                        quote="Warranty triage fell from 40 minutes to 9 seconds.",
                    )
                ],
            )
        ]
    )

    identity = claim_identity("automated warranty triage", ["E-relevant"])
    assert identity in result.forbidden_ids
    assert identity not in result.allowed_ids
    assert identity not in result.withheld_ids
    # And the claim text itself never reaches the campaign-safe set.
    assert "Cuts warranty triage from 40 minutes to 9 seconds" not in texts(
        result.campaign_allowed_claims
    )
    assert result.conflicts() == []


def test_the_resolution_is_recorded_rather_than_silent():
    result = contract(
        constraints=[
            ScopeBoundary(id="no_voice", statement="Cuts warranty triage from 40 minutes to 9 seconds")
        ]
    )

    assert any("forbidden won" in warning for warning in result.warnings)


# --- 2. contested pricing ----------------------------------------------------


def test_contested_pricing_evidence_cannot_become_campaign_safe():
    result = contract()

    assert "Pro is $29 per month" not in texts(result.campaign_allowed_claims)
    assert "Pro is $29 per month" in texts(result.withheld_claims)
    held = next(row for row in result.withheld_claims if row.text == "Pro is $29 per month")
    assert "Contested territory" in held.reason


def test_contested_pricing_evidence_cannot_license_an_objection_answer():
    """A price answer sourced from contested ground is not an answer.

    The stripping has to happen inside `normalize_dossier`, while objections
    are still being built - the recommendation runs afterwards and would only
    ever find an answer that already reads as licensed.
    """
    proposal = RelevanceProposal(
        ranked_relevance=[
            RankedRelevanceProposal(
                evidence_id="E-price",
                band=RelevanceBand.SUPPORT,
                why="Price is the second question they ask.",
                problem_ids=["P1"],
            )
        ],
        segment_objections=[
            ObjectionProposal(
                objection="This will cost more than the hour it saves.",
                answer="It is $29 per month, well under the hour it returns.",
                evidence_ids=["E-price"],
            )
        ],
    )

    dossier = normalize_dossier(
        proposal,
        ledger=ledger(),
        research=research(),
        positioning=positioning(),
        knowledge_id=uuid4(),
        knowledge_version=1,
        research_id=uuid4(),
        research_version=1,
        market_scan_id=uuid4(),
        market_scan_version=1,
    )

    answered = dossier.segment_objections[0]
    assert answered.answer == ""
    assert answered.evidence_ids == []
    assert any("contested" in warning.lower() for warning in dossier.validation_warnings)


# --- 3. withheld stays withheld ----------------------------------------------


def test_withheld_model_count_and_latency_stay_out_of_campaign_safe_claims():
    result = contract()
    safe = texts(result.campaign_allowed_claims)

    assert "25 models across 9 providers" not in safe
    assert "Median latency is 200ms" not in safe
    assert {"25 models across 9 providers", "Median latency is 200ms"} <= texts(
        result.withheld_claims
    )
    # Withheld is not a prohibition. These may well be true.
    assert "25 models across 9 providers" not in texts(result.forbidden_claims)


def test_irrelevant_product_truth_is_not_bulk_added():
    """A fact nothing ranked and no fit uses is true, and not this campaign's."""
    result = contract()

    assert "There is a dark mode" not in texts(result.campaign_allowed_claims)
    held = next(row for row in result.withheld_claims if row.text == "There is a dark mode")
    assert held.reason == "No addressed or partial problem for this audience uses it."
    # It is still on the record as product truth.
    assert "There is a dark mode" in texts(result.verified_product_claims)


def test_evidence_without_a_customer_copy_licence_cannot_be_campaign_safe():
    internal = [
        ProductClaim(
            text="Cuts warranty triage from 40 minutes to 9 seconds",
            visibility=ClaimVisibility.INTERNAL,
            evidence_ids=["E-relevant"],
        )
    ]
    result = contract(product_claims=internal)

    assert result.campaign_allowed_claims == []
    held = result.withheld_claims[0]
    assert held.reason == "Not licensed for customer-facing copy."


# --- 4. the good path still works --------------------------------------------


def test_relevant_licensed_evidence_still_reaches_campaign_safe_claims():
    result = contract()

    assert texts(result.campaign_allowed_claims) == {
        "Cuts warranty triage from 40 minutes to 9 seconds"
    }
    assert result.allowed_evidence_ids == ["E-relevant"]


def test_a_claim_survives_only_if_every_id_it_rests_on_survives():
    """Partial survival was the pricing bug: one good id carried a bad one in."""
    mixed = [
        ProductClaim(
            text="Fast, and $29 per month",
            visibility=ClaimVisibility.CUSTOMER,
            evidence_ids=["E-relevant", "E-price"],
        )
    ]
    result = contract(product_claims=mixed)

    assert result.campaign_allowed_claims == []
    assert "Fast, and $29 per month" in texts(result.withheld_claims)


# --- 5. the invariant --------------------------------------------------------


def test_allowed_forbidden_and_withheld_are_pairwise_disjoint():
    result = contract(
        capabilities=[
            ProductCapability(
                id="voice",
                label="voice calls",
                state=CapabilityState.UNSUPPORTED,
                evidence=[
                    CapabilityEvidence(
                        evidence_id="E-latency", claim="Median latency is 200ms", quote="200ms."
                    )
                ],
            )
        ],
        constraints=[ScopeBoundary(id="no_voice", statement="Never promise voice support.")],
    )

    assert result.allowed_ids & result.forbidden_ids == set()
    assert result.allowed_ids & result.withheld_ids == set()
    assert result.forbidden_ids & result.withheld_ids == set()
    assert result.conflicts() == []


def test_claim_sets_are_deduplicated_by_identity():
    duplicated = claims() + claims()
    result = contract(product_claims=duplicated)

    ids = [row.id for row in result.campaign_allowed_claims]
    assert ids == list(dict.fromkeys(ids))
    assert len(result.campaign_allowed_claims) == 1


def test_conflicts_reports_an_overlap_it_did_not_build():
    """The invariant is checkable on a contract from anywhere, not just ours."""
    shared = ContractClaim(id="evidence:E-relevant", text="Both at once")
    hand_built = ClaimContract(
        campaign_allowed_claims=[shared], forbidden_claims=[shared]
    )

    assert hand_built.conflicts() == [
        "Claim 'evidence:E-relevant' is in both allowed and forbidden claims."
    ]


# --- 6. what the writer is handed --------------------------------------------


def writer_context(recommendation: CampaignRecommendation) -> CampaignIntelligence:
    return CampaignIntelligence(
        selected_audience="Repair shops answering warranty requests",
        recommendation_state=recommendation.state,
        readiness=recommendation.readiness,
        recommendation_reasons=list(recommendation.reasons),
        allowed_claims=list(recommendation.allowed_claims),
        forbidden_claims=list(recommendation.forbidden_claims),
        withheld_claims=[
            row.text for row in (recommendation.claim_contract or ClaimContract()).withheld_claims
        ],
        claim_contract=recommendation.claim_contract,
        trace=CampaignIntelligenceTrace(
            selected_audience="Repair shops answering warranty requests",
            audience_resolution_status=AudienceResolution.LOADED,
            dossier_status=DossierPosture.CURRENT,
            dossier_schema_version=2,
        ),
    )


def recommendation() -> CampaignRecommendation:
    dossier = RelevanceDossier(
        schema_version=2,
        audience_research_id=uuid4(),
        audience_name="Repair shops answering warranty requests",
        audience_research_version=1,
        knowledge_id=uuid4(),
        knowledge_version=1,
        market_scan_id=uuid4(),
        market_scan_version=1,
        ranked_relevance=ranked(),
        problem_fits=fits(),
    )
    return recommend_campaign(
        dossier, profile=profile(), research=research(), companies=[], ledger=ledger()
    )


def test_the_writer_receives_campaign_safe_claims_and_not_the_whole_ledger():
    rendered = writer_context(recommendation()).render_for_strategy()

    assert "Cuts warranty triage from 40 minutes to 9 seconds" in rendered
    # Everything true, ranked away, and not this campaign's to spend.
    for withheld in ("25 models across 9 providers", "Median latency is 200ms", "dark mode"):
        assert withheld not in rendered
    assert "Pro is $29 per month" not in rendered


def test_the_writer_is_told_the_allowed_set_is_exhaustive():
    rendered = writer_context(recommendation()).render_for_strategy()

    assert "Campaign-safe product claims:" in rendered
    assert "Anything not listed is unavailable to you" in rendered


# --- 7. one label ------------------------------------------------------------


def test_the_recommendation_is_rendered_once_not_twice():
    """`state` and `readiness` are one verdict under two names.

    Rendering both produced "NOT RECOMMENDEDNO GO", which reads as two
    separate findings that happen to agree.
    """
    result = recommendation()
    rendered = writer_context(result).render_for_strategy()

    assert rendered.count(f"Campaign recommendation: {result.state}") == 1
    assert str(result.readiness) not in rendered
    assert "RECOMMENDEDGO" not in rendered.replace(" ", "")


# --- 9. legacy payloads ------------------------------------------------------


def test_a_v1_dossier_without_a_recommendation_still_loads():
    payload = {
        "schema_version": 1,
        "audience_research_id": str(uuid4()),
        "audience_name": "Repair shops",
        "audience_research_version": 1,
        "knowledge_id": str(uuid4()),
        "knowledge_version": 1,
        "market_scan_id": str(uuid4()),
        "market_scan_version": 1,
    }

    loaded = RelevanceDossier.model_validate(payload)

    assert loaded.schema_version == 1
    assert loaded.recommendation is None


def test_a_legacy_v2_recommendation_without_a_contract_still_loads():
    """Persisted before the contract existed. It must parse, not migrate."""
    loaded = CampaignRecommendation.model_validate(
        {
            "state": "RECOMMENDED",
            "readiness": "GO",
            "allowed_claims": ["Pro is $29 per month"],
            "forbidden_claims": ["Pro is $29 per month"],
        }
    )

    assert loaded.claim_contract is None
    assert loaded.state is RecommendationState.RECOMMENDED
    assert loaded.readiness is CampaignReadiness.GO


def test_a_legacy_overlap_is_tightened_when_it_reaches_the_writer():
    """No contract to trust, so the overlap is resolved on the safe side."""
    from app.marketing.intelligence import _add_dossier

    dossier = RelevanceDossier(
        schema_version=2,
        audience_research_id=uuid4(),
        audience_name="Repair shops",
        audience_research_version=1,
        knowledge_id=uuid4(),
        knowledge_version=1,
        market_scan_id=uuid4(),
        market_scan_version=1,
        recommendation=CampaignRecommendation(
            state=RecommendationState.RECOMMENDED,
            readiness=CampaignReadiness.GO,
            allowed_claims=["Pro is $29 per month", "Cuts warranty triage"],
            forbidden_claims=["Pro is $29 per month"],
        ),
    )
    context = CampaignIntelligence(
        selected_audience="Repair shops",
        trace=CampaignIntelligenceTrace(
            selected_audience="Repair shops",
            audience_resolution_status=AudienceResolution.LOADED,
        ),
    )

    _add_dossier(context, dossier, ledger())

    assert context.claim_contract is None
    assert context.allowed_claims == ["Cuts warranty triage"]
    assert any("forbidden won" in item for item in context.trace.validation_warnings)


def test_objections_without_contested_evidence_keep_their_answers():
    """The stripping is targeted; an ordinary licensed answer survives."""
    proposal = RelevanceProposal(
        ranked_relevance=[
            RankedRelevanceProposal(
                evidence_id="E-relevant",
                band=RelevanceBand.LEAD,
                why="Direct fit for the hour they lose.",
                problem_ids=["P1"],
            )
        ],
        segment_objections=[
            ObjectionProposal(
                objection="Triage cannot be automated for warranty work.",
                answer="Warranty triage fell from 40 minutes to 9 seconds.",
                evidence_ids=["E-relevant"],
            )
        ],
    )

    dossier = normalize_dossier(
        proposal,
        ledger=ledger(),
        research=research(),
        positioning=positioning(),
        knowledge_id=uuid4(),
        knowledge_version=1,
        research_id=uuid4(),
        research_version=1,
        market_scan_id=uuid4(),
        market_scan_version=1,
    )

    answered = dossier.segment_objections[0]
    assert isinstance(answered, Objection)
    assert answered.answer == "Warranty triage fell from 40 minutes to 9 seconds."
    assert answered.evidence_ids == ["E-relevant"]
