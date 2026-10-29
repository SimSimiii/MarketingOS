"""General contracts plus captured failure patterns; no live provider calls."""

import json
from uuid import uuid4

import pytest

from app.knowledge.artifacts import CallToAction, KnowledgeArtifacts, OfferSheet
from app.knowledge.corpus import SourceCorpus
from app.knowledge.decision_context import select_evidence
from app.knowledge.ledger import Evidence, EvidenceContext, EvidenceKind, EvidenceLedger
from app.market.material_research import MaterialRecovery
from app.market.relevance import DossierEvidence, DossierState, _product_context
from app.marketing.briefs import ArgumentOption
from app.marketing.contract import parse_contract
from app.marketing.exceptions import StrategyError
from app.marketing.intent import CampaignIntent, infer_intent
from app.marketing.request import CampaignRequest
from app.marketing.strategist import Strategist, _resolve_proposition_action
from app.marketing.substantiation import Substantiation, assess_text
from tests.marketing.conftest import (
    RoleScriptedProvider,
    artifacts_fixture,
    campaign_brief,
    make_session,
)
from tests.marketing.test_argument_integrity import tally_case


@pytest.mark.parametrize("prompt,objective", [
    ("Announce the launch to non-buyers", "announcement"),
    ("Write a cold acquisition email", "acquisition"),
    ("Help with onboarding", "activation"),
    ("Abandoned cart recovery", "recovery"),
    ("A newsletter for our audience", "nurture"),
    ("Explain our service", "custom"),
])
def test_six_intents_do_not_invent_launch_facts_or_relationship(prompt, objective):
    intent = infer_intent(prompt)
    assert intent.objective == objective
    assert intent.announcement == intent.reason_now == ""
    assert intent.reader_relationship == ("cold" if "cold" in prompt else "unknown")
    assert intent.objective_source == "inferred"


@pytest.mark.parametrize("destination,licensed", [
    ("https://example.com/product", True),
    ("https://invented.example/demo", False),
])
def test_action_without_url_preserves_only_a_licensed_selected_source(destination, licensed):
    action = CallToAction(label="Inspect the product")
    artifacts = KnowledgeArtifacts(
        offer=OfferSheet(calls_to_action=[action]),
        evidence=EvidenceLedger(entries=[Evidence(
            id="E1", kind=EvidenceKind.FEATURE, claim="Product has pockets",
            verbatim="Product has pockets", source="https://example.com/product",
        )]),
    )
    argument = ArgumentOption(action_id=action.reference_id, call_to_action=action.label,
                              next_step_url=destination, evidence_ids=["E1"])
    resolved = _resolve_proposition_action(argument, artifacts, "")
    assert resolved.next_step_url == (destination if licensed else "")
    assert bool(resolved.argument_issue) is not licensed


def test_action_destination_and_user_fixed_url_still_take_precedence():
    action = CallToAction(label="Inspect the product", url="https://example.com/product")
    artifacts = KnowledgeArtifacts(offer=OfferSheet(calls_to_action=[action]))
    argument = ArgumentOption(action_id=action.reference_id,
                              next_step_url="https://invented.example/demo")
    assert _resolve_proposition_action(argument, artifacts, "").next_step_url == action.url
    assert _resolve_proposition_action(argument, artifacts, "https://example.com/launch").next_step_url == "https://example.com/launch"


def test_matching_action_label_keeps_canonical_url_over_a_model_invention():
    action = CallToAction(label="Inspect the product", url="https://example.com/product")
    artifacts = KnowledgeArtifacts(offer=OfferSheet(calls_to_action=[action]))
    argument = ArgumentOption(call_to_action=action.label, next_step_url="https://invented.example/demo")
    resolved = _resolve_proposition_action(argument, artifacts, "")
    assert resolved.next_step_url == action.url
    assert not resolved.argument_issue


def test_exact_unique_next_step_source_can_resolve_a_documentation_destination():
    artifacts = KnowledgeArtifacts(evidence=EvidenceLedger(entries=[Evidence(
        id="E1", kind=EvidenceKind.FEATURE, claim="The settings page shows the connector state.",
        verbatim="The settings page shows the connector state.", source="https://example.com/settings",
    )]))
    argument = ArgumentOption(call_to_action="Inspect settings", evidence_ids=["E1"], next_step_evidence_ids=["E1"])
    assert _resolve_proposition_action(argument, artifacts, "").next_step_url == "https://example.com/settings"
    argument.evidence_ids = []
    assert _resolve_proposition_action(argument, artifacts, "").next_step_url == ""


def test_sender_name_and_unrelated_number_are_not_eight_testimonial_attributions():
    ledger = [Evidence(id=f"E{i}", kind=EvidenceKind.FEATURE,
                       claim="Glint supports forms", verbatim="Use Glint to build forms.") for i in range(2)]
    ledger += [Evidence(id=f"T{i}", kind=EvidenceKind.TESTIMONIAL,
                        claim="A customer result", verbatim=f'"Glint saved 10 hours." — Customer{i}') for i in range(8)]
    result = assess_text("Try Glint. This endpoint has a 10 second response limit.", ledger[2:], ledger)
    assert result.attributions == 0
    assert result.carried == ()


def test_lexical_hints_do_not_veto_a_rewrite_without_explicit_support_loss():
    before = Substantiation(carried=("E1",), attributions=2, explicit=())
    after = Substantiation(explicit=())
    assert not after.loses_explicit_support(before)
    assert Substantiation(explicit=()).loses_explicit_support(Substantiation(explicit=("Q1",)))
    assert not Substantiation().loses_explicit_support(Substantiation(carried=("E1",), attributions=8))


def test_a_sender_name_never_counts_as_an_attribution_even_without_other_product_facts():
    fact = Evidence(id="T1", kind=EvidenceKind.TESTIMONIAL,
                    claim="A customer praises Glint", verbatim='"Glint made our work easier." — Marta')
    assert assess_text("Try Glint today.", [fact], [fact], company_name="Glint").attributions == 0


def test_source_scope_survives_dossier_input_and_persisted_reference():
    fact = Evidence(id="E1", kind=EvidenceKind.PRICE, claim="Annual plan includes uploads",
                    verbatim="Uploads are included with the annual plan.", source="https://example.com/pricing",
                    document_id="doc-7", context=EvidenceContext(subject="Example", conditions="annual billing",
                    limitations="not the separate price of uploads", temporal_scope="captured 2026-10-17"))
    record = DossierEvidence.of(fact)
    assert record.document_id == "doc-7"
    assert record.context == fact.context
    context = json.loads(_product_context(KnowledgeArtifacts(evidence=EvidenceLedger(entries=[fact])), uuid4(), 1))
    item = context["selected_evidence_ledger"][0]
    assert item["context"]["conditions"] == "annual billing"
    assert item["document_id"] == "doc-7"


def test_context_selection_is_order_invariant_and_never_discards_assigned_limits():
    facts = [Evidence(id=f"E{i:02}", kind=EvidenceKind.FEATURE, claim=f"Feature {i}",
                      verbatim=f"Feature {i} is supported.", source="https://example.com/features") for i in range(60)]
    facts[-1].context = EvidenceContext(limitations="Only new records; historical replay unknown")
    ledger = EvidenceLedger(entries=facts)
    first = select_evidence(ledger, "Feature", preferred_ids=["E03"], cap=5)
    second = select_evidence(EvidenceLedger(entries=list(reversed(facts))), "Feature", preferred_ids=["E03"], cap=5)
    assert first.ledger.ids == second.ledger.ids
    assert {"E03", "E59"} <= first.ledger.ids
    assert first.omitted_ids
    assert "not absence" in first.render_manifest()


def test_problem_reference_survives_a_paraphrase_with_multiple_problems():
    _, _, _, context, brief = tally_case(DossierState.CURRENT)
    context.ranked_evidence[0].problem_ids = ["P1"]
    context.problems.append(context.problems[0].model_copy(update={"id": "P2", "statement": "A different problem"}))
    email = brief.emails[0]
    email.problem_ids = ["P1"]
    email.felt_need = "A paraphrase with none of the original phrasing"
    assert context.normalized_felt_need(email.felt_need, email.evidence_ids, email.problem_ids) == context.problems[0].statement


def test_invalid_primary_chooses_complete_alternative_and_preserves_announcement_action():
    artifacts, _, _, context, brief = tally_case(DossierState.CURRENT)
    action = CallToAction(label="Create a free form", url="https://example.com/create")
    artifacts.offer = OfferSheet(calls_to_action=[action])
    brief.emails[0].alternative_arguments = [ArgumentOption(
        single_idea="Build a first form and inspect its supported submission path.", evidence_ids=["E33"],
        action_id=action.reference_id, call_to_action=action.label,
        next_step_value="Inspect the form builder", next_step_evidence_ids=["E33"],
        selection_reason="A product introduction needs a first evaluation, not an unproved maintenance promise.",
    )]
    result = Strategist(None)._normalize(brief, parse_contract("Write 1 announcement email"), artifacts, context,
                                         intent=CampaignIntent(objective="announcement"))
    selected = result.emails[0]
    assert not selected.argument_issue
    assert selected.action_id == action.reference_id
    assert selected.next_step_url == action.url
    assert selected.call_to_action == action.label
    assert result.intent.objective == "announcement"
    assert not selected.felt_need


@pytest.mark.asyncio
async def test_recovery_and_other_plan_defects_share_one_correction():
    artifacts = artifacts_fixture()
    recovered = Evidence(id="R1", kind=EvidenceKind.FEATURE, claim="A verified setup guide",
                         verbatim="The guide documents the supported setup path.", source="https://example.com/guide")
    artifacts.evidence.entries.append(recovered)
    provider = RoleScriptedProvider({"strategist": campaign_brief(1)})
    provider.push("strategist", json.dumps({"emails": []}), campaign_brief(1))
    with pytest.raises(StrategyError, match="one combined correction"):
        await Strategist(make_session(provider)).build(
            request=CampaignRequest(name="Announcement", request="Write exactly one email"),
            artifacts=artifacts, corpus=SourceCorpus(),
            contract=parse_contract("Write exactly one email"),
            recovery=MaterialRecovery(gap="The setup path", evidence=[recovered]),
        )
    assert provider.calls_by_role["strategist"] == 2


@pytest.mark.asyncio
async def test_recovery_preserves_the_other_email_without_buying_its_calls_again(provider, request_fixture):
    from dataclasses import replace

    from tests.marketing.conftest import CRITIQUE_SHIP
    from tests.marketing.test_pipeline import build, refine_only

    missing = json.dumps({"verdict": "revise", "failure_mode": "missing_material",
                          "strategy_gap": "The supported setup path is missing.", "edits": []})
    repaired = json.loads(campaign_brief(2))
    repaired["emails"][0].update(evidence_ids=["R1"], next_step_evidence_ids=["R1"])
    provider.push("strategist", campaign_brief(2), json.dumps(repaired))
    provider.push("conversion_critic", missing, CRITIQUE_SHIP, CRITIQUE_SHIP)
    recovery = MaterialRecovery(gap="The supported setup path", evidence=[Evidence(
        id="R1", kind=EvidenceKind.FEATURE, claim="The guide explains the setup path.",
        verbatim="The guide explains the supported setup path.", source="https://example.com/guide",
    )])

    class Researcher:
        async def recover(self, **kwargs):
            return recovery

    pipeline, _ = build(provider, refine_only(max_revisions=0), material_researcher=Researcher())
    result = await pipeline.run(replace(request_fixture, request="Write exactly 2 emails"))
    assert len(result.outcomes) == 2
    assert [item.brief.position for item in result.outcomes] == [1, 2]
    assert provider.calls_by_role["email_writer"] == 3, "The unaffected second email is retained."
    assert provider.calls_by_role["blind_reader"] == 3
    assert provider.calls_by_role["strategist"] == 2
