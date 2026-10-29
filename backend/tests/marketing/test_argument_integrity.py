"""Captured Tally failure plus labelled synthetic cases; no live providers.

The captured strings below are a small subset of execution
905534e6392f442e927bc1a132458c1d, not freshly generated copy.
"""
from uuid import uuid4

import pytest

from app.knowledge.artifacts import (
    AudienceModel,
    BusinessProfile,
    Grounding,
    KnowledgeArtifacts,
    Segment,
)
from app.knowledge.corpus import SourceCorpus
from app.knowledge.ledger import Evidence, EvidenceKind, EvidenceLedger
from app.market.audience_research import (
    AudienceProblem,
    AudienceResearch,
    EvidenceReference,
    SourcedObservation,
)
from app.market.relevance import (
    INTERPRETATION_VERSION,
    CampaignReadiness,
    CampaignRecommendation,
    DossierState,
    RankedRelevanceItem,
    RecommendationState,
    RelevanceBand,
    RelevanceDossier,
    RelevanceStatus,
)
from app.marketing.briefs import ArgumentOption, CampaignBrief, EmailBrief
from app.marketing.contract import parse_contract
from app.marketing.intelligence import (
    adapt_researched_audience,
    build_campaign_intelligence,
    resolve_audience_research,
)
from app.marketing.request import CampaignRequest
from app.marketing.strategist import Strategist
from app.models.market import AudienceResearchRow
from tests.marketing.conftest import RoleScriptedProvider, make_session

TALLY_AUDIENCE = "The ops or no-code person on a small team whose intake form is step one of an automation nobody owns"
TALLY_PROBLEM = "After a Tally form submits to a webhook, the respondent cannot be reliably redirected or shown a conditional response from the automation tool; the connection appears to be lost once the platform returns its own 'accepted' acknowledgement."
TALLY_INVERSION = "Builders are advised to use the generic Webhook trigger module instead of the native Tally app module, because the native module simplifies the payload in a way that complicates handling it downstream."
TALLY_QUOTE = "Using the app, you’ll receive the data in a simplified version which is easier to handle within Make."
TALLY_SOURCE = "https://tally.so/help/webhooks"


def tally_case(state=DossierState.STALE):
    ledger = EvidenceLedger(entries=[
        Evidence(id="E21", kind=EvidenceKind.PRICE, claim="Webhooks are available for free to all Tally users.",
                 verbatim="Webhooks are available **for free** to all Tally users.", source=TALLY_SOURCE),
        Evidence(id="E33", kind=EvidenceKind.INTEGRATION,
                 claim="A Tally form can trigger automation platforms like Make, Zapier, or n8n, which then route the data to CRMs, billing tools, internal databases, or messaging apps.",
                 verbatim="A Tally form can trigger automation platforms like Make, Zapier or n8n.", source=TALLY_SOURCE),
    ])
    artifacts = KnowledgeArtifacts(business=BusinessProfile(company_name="Tally", what_it_does="an online form builder"),
        evidence=ledger, audience=AudienceModel(segments=[Segment(name=TALLY_AUDIENCE)]))
    research = AudienceResearch(audience_name=TALLY_AUDIENCE, candidate_kind="core", problems=[
        AudienceProblem(id="P1", statement=TALLY_PROBLEM, grounding=Grounding.GROUNDED,
                        evidence=[EvidenceReference(source_id="S1", quote="the automatic response message is (accepted)")]),
    ], incumbent_behaviour=[SourcedObservation(text=TALLY_INVERSION, grounding=Grounding.GROUNDED,
        evidence=[EvidenceReference(source_id="S3", quote=TALLY_QUOTE)])])
    row = AudienceResearchRow(brand_id=uuid4(), audience_key=TALLY_AUDIENCE.casefold(),
                             audience_name=TALLY_AUDIENCE, payload=research.model_dump(mode="json"))
    dossier = RelevanceDossier(interpretation_version=INTERPRETATION_VERSION,
        audience_research_id=row.id, audience_name=TALLY_AUDIENCE, audience_research_version=1,
        knowledge_id=uuid4(), knowledge_version=1, market_scan_id=uuid4(), market_scan_version=1,
        ranked_relevance=[RankedRelevanceItem(evidence_id="E33", band=RelevanceBand.LEAD,
                                              why="This is the platform connection described in the original run.")])
    match = resolve_audience_research(TALLY_AUDIENCE, [row])
    context = build_campaign_intelligence(selected_audience=TALLY_AUDIENCE, match=match,
        dossier_status=RelevanceStatus(audience_name=TALLY_AUDIENCE, status=state, dossier=dossier,
                                      stale_reasons=["interpretation_changed"] if state is DossierState.STALE else []),
        ledger=ledger)
    brief = CampaignBrief(reader_segment=TALLY_AUDIENCE, reader="An ops/no-code builder", promise="A form front end for your automation.", emails=[EmailBrief(
        single_idea="Tally is now available as a form front end for automations with a free webhook route.",
        felt_need=TALLY_PROBLEM, status_quo=TALLY_INVERSION,
        mechanism="The webhook solves this automation handover problem without polling or CSV exports.",
        belief_shift="The workflow no longer needs an owner.",
        objection="Nobody will maintain this pipeline.", evidence_ids=["E21", "E33"],
        call_to_action="Create a free form", next_step_evidence_ids=["E21", "E33"],
        next_step_value="Decide whether the form is worth wiring up to resolve this operational concern.",
    )])
    return artifacts, research, row, context, brief


@pytest.mark.parametrize("state", [DossierState.STALE, DossierState.CURRENT])
def test_captured_webhook_argument_loses_unlinked_problem_and_dependent_promises(state):
    artifacts, research, _, context, original = tally_case(state)
    result = Strategist(None)._normalize(original.model_copy(deep=True), parse_contract("Write 1 email"),
                                         artifacts, context)
    email = result.emails[0]
    assert email.felt_need == email.status_quo == email.why_it_fails == ""
    assert email.single_idea == artifacts.evidence.get("E33").claim
    assert email.mechanism == artifacts.evidence.get("E33").claim
    assert email.belief_shift == email.objection == ""
    assert email.call_to_action == original.emails[0].call_to_action
    assert email.next_step_value == ""
    assert email.argument_issue
    assert "operational concern" not in email.next_step_value
    assert "without polling" not in email.mechanism
    assert "without polling" not in result.promise
    assert any("does not establish" in item for item in email.must_not_say)
    assert any("separate setup paths" in item for item in email.must_not_say)
    assert context.problems[0].statement == research.problems[0].statement
    assert context.problems[0].evidence == research.problems[0].evidence
    assert original.emails[0].felt_need == TALLY_PROBLEM, "Historical input is not rewritten"


def test_captured_native_module_inversion_is_not_promoted_to_observed_status_quo():
    _, _, original_row, context, _ = tally_case()
    assert context.incumbent_behaviour[0].grounding == "inferred"
    assert context.incumbent_behaviour[0].evidence[0].quote == TALLY_QUOTE
    assert context.normalized_status_quo(TALLY_INVERSION) == ""
    assert any("reverse" in warning for warning in context.trace.validation_warnings)
    assert original_row.payload["incumbent_behaviour"][0]["grounding"] == "grounded"


def test_fixed_user_destination_is_preserved_without_an_invented_evaluation_payoff():
    artifacts, _, _, context, original = tally_case()
    email = Strategist(None)._normalize(original, parse_contract("Write 1 email"), artifacts, context,
        fixed_cta_url="https://tally.so/create").emails[0]
    assert email.call_to_action == "Create a free form"
    assert email.next_step_value == email.next_step_decision == ""
    assert email.next_step_evidence_ids == []
    assert "does not establish" in email.next_step_limit


def test_activation_without_a_problem_is_not_rewritten_into_a_pain_pitch():
    artifacts, _, _, context, original = tally_case()
    original.emails[0] = original.emails[0].model_copy(update={
        "felt_need": "", "status_quo": "", "why_it_fails": "",
        "single_idea": "Connect your first form to the documented workflow.",
        "mechanism": "New submissions can trigger Make, Zapier, or n8n.",
    })
    result = Strategist(None)._normalize(original.model_copy(deep=True), parse_contract("Write 1 email"), artifacts, context)
    assert result.emails[0].single_idea == original.emails[0].single_idea
    assert result.emails[0].mechanism == original.emails[0].mechanism
    assert result.emails[0].felt_need == ""
    assert result.emails[0].call_to_action == "Create a free form"


def test_synthetic_repair_argument_clears_invented_alternative_failure_but_keeps_supported_bridge():
    # Synthetic contrast: a repair-status capability does address the stated
    # problem, but the strategist invented CSV imports as the current method.
    artifacts, _, _, context, original = tally_case(DossierState.CURRENT)
    context.problems[0].statement = "Customers must call the shop to learn repair status."
    context.ranked_evidence[0].problem_ids = ["P1"]
    original.emails[0] = EmailBrief(single_idea="Show repair status before a customer needs to call.",
        felt_need=context.problems[0].statement, status_quo="They import a CSV every morning.",
        why_it_fails="The repeated CSV import leaves jobs unowned.",
        mechanism="A shared status board displays the repair stage.", evidence_ids=["E33"],
        alternative_arguments=[ArgumentOption(single_idea="Let a customer inspect the current repair stage.",
            felt_need=context.problems[0].statement, status_quo="An in-house spreadsheet needs daily imports.",
            why_it_fails="The spreadsheet is never maintained.", evidence_ids=["E33"])])
    artifacts.evidence.entries[1] = Evidence(id="E33", kind=EvidenceKind.FEATURE,
        claim="A shared board shows each repair stage.", verbatim="A shared board shows each repair stage.")
    email = Strategist(None)._normalize(original, parse_contract("Write 1 email"), artifacts, context).emails[0]
    assert email.felt_need == context.problems[0].statement
    assert email.status_quo == email.why_it_fails == ""
    assert email.mechanism == "A shared status board displays the repair stage."
    assert email.alternative_arguments[0].status_quo == email.alternative_arguments[0].why_it_fails == ""


@pytest.mark.asyncio
async def test_current_qualified_slice_reaches_strategy_and_effective_reader_without_an_extra_call():
    artifacts, research, row, context, original = tally_case(DossierState.CURRENT)
    # This test isolates scope propagation. A functional announcement needs no
    # unlinked pain; a genuinely invalid argument now earns one repair call.
    original.emails[0].felt_need = ""
    recommendation = CampaignRecommendation(state=RecommendationState.RECOMMENDED_NARROW, readiness=CampaignReadiness.GO_NARROW,
        eligible_subsegment="no-code automation agencies", recommended_next_action="Target only no-code automation agencies.",
        allowed_evidence_ids=artifacts.evidence.ids)
    dossier = RelevanceDossier(schema_version=2, interpretation_version=INTERPRETATION_VERSION,
        audience_research_id=row.id, audience_name=row.audience_name, audience_research_version=1,
        knowledge_id=uuid4(), knowledge_version=1, market_scan_id=uuid4(), market_scan_version=1,
        recommendation=recommendation)
    context = build_campaign_intelligence(selected_audience=row.audience_name,
        match=resolve_audience_research(row.audience_name, [row]),
        dossier_status=RelevanceStatus(audience_name=row.audience_name, status=DossierState.CURRENT, dossier=dossier),
        ledger=artifacts.evidence)
    provider = RoleScriptedProvider({"strategist": original.model_dump_json()})
    request = CampaignRequest(name="Launch", request="Write 1 email announcing the product",
                              cta_url="https://tally.so/")
    brief = await Strategist(make_session(provider)).build(request=request, artifacts=adapt_researched_audience(artifacts, research, context),
        corpus=SourceCorpus(), contract=parse_contract(request.request), chosen_segment=row.audience_name, intelligence=context)
    assert brief.reader_scope == context.trace.qualified_subsegment == "no-code automation agencies"
    assert "Qualified campaign scope" in brief.reader and brief.reader_scope in brief.reader
    assert brief.reader_scope in context.render_for_strategy()
    assert provider.calls_by_role["strategist"] == 1
    assert "Qualified campaign scope: no-code automation agencies" in provider.requests_for("strategist")[0].system_prompt


@pytest.mark.parametrize("name,claim", [
    ("SyntheticRepair", "The repair status board has a prebuilt accounting integration."),
    ("SyntheticSurvey", "New responses can be sent to an HTTP endpoint."),
])
def test_connection_route_constraints_are_source_driven_across_products(name, claim):
    artifacts = KnowledgeArtifacts(business=BusinessProfile(company_name=name), evidence=EvidenceLedger(entries=[
        Evidence(id="E1", kind=EvidenceKind.INTEGRATION, claim=claim, verbatim=claim),
    ]))
    brief = CampaignBrief(emails=[EmailBrief(single_idea=claim, evidence_ids=["E1"])])
    email = Strategist(None)._normalize(brief, parse_contract("Write 1 email"), artifacts).emails[0]
    assert any("separate setup paths" in item for item in email.must_not_say)


def test_reframing_duplicate_alternatives_does_not_buy_the_same_draft_twice():
    artifacts, _, _, context, original = tally_case()
    original.emails[0].alternative_arguments = [ArgumentOption(
        single_idea="A different unsupported promise about automatic ownership transfer.",
        felt_need=TALLY_PROBLEM, evidence_ids=["E33"],
    )]
    email = Strategist(None)._normalize(original, parse_contract("Write 1 email"), artifacts, context).emails[0]
    assert email.alternative_arguments == []
    assert any("no redundant draft" in item for item in context.trace.validation_warnings)
