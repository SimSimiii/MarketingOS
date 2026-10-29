"""Saved-source resource questions must not automatically become new research.

The first header and sentence were captured in the Tally webhook material.
The other product manual is synthetic. No model or open-web call is made.
"""

import json
from dataclasses import replace

import pytest
from pydantic import ValidationError

from app.knowledge.corpus import Document, SourceCorpus
from app.knowledge.ledger import Evidence, EvidenceContext, EvidenceKind, EvidenceLedger
from app.marketing.briefs import EmailBrief
from app.marketing.craft import CraftLoop
from app.marketing.critic import Critique
from app.marketing.reader import BlindRead, PanelRead
from tests.marketing.conftest import (
    CRITIQUE_REVISE,
    CRITIQUE_SHIP,
    RoleScriptedProvider,
    artifacts_fixture,
    blind_read,
    campaign_brief,
)
from tests.marketing.test_pipeline import build, refine_only


def fact_loop(entries, corpus=None):
    loop = object.__new__(CraftLoop)
    loop._corpus = corpus
    loop._artifacts = artifacts_fixture().model_copy(update={
        "evidence": EvidenceLedger(entries=entries),
    })
    return loop


def export_fact(id_="export", **kwargs):
    return Evidence(
        id=id_, kind=EvidenceKind.FEATURE,
        claim="Video downloads are SD on Free and HD on paid plans.",
        verbatim="Video downloads are SD on Free and HD on paid plans.",
        source="https://product.example/plans", **kwargs,
    )


def review_brief(**kwargs):
    return EmailBrief(position=1, job="Evaluate collection", single_idea="A collection form", **kwargs)


def test_unassigned_licensed_fact_is_indexed_and_selected_with_full_source_context():
    loop = fact_loop([export_fact(context=EvidenceContext(
        subject="video export", conditions="Paid plans only for HD",
    ))])
    context = loop._review_sources(PanelRead(reads=[BlindRead(
        biggest_doubt="Can I download the video on Free or does HD need a paid plan?",
    )]), review_brief())
    assert "[export]" in context
    assert "Video downloads are SD on Free and HD on paid plans." in context
    assert "Paid plans only for HD" in context
    assert "lookup only, not assigned arguments or source quotations" in context
    selected = loop._selected_review_facts(Critique(supporting_evidence_ids=["export"]), review_brief())
    assert "https://product.example/plans" in selected
    assert "source says:" in selected
    assert "Paid plans only for HD" in selected


def test_excluded_facts_cannot_reenter_through_reader_question_retrieval():
    loop = fact_loop([export_fact(), export_fact("excluded")])
    context = loop._review_sources(PanelRead(reads=[BlindRead(
        biggest_doubt="Which video downloads are available?",
    )]), review_brief(forbidden_evidence_ids=["excluded"]))
    assert "[export]" in context
    assert "[excluded]" not in context
    selected = loop._selected_review_facts(Critique(
        supporting_evidence_ids=["excluded", "missing", "export", "export"],
    ), review_brief(forbidden_evidence_ids=["excluded"]))
    assert "[excluded]" not in selected
    assert "[missing]" not in selected
    assert selected.count("[export]") == 1


def test_selected_fact_count_is_bounded_and_no_index_is_added_without_a_reported_question():
    loop = fact_loop([export_fact(str(index)) for index in range(12)])
    selected = loop._selected_review_facts(Critique(
        supporting_evidence_ids=[str(index) for index in range(6)],
    ), review_brief())
    assert all(f"[{index}]" in selected for index in range(6))
    assert "[6]" not in selected
    with pytest.raises(ValidationError):
        Critique(supporting_evidence_ids=[str(index) for index in range(7)])
    assert loop._selected_review_facts(None, review_brief()) == ""
    assert loop._review_sources(PanelRead(), review_brief()) == ""
    assert loop._review_sources(PanelRead(reads=[BlindRead(
        reported=False, biggest_doubt="Video downloads",
    )]), review_brief()) == ""


def test_index_allows_selection_beyond_repeated_display_claims_without_forwarding_them_all():
    entries = [Evidence(
        id=f"display{index}", kind=EvidenceKind.FEATURE,
        claim="Share proof on your website, sales pages, emails and socials.",
        verbatim="Share proof on your website, sales pages, emails and socials.",
    ) for index in range(5)]
    entries.extend([export_fact(), Evidence(
        id="price", kind=EvidenceKind.PRICE,
        claim="Starter costs $29/month, billed monthly.",
        verbatim="Starter costs $29/month, billed monthly.",
    )])
    loop = fact_loop(entries)
    context = loop._review_sources(PanelRead(reads=[BlindRead(
        to_click_it_would_have_to="What happens to a video afterwards and what does upgrading cost?",
    )]), review_brief())
    assert "[export]" in context and "[price]" in context
    selected = loop._selected_review_facts(Critique(
        supporting_evidence_ids=["export", "price"],
    ), review_brief())
    assert "[export]" in selected and "[price]" in selected
    assert "[display" not in selected


def test_existing_example_is_retrieved_without_turning_it_into_a_claim_permission():
    # Exact recorded heading/sentence, not a newly asserted product capability.
    corpus = SourceCorpus.from_documents([Document(
        id="recorded-webhook", title="Webhooks", source="https://tally.so/help/webhooks",
        content="### Example webhook event\nThis example event contains every type of field that Tally supports.",
    )])
    loop = object.__new__(CraftLoop)
    loop._corpus = corpus
    context = loop._review_sources(PanelRead(reads=[BlindRead(
        biggest_doubt="What is in the payload?",
        to_click_it_would_have_to="I need a sample payload showing choice and email fields.",
    )]))
    assert "Example webhook event" in context
    assert "https://tally.so/help/webhooks" in context
    assert "does not expand" in context
    assert "not an entailed answer" in context


@pytest.mark.asyncio
async def test_existing_manual_reaches_same_critique_and_rewrite_but_not_cold_reader(
    provider: RoleScriptedProvider, request_fixture,
):
    provider.set_default("strategist", campaign_brief(1))
    provider.push("blind_reader", blind_read(pull=4, biggest_doubt="I need a sample configuration.",
        to_click_it_would_have_to="Show an example configuration."), blind_read(pull=8))
    provider.push("conversion_critic", CRITIQUE_REVISE, CRITIQUE_SHIP)
    pipeline, gateway = build(provider, refine_only(max_revisions=1))
    gateway._corpus = SourceCorpus.from_documents([Document(
        id="synthetic-manual", title="Synthetic product manual", source="https://synthetic.example/manual",
        content="### Example configuration\nLOCAL_SOURCE_SENTINEL. This manual shows a sample configuration for the device. "
                "It is an illustration, not proof that every setup or customer will work.",
    )])
    await pipeline.run(replace(request_fixture, request="Write exactly one email"))
    critique = provider.requests_for("conversion_critic")[0]
    rewrite = provider.requests_for("email_writer")[1]
    assert "LOCAL_SOURCE_SENTINEL" in critique.messages[0].content
    assert "LOCAL_SOURCE_SENTINEL" in rewrite.messages[0].content
    assert all("LOCAL_SOURCE_SENTINEL" not in call.system_prompt
               for call in provider.requests_for("blind_reader"))
    assert not provider.requests_for("material_researcher")
    assert provider.calls_by_role["email_writer"] == 2


@pytest.mark.asyncio
async def test_licensed_reader_fact_reaches_critique_and_rewrite_but_not_cold_reader(
    provider: RoleScriptedProvider, request_fixture,
):
    provider.set_default("strategist", campaign_brief(1))
    provider.push("blind_reader", blind_read(pull=4,
        biggest_doubt="Can I download the video on Free?"), blind_read(pull=8))
    critique_answer = json.loads(CRITIQUE_REVISE)
    critique_answer["supporting_evidence_ids"] = ["export", "missing", "export"]
    provider.push("conversion_critic", json.dumps(critique_answer), CRITIQUE_SHIP)
    artifacts = artifacts_fixture()
    artifacts.evidence.entries.append(export_fact())
    pipeline, _ = build(provider, refine_only(max_revisions=1), artifacts=artifacts)

    await pipeline.run(replace(request_fixture, request="Write exactly one email"))

    critique = provider.requests_for("conversion_critic")[0]
    rewrite = provider.requests_for("email_writer")[1]
    assert "Index of existing campaign-licensed facts" in critique.messages[0].content
    assert "Existing licensed supporting facts selected by the critique" in rewrite.messages[0].content
    assert "Video downloads are SD on Free and HD on paid plans." in rewrite.messages[0].content
    assert "[missing]" not in rewrite.messages[0].content
    assert all("Video downloads are SD" not in (call.system_prompt or "")
               for call in provider.requests_for("blind_reader"))
    assert not provider.requests_for("material_researcher")
