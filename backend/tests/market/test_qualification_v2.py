"""Deterministic receipts at the V2 product/audience/company boundary."""

from uuid import uuid4

import pytest

import app.market.qualification as qualification_module
from app.knowledge.ledger import Evidence, EvidenceKind, EvidenceLedger
from app.market.audience_research import AudienceProblem, AudienceResearch
from app.market.capabilities import (
    CapabilityProfileDraft,
    CapabilityState,
    ClaimVisibility,
    ProductCapability,
    ProductCapabilityProfile,
    ProductClaim,
    derive_capability_profile,
    normalize_capability_profile,
)
from app.market.positioning import Territory
from app.market.qualification import (
    AudienceDefinition,
    AudienceExclusion,
    AudienceRequirement,
    CompanyCapabilityRequirement,
    CompanySignal,
    QualificationClass,
    SignalGrounding,
    UnmappedCompanyRequirement,
    qualify_company,
    stale_company_qualification,
)
from app.market.relevance import (
    FitVerdict,
    ProblemFit,
    QualifiedCompanySnapshot,
    RankedRelevanceItem,
    RecommendationState,
    RelevanceBand,
    RelevanceDossier,
    recommend_campaign,
)
from app.services import market_service


def _profile() -> ProductCapabilityProfile:
    return ProductCapabilityProfile(
        knowledge_id=uuid4(),
        knowledge_version=3,
        capabilities=[
            ProductCapability(id="text_chat_agent", label="Text agent", state="verified"),
            ProductCapability(id="per_client_configuration", label="Client config", state="verified"),
            ProductCapability(id="voice_telephony", label="Voice", state="unsupported"),
            ProductCapability(
                id="deep_vertical_integrations", label="Vertical integrations", state="unknown"
            ),
        ],
    )


def _definition() -> AudienceDefinition:
    return AudienceDefinition(
        required_structural_signals=[
            AudienceRequirement(code="founder_led", description="A working founder owns delivery"),
        ],
        required_workflow_signals=[
            AudienceRequirement(code="repeated_client_workflow"),
        ],
        required_product_capabilities=["text_chat_agent", "per_client_configuration"],
        hard_disqualifiers=[
            AudienceExclusion(
                code="agency_services",
                description="A services business is related but is not the target model.",
                outcome=QualificationClass.ADJACENT,
            )
        ],
        eligible_subsegments=["small founder-led operators with repeatable text workflows"],
        max_team_size=10,
    )


def _signal(code: str, value: str = "true") -> CompanySignal:
    return CompanySignal(
        code=code,
        value=value,
        grounding=SignalGrounding.DIRECT,
        quote=f"Published proof for {code}: {value}",
        source_identifier="https://example.test/about",
    )


def _requirement(
    capability_id: str, quote: str = "The company directly sells this required workflow."
) -> CompanyCapabilityRequirement:
    return CompanyCapabilityRequirement(
        capability_id=capability_id,
        evidence_state=SignalGrounding.DIRECT,
        quote=quote,
        source_url="https://example.test/product",
        reasoning="The published workflow requires the catalogued capability.",
    )


def _qualify(
    *signals: CompanySignal,
    verified: bool = True,
    requirements: list[CompanyCapabilityRequirement] | None = None,
    unmapped: list[UnmappedCompanyRequirement] | None = None,
    profile: ProductCapabilityProfile | None = None,
    definition: AudienceDefinition | None = None,
):
    return qualify_company(
        definition=definition or _definition(),
        profile=profile or _profile(),
        evidence=list(signals),
        requirements=requirements,
        unmapped_requirements=unmapped,
        site_verified=verified,
        pages_read=2 if verified else 0,
        reachable=True,
    )


def test_small_founder_led_text_workflow_is_qualified() -> None:
    result = _qualify(_signal("founder_led"), _signal("repeated_client_workflow"))

    assert result.classification is QualificationClass.QUALIFIED
    assert result.reason_codes == ["all_required_signals_verified"]


@pytest.mark.parametrize(
    "quote",
    [
        "answers phone calls",
        "answers calls for every practice",
        "an AI phone receptionist",
        "a voice agent for the front desk",
        "a phone system with agents handling every inbound call",
    ],
)
def test_profile_mapped_voice_requirement_is_excluded_for_every_company_wording(
    quote: str,
) -> None:
    result = _qualify(
        requirements=[_requirement("voice_telephony", quote)],
    )

    assert result.classification is QualificationClass.EXCLUDED
    assert result.reason_codes[0] == "unsupported_required_capability:voice_telephony"
    assert result.capability_matches[0].quote == quote
    assert result.capability_matches[0].product_capability_state is CapabilityState.UNSUPPORTED


def test_same_direct_requirement_is_unverified_when_profile_state_is_unknown() -> None:
    profile = _profile()
    profile.capability("voice_telephony").state = CapabilityState.UNKNOWN

    result = _qualify(
        requirements=[_requirement("voice_telephony", "answers phone calls")],
        profile=profile,
    )

    assert result.classification is QualificationClass.UNVERIFIED
    assert "unknown_required_capability:voice_telephony" in result.reason_codes
    assert result.hard_disqualifiers_triggered == []


def test_an_unrelated_profile_capability_uses_the_same_generic_mismatch_path() -> None:
    profile = ProductCapabilityProfile(
        knowledge_id=uuid4(),
        knowledge_version=1,
        capabilities=[
            ProductCapability(
                id="warehouse_robotics",
                label="Warehouse robotics runtime",
                state=CapabilityState.UNSUPPORTED,
            )
        ],
    )

    result = _qualify(
        requirements=[_requirement("warehouse_robotics")],
        profile=profile,
    )

    assert result.classification is QualificationClass.EXCLUDED
    assert result.reason_codes[0] == "unsupported_required_capability:warehouse_robotics"


def test_explicit_unmapped_requirement_is_unverified_not_an_invented_mismatch() -> None:
    result = _qualify(
        unmapped=[
            UnmappedCompanyRequirement(
                raw_requirement="practice-management-system integration",
                evidence_state=SignalGrounding.DIRECT,
                quote="Connects directly to the practice management system.",
                source_url="https://example.test/integrations",
            )
        ]
    )

    assert result.classification is QualificationClass.UNVERIFIED
    assert result.product_capability_fit.value == "unknown"
    assert result.hard_disqualifiers_triggered == []
    assert "unmapped_company_requirement" in result.reason_codes


def test_a_requirement_with_an_id_outside_the_profile_becomes_unmapped() -> None:
    result = _qualify(requirements=[_requirement("invented_capability_id")])

    assert result.classification is QualificationClass.UNVERIFIED
    assert result.capability_matches == []
    assert result.unmapped_requirements[0].raw_requirement == "invented_capability_id"
    assert result.product_capability_fit.value == "unknown"


def test_direct_capability_mismatch_overrides_missing_structural_evidence() -> None:
    result = _qualify(
        requirements=[_requirement("voice_telephony", "answers phone calls")]
    )

    assert result.audience_structure_fit.value == "unknown"
    assert result.evidence_completeness.value == "missing"
    assert result.classification is QualificationClass.EXCLUDED


def test_related_service_business_is_adjacent_when_the_definition_says_so() -> None:
    result = _qualify(
        _signal("founder_led"),
        _signal("repeated_client_workflow"),
        _signal("agency_services"),
    )

    assert result.classification is QualificationClass.ADJACENT
    assert "hard_disqualifier:agency_services" in result.reason_codes


def test_insufficient_evidence_alone_is_never_adjacent() -> None:
    result = _qualify(_signal("repeated_client_workflow"))

    assert result.classification is QualificationClass.UNVERIFIED
    assert "insufficient_direct_evidence_for_qualification" in result.reason_codes


def test_unreadable_site_is_unverified_and_never_qualified_from_a_guess() -> None:
    result = _qualify(
        CompanySignal(
            code="founder_led",
            grounding=SignalGrounding.INFERENCE,
            quote="Probably founder led",
        ),
        verified=False,
    )

    assert result.classification is QualificationClass.UNVERIFIED
    assert result.reason_codes == ["site_unreadable"]
    assert result.evidence[0].grounding is SignalGrounding.INFERENCE


def test_inferred_solo_or_founder_signal_cannot_satisfy_a_required_signal() -> None:
    result = _qualify(
        CompanySignal(
            code="founder_led",
            grounding=SignalGrounding.INFERENCE,
            quote="The page uses first-person language.",
        ),
        _signal("repeated_client_workflow"),
    )

    assert result.classification is QualificationClass.UNVERIFIED
    assert "required_signal_missing:founder_led" in result.reason_codes


def test_capability_profile_derives_positive_support_only_from_ledger_evidence() -> None:
    knowledge_id = uuid4()
    ledger = EvidenceLedger(
        entries=[
            Evidence(
                id="E-chat",
                kind=EvidenceKind.FEATURE,
                claim="A hosted text agent uses a reusable per-client configuration.",
                verbatim="Deploy a text agent with reusable per-client configuration.",
                source="product.md",
            )
        ]
    )

    profile = derive_capability_profile(
        ledger, knowledge_id=knowledge_id, knowledge_version=4
    )

    assert profile.state_of("text_chat_agent") is CapabilityState.VERIFIED
    assert profile.state_of("per_client_configuration") is CapabilityState.VERIFIED
    assert profile.capability("voice_telephony") is None
    assert profile.state_of("voice_telephony") is CapabilityState.UNKNOWN
    assert profile.capability("text_chat_agent").evidence[0].quote == ledger.entries[0].verbatim


def test_profile_editor_cannot_create_verified_capability_or_customer_claim_without_evidence() -> None:
    profile = normalize_capability_profile(
        CapabilityProfileDraft(
            capabilities=[
                ProductCapability(id="voice_telephony", label="Voice", state="verified")
            ],
            claims=[
                ProductClaim(
                    text="We support every phone system.",
                    visibility=ClaimVisibility.CUSTOMER,
                    evidence_ids=["not-in-ledger"],
                )
            ],
        ),
        ledger=EvidenceLedger(),
        knowledge_id=uuid4(),
        knowledge_version=1,
    )

    assert profile.state_of("voice_telephony") is CapabilityState.UNKNOWN
    assert profile.allowed_claims == []


def test_a_user_maintained_catalogue_is_not_filled_with_unrelated_default_ids() -> None:
    profile = normalize_capability_profile(
        CapabilityProfileDraft(
            capabilities=[
                ProductCapability(
                    id="warehouse_robotics",
                    label="Warehouse robotics runtime",
                    state=CapabilityState.UNSUPPORTED,
                    aliases=["picking robot"],
                )
            ]
        ),
        ledger=EvidenceLedger(),
        knowledge_id=uuid4(),
        knowledge_version=1,
    )

    assert [item.id for item in profile.capabilities] == ["warehouse_robotics"]


def test_company_identity_and_cache_change_with_profile_or_extractor_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = _profile()
    qualification = _qualify(
        _signal("founder_led"),
        _signal("repeated_client_workflow"),
        profile=profile,
    )
    company = QualifiedCompanySnapshot(
        prospect_id=uuid4(), name="Example", qualification=qualification
    )
    initial = market_service._qualification_fingerprint([company], profile=profile)

    changed_profile = profile.model_copy(update={"version": profile.version + 1})
    assert (
        market_service._qualification_fingerprint([company], profile=changed_profile)
        != initial
    )
    assert qualification.stale_reasons(changed_profile) == []

    changed_catalog = changed_profile.model_copy(deep=True)
    changed_catalog.capability("text_chat_agent").description = "A newly scoped capability"
    stale = stale_company_qualification(qualification, changed_catalog)
    assert stale.classification is QualificationClass.UNVERIFIED
    assert "capability_catalog_changed" in stale.reason_codes

    monkeypatch.setattr(
        qualification_module,
        "COMPANY_REQUIREMENT_EXTRACTOR_VERSION",
        qualification.identity.requirement_extractor_version + 1,
    )
    assert "company_requirement_extractor_changed" in qualification.stale_reasons(profile)
    monkeypatch.setattr(
        market_service,
        "COMPANY_REQUIREMENT_EXTRACTOR_VERSION",
        qualification.identity.requirement_extractor_version + 1,
    )
    assert market_service._qualification_fingerprint([company], profile=profile) != initial


def _dossier(*, territory: Territory = Territory.OPEN) -> RelevanceDossier:
    return RelevanceDossier(
        schema_version=2,
        audience_research_id=uuid4(),
        audience_name="Founder-led service operators",
        audience_research_version=1,
        knowledge_id=uuid4(),
        knowledge_version=1,
        market_scan_id=uuid4(),
        market_scan_version=1,
        ranked_relevance=[
            RankedRelevanceItem(
                evidence_id="E-allowed",
                band=RelevanceBand.LEAD,
                why="Direct fit",
                problem_ids=["P1"],
                territory=Territory.OPEN,
            ),
            RankedRelevanceItem(
                evidence_id="E-withheld",
                band=RelevanceBand.WITHHOLD,
                why="Do not use",
                problem_ids=["P1"],
                territory=territory,
            ),
        ],
        problem_fits=[
            ProblemFit(
                problem_id="P1",
                verdict=FitVerdict.SOLVED,
                evidence_ids=["E-allowed"],
                capability_ids=["text_chat_agent"],
                why="The verified text agent addresses the workflow.",
            )
        ],
    )


def _ledger() -> EvidenceLedger:
    return EvidenceLedger(
        entries=[
            Evidence(
                id="E-allowed",
                kind=EvidenceKind.FEATURE,
                claim="Reusable text agents can be configured per client.",
                verbatim="Configure a reusable text agent for each client.",
                source="product.md",
            ),
            Evidence(
                id="E-withheld",
                kind=EvidenceKind.FEATURE,
                claim="The product handles voice calls.",
                verbatim="An experimental voice demo is shown.",
                source="prototype.md",
            ),
        ]
    )


def test_recommendation_excludes_withheld_evidence_from_writer_allowlist() -> None:
    ledger = _ledger()
    profile = derive_capability_profile(ledger, knowledge_id=uuid4(), knowledge_version=1)
    research = AudienceResearch(
        audience_name="Founder-led service operators",
        candidate_kind="core",
        definition=AudienceDefinition(),
        problems=[AudienceProblem(id="P1", statement="Repeated setup work")],
    )

    result = recommend_campaign(
        _dossier(), profile=profile, research=research, companies=[], ledger=ledger
    )

    assert result.state is RecommendationState.RECOMMENDED
    assert "E-allowed" in result.allowed_evidence_ids
    assert "E-withheld" not in result.allowed_evidence_ids
    assert "E-withheld" in result.forbidden_evidence_ids
    assert "The product handles voice calls." in result.forbidden_claims


def test_recommendation_excludes_contested_evidence_even_when_ranked_support() -> None:
    ledger = _ledger()
    profile = derive_capability_profile(ledger, knowledge_id=uuid4(), knowledge_version=1)
    research = AudienceResearch(
        audience_name="Founder-led service operators",
        candidate_kind="core",
        problems=[AudienceProblem(id="P1", statement="Repeated setup work")],
    )
    dossier = _dossier()
    dossier.ranked_relevance[1] = dossier.ranked_relevance[1].model_copy(
        update={"band": RelevanceBand.SUPPORT, "territory": Territory.CONTESTED}
    )

    result = recommend_campaign(
        dossier, profile=profile, research=research, companies=[], ledger=ledger
    )

    assert "E-withheld" in result.forbidden_evidence_ids
    assert "E-withheld" not in result.allowed_evidence_ids


def test_required_unsupported_capability_forces_no_go_even_with_positive_problem_fit() -> None:
    ledger = _ledger()
    profile = derive_capability_profile(ledger, knowledge_id=uuid4(), knowledge_version=1)
    research = AudienceResearch(
        audience_name="Voice-first dental practices",
        candidate_kind="adjacent",
        definition=AudienceDefinition(required_product_capabilities=["full_saas_backend"]),
        problems=[AudienceProblem(id="P1", statement="Inbound calls")],
    )

    result = recommend_campaign(
        _dossier(), profile=profile, research=research, companies=[], ledger=ledger
    )

    assert result.state is RecommendationState.NOT_RECOMMENDED
    assert result.readiness == "NO_GO"
    assert any("full_saas_backend" in reason for reason in result.reasons)


def test_company_groups_are_persistable_recommendation_inputs() -> None:
    ledger = _ledger()
    profile = derive_capability_profile(ledger, knowledge_id=uuid4(), knowledge_version=1)
    agency = _qualify(
        _signal("founder_led"), _signal("repeated_client_workflow"), _signal("agency_services")
    )
    research = AudienceResearch(
        audience_name="Founder-led service operators",
        candidate_kind="core",
        problems=[AudienceProblem(id="P1", statement="Repeated setup work")],
    )

    result = recommend_campaign(
        _dossier(),
        profile=profile,
        research=research,
        companies=[
            QualifiedCompanySnapshot(
                prospect_id=uuid4(), name="Example Agency", qualification=agency
            )
        ],
        ledger=ledger,
    )

    assert result.state is RecommendationState.DISCOVERY_ONLY
    assert [item.name for item in result.adjacent_companies] == ["Example Agency"]
