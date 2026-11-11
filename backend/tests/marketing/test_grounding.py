"""The boundary between source judgment and mechanical receipt validation."""

import json

import pytest

from app.knowledge.artifacts import CallToAction, Plan, Provenance
from app.knowledge.corpus import Document, SourceCorpus
from app.knowledge.ledger import EvidenceIndex
from app.marketing.briefs import CampaignBrief, EmailBrief
from app.marketing.craft import check_draft
from app.marketing.email_copy import Email, parse_email, render_review
from app.marketing.gates import GateReport
from app.marketing.grounding import (
    ClaimReviewer,
    destination_excerpts,
    factual_repair,
    offer_source_excerpts,
    proposition_source_excerpts,
    reuse_review,
)
from app.marketing.reader import PanelRead
from app.marketing.request import CampaignRequest
from app.marketing.writer import EmailWriter
from app.runtime.exceptions import ProviderError
from tests.marketing.conftest import FAIL, artifacts_fixture, email_draft, make_session


def inputs(provider):
    artifacts = artifacts_fixture()
    email = parse_email(email_draft(), 1)
    brief = EmailBrief(position=1, single_idea="Write release notes", evidence_ids=["E1"])
    reviewer = ClaimReviewer(make_session(provider))
    return reviewer, email, brief, artifacts


def decision(email, artifacts, *, verdict="supported", kind=None, quote=None):
    fact = artifacts.evidence.entries[0]
    return json.dumps({"verdict": verdict, "summary": "Source review decision",
        "claims": [{"text": email.body, "status": "supported", "explanation": "Assessed in context",
                    "citations": [{"source_id": fact.id, "quote": quote or fact.verbatim}]}],
        "findings": [{"text": email.body, "kind": kind, "explanation": "Unsupported capability"}] if kind else []})


@pytest.mark.parametrize("destination", ["/download", "https://product.example/download"])
def test_destination_proof_requires_a_literal_link_to_the_selected_origin(destination):
    artifacts = artifacts_fixture()
    origin = "https://product.example/"
    action = CallToAction(label="Download for Mac", url=destination, provenance=Provenance(source=origin))
    artifacts.offer.calls_to_action = [action]
    brief = EmailBrief(position=1, single_idea="Download the app", action_id=action.reference_id,
                       next_step_url=destination)
    corpus = SourceCorpus.from_documents([
        Document(id="other", title="Other", content="[Export free](/download)", source="https://other.example/"),
        Document(id="product", title="Product",
                 content="[Malformed](http://[)\n[Download for Mac](/download)", source=origin),
    ])

    assert destination_excerpts(brief, artifacts, corpus) == {
        "cta:0": f"Source page: {origin}\nResolved link: {origin}download\n"
                 "Literal link: [Download for Mac](/download)",
    }


@pytest.mark.asyncio
async def test_plan_price_receipt_can_cite_captured_terms_missing_from_ledger_quote(provider):
    reviewer, email, brief, artifacts = inputs(provider)
    origin = "https://product.example/pricing"
    artifacts.evidence.entries[0].verbatim = "## Basic Publish audio."
    plan = Plan(name="Basic", price="$12/mo", provenance=Provenance(source=origin, evidence_id="E1"))
    artifacts.offer.plans = [plan]
    brief.offer_id = plan.reference_id
    corpus = SourceCorpus.from_documents([
        Document(id="other", title="Other", content="## Basic\nPublish audio.\n\n$2/mo",
                 source="https://other.example/pricing"),
        Document(id="official", title="Pricing", source=origin,
                 content="## Pricing\nAll prices in USD. Billed monthly.\n\n## Basic\nPublish audio.\n\n$12/mo"),
    ])
    email.body = "Basic costs 12 US dollars per month, billed monthly."
    verdict = json.loads(decision(email, artifacts))
    verdict["claims"][0]["citations"] = [
        {"source_id": f"offer:{plan.reference_id}", "quote": "$12/mo"},
        {"source_id": f"offer:{plan.reference_id}:context", "quote": "All prices in USD. Billed monthly."},
    ]
    provider.push("claim_reviewer", json.dumps(verdict))

    report = await reviewer.review(email=email, brief=brief, artifacts=artifacts,
                                   hints=GateReport(), corpus=corpus)
    assert report.passed
    excerpts = offer_source_excerpts(artifacts, corpus, offer_id=plan.reference_id)
    assert "$2/mo" not in excerpts[f"offer:{plan.reference_id}"]
    assert not offer_source_excerpts(artifacts, corpus, allowed_ids=set())


@pytest.mark.asyncio
async def test_draft_rewrite_and_reviewer_share_proposition_sources(provider):
    reviewer, email, brief, artifacts = inputs(provider)
    brief.mechanism = "Generate branded variations from one template and product data."
    brief.user_request = "Introduce our product with one next step."
    brief.claim_conditions = ["The trial includes one workspace."]
    brief.must_not_say = ["Billing periods"]
    quote = "Fill a template with your own data and get back a finished image."
    corpus = SourceCorpus.from_documents([
        Document(id="official", title="Image API", content=quote, source="https://product.example/api"),
    ])
    writer = EmailWriter(make_session(provider), corpus=corpus)
    arguments = {
        "brief": brief,
        "campaign": CampaignBrief(emails=[brief]),
        "request": CampaignRequest(name="One email", request="Introduce our product"),
        "artifacts": artifacts,
        "previous": [],
    }
    await writer.draft(**arguments)
    await writer.revise(draft=email, gates=GateReport(), read=PanelRead(), **arguments)
    prompts = [request.system_prompt for request in provider.requests_for("email_writer")]
    assert len(prompts) == 2
    assert all(quote in prompt and "Billing periods" in prompt for prompt in prompts)

    source_id = next(iter(proposition_source_excerpts(brief, artifacts, corpus)))
    email.body = "Use your own data to render an image from a template."
    verdict = json.loads(decision(email, artifacts))
    verdict["claims"][0]["citations"] = [{"source_id": source_id, "quote": quote}]
    provider.push("claim_reviewer", json.dumps(verdict))
    report = await reviewer.review(email=email, brief=brief, artifacts=artifacts,
                                   hints=GateReport(), corpus=corpus)
    assert report.passed
    prompt = provider.requests_for("claim_reviewer")[0].system_prompt
    assert f"ACTUAL USER REQUEST\n{brief.user_request}" in prompt
    assert "CAMPAIGN SCOPE, STRATEGY NOTES AND ANY USER STEERING" in prompt
    assert brief.claim_conditions[0] not in prompt


@pytest.mark.asyncio
async def test_model_can_reject_a_qualitative_claim_without_a_number(provider):
    reviewer, email, brief, artifacts = inputs(provider)
    email.body += "\n\nNotewright replaces your entire security team."
    mechanical, _ = check_draft(email, brief, artifacts=artifacts,
                               evidence=EvidenceIndex(artifacts.evidence), previous=[])
    assert mechanical.passed
    provider.push("claim_reviewer", decision(email, artifacts, verdict="revise", kind="factual"))
    report = await reviewer.review(email=email, brief=brief, artifacts=artifacts, hints=mechanical)
    assert report.blocking and not report.semantic_review["approved"]
    assert provider.calls_by_role["claim_reviewer"] == 1


@pytest.mark.asyncio
async def test_model_approval_cannot_cite_a_fabricated_quote(provider):
    reviewer, email, brief, artifacts = inputs(provider)
    provider.push("claim_reviewer", decision(email, artifacts, quote="A quotation the source never contained"))
    report = await reviewer.review(email=email, brief=brief, artifacts=artifacts, hints=GateReport())
    assert any(issue.gate == "review-reference" for issue in report.blocking)


@pytest.mark.asyncio
async def test_only_identical_words_and_source_context_reuse_their_own_review(provider):
    reviewer, email, brief, artifacts = inputs(provider)
    first = await reviewer.review(email=email, brief=brief, artifacts=artifacts, hints=GateReport())
    same = await reviewer.review(email=email, brief=brief, artifacts=artifacts, hints=GateReport())
    assert first.passed and same.passed
    assert provider.calls_by_role["claim_reviewer"] == 1
    assert reuse_review(GateReport(), first.semantic_review, email=email, brief=brief, artifacts=artifacts).passed
    audience_only = artifacts.model_copy(deep=True)
    audience_only.audience.segments[0].situation = "A different display summary, not source evidence"
    assert reuse_review(GateReport(), first.semantic_review, email=email, brief=brief, artifacts=audience_only).passed
    changed = email.model_copy(update={"subject": "A changed promise"})
    assert reuse_review(GateReport(), first.semantic_review, email=changed, brief=brief, artifacts=artifacts).blocking
    updated = artifacts.model_copy(deep=True)
    updated.evidence.entries[0].verbatim += " A new condition applies."
    assert reuse_review(GateReport(), first.semantic_review, email=email, brief=brief, artifacts=updated).blocking
    await reviewer.review(email=changed, brief=brief, artifacts=artifacts, hints=GateReport())
    assert provider.calls_by_role["claim_reviewer"] == 2


@pytest.mark.asyncio
async def test_an_editorial_objection_never_becomes_a_factual_veto(provider):
    reviewer, email, brief, artifacts = inputs(provider)
    provider.push("claim_reviewer", decision(email, artifacts, kind="editorial"))
    report = await reviewer.review(email=email, brief=brief, artifacts=artifacts, hints=GateReport())
    assert report.passed and report.advisory


@pytest.mark.asyncio
@pytest.mark.parametrize("retention", ["preserved", "lost"])
async def test_factual_repair_checks_retention_without_inheriting_approval(provider, retention):
    reviewer, original, brief, artifacts = inputs(provider)
    candidate = original.model_copy(deep=True)
    invented = "Notewright replaces your entire security team."
    original.body += "\n\n" + invented
    rejected = json.loads(decision(candidate, artifacts, verdict="revise"))
    rejected["claims"].append({
        "text": invented, "status": "unsupported", "explanation": "No supporting source.",
        "citations": [],
    })
    provider.push("claim_reviewer", json.dumps(rejected))
    prior = await reviewer.review(email=original, brief=brief, artifacts=artifacts, hints=GateReport())
    context = factual_repair(original, brief, artifacts, prior)
    assert context is not None and [claim.text for claim in context.supported_passages] == [candidate.body]
    assert invented not in context.render()
    assert prior.blocking

    verdict = json.loads(decision(candidate, artifacts))
    verdict["benefit_retention"] = {
        "status": retention, "explanation": "Comparison with the prior draft.",
        "original_passage": candidate.body, "revised_passage": candidate.body if retention == "preserved" else "",
    }
    provider.push("claim_reviewer", json.dumps(verdict))
    fresh = await reviewer.review(
        email=candidate, brief=brief, artifacts=artifacts, hints=GateReport(), repair=context,
    )
    assert fresh.passed and provider.calls_by_role["claim_reviewer"] == 2
    assert bool(fresh.advisory) == (retention == "lost")
    restored = reuse_review(GateReport(), fresh.semantic_review, email=candidate, brief=brief, artifacts=artifacts)
    assert restored.advisory == fresh.advisory


@pytest.mark.asyncio
async def test_factual_repair_excludes_unresolvable_citations(provider):
    reviewer, email, brief, artifacts = inputs(provider)
    provider.push("claim_reviewer", decision(email, artifacts, verdict="revise", kind="factual", quote="Invented proof"))
    gates = await reviewer.review(email=email, brief=brief, artifacts=artifacts, hints=GateReport())
    assert factual_repair(email, brief, artifacts, gates) is None


@pytest.mark.asyncio
async def test_unavailable_reviewer_does_not_approve_changed_text(provider):
    reviewer, email, brief, artifacts = inputs(provider)
    await reviewer.review(email=email, brief=brief, artifacts=artifacts, hints=GateReport())
    provider.push("claim_reviewer", FAIL, FAIL, FAIL)
    changed = email.model_copy(update={"body": email.body + "\n\nAnother promise."})
    with pytest.raises(ProviderError):
        await reviewer.review(email=changed, brief=brief, artifacts=artifacts, hints=GateReport())


def test_mechanical_checks_do_not_interpret_acronyms_plans_or_square_brackets():
    artifacts = artifacts_fixture()
    email = Email(position=1, subject="SCIM for Pro", preview_text="A plan", greeting="Hello",
                  body="The Pro plan costs $10 per user/month, billed annually. [Optional context]",
                  call_to_action="See Pro", sign_off="Team")
    gates, _ = check_draft(email, EmailBrief(position=1), artifacts=artifacts,
                          evidence=EvidenceIndex(artifacts.evidence), previous=[])
    assert gates.passed
    email.body += " {{unconfigured_field}}"
    gates, _ = check_draft(email, EmailBrief(position=1), artifacts=artifacts,
                          evidence=EvidenceIndex(artifacts.evidence), previous=[])
    assert [issue.gate for issue in gates.blocking] == ["merge-field"]
    assert "unconfigured_field" in render_review(email)
