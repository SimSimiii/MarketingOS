"""Reproductions of the saved email failure, plus explicitly synthetic offers.

The first opening and customer quotation reproduce exported Tally artifacts.
Other names and offer sections are synthetic; no test asserts current web facts.
"""

from datetime import UTC, datetime

import pytest

from app.knowledge.ledger import (
    Evidence,
    EvidenceContext,
    EvidenceIndex,
    EvidenceKind,
    EvidenceLedger,
    context_of,
)
from app.marketing.gates import evidence_gate


@pytest.mark.parametrize("name", ["Tally", "RelayDesk", "PressCraft"])
def test_now_available_requires_launch_support_for_each_product(name):
    index = EvidenceIndex(EvidenceLedger(entries=[Evidence(
        id="E1", kind=EvidenceKind.FEATURE, claim=f"{name} supports webhooks",
        verbatim=f"{name} can push each submitted record to an endpoint.",
    )]))
    report = evidence_gate(f"{name} is now available as the form front end for your next automation.", index)
    assert report.passed, "Novelty interpretation remains advisory"
    assert any("dated launch evidence" in issue.detail for issue in report.advisory)
    assert not evidence_gate("New submissions can trigger a workflow.", index).advisory


def test_an_unrelated_dated_launch_cannot_license_now_available():
    today = datetime.now(UTC).date().isoformat()
    index = EvidenceIndex(EvidenceLedger(entries=[Evidence(
        id="E1", kind=EvidenceKind.FEATURE, claim="OtherApp launched",
        verbatim=f"OtherApp launched on {today}.",
        context=EvidenceContext(subject="OtherApp", claim_scope="launch", temporal_scope=today),
    )]))
    assert evidence_gate("RelayDesk is now available.", index).advisory
    assert not evidence_gate("OtherApp is now available.", index).advisory


def test_launch_framing_from_first_qualitative_draft_is_advisory_without_dated_support():
    index = EvidenceIndex(EvidenceLedger(entries=[Evidence(
        id="E1", kind=EvidenceKind.FEATURE, claim="A form builder sends webhooks",
        verbatim="A form builder sends webhooks.",
    )]))
    report = evidence_gate("PRODUCT LAUNCH. Today, we’re introducing a form builder.", index)
    assert report.passed
    assert any("dated launch evidence" in item.detail for item in report.advisory)


def test_a_historical_launch_date_does_not_license_current_novelty():
    index = EvidenceIndex(EvidenceLedger(entries=[Evidence(
        id="E1", kind=EvidenceKind.FEATURE, claim="OtherApp launched",
        verbatim="OtherApp launched on 2001-04-03.",
        context=EvidenceContext(subject="OtherApp", claim_scope="launch", temporal_scope="2001-04-03"),
    )]))
    assert evidence_gate("OtherApp is now available.", index).advisory


CUSTOMER_QUOTE = (
    "Learn how entrepreneur and creator Thomas Frank uses Tally forms to collect critical "
    "product feedback, achieve 30%+ response rates, and make informed development decisions "
    "for his web clipper tool, Flylighter."
)


@pytest.mark.parametrize("draft", [
    "Tally gets you 30%+ response rates with Make, Zapier or n8n.",
    "You will increase your response rate to 30%.",
    "Tally guarantees a 30% response rate.",
    "Our forms deliver 30% response rates for every workflow.",
])
def test_legacy_customer_result_does_not_silently_become_general_performance(draft):
    entry = Evidence(id="E265", kind=EvidenceKind.METRIC,
                     claim="Thomas Frank obtained 30%+ feedback response rates",
                     verbatim=CUSTOMER_QUOTE, source="https://tally.so/customers")
    report = evidence_gate(draft, EvidenceIndex(EvidenceLedger(entries=[entry])))
    assert report.passed, "A bounded semantic warning is not a new hard gate"
    assert any("attributed customer result" in issue.detail for issue in report.advisory)
    assert entry.context is None, "Scope review never rewrites historical artifacts"
    derived = context_of(entry)
    assert derived.claim_scope == "customer_outcome"
    assert "inferred" in derived.verification
    assert "review" in derived.limitations


def test_customer_result_keeps_its_customer_and_documented_use_case():
    entry = Evidence(id="E1", kind=EvidenceKind.METRIC, claim="A bakery's pilot result",
                     verbatim="Riverton Bakery reduced ingredient waste by 20% during its May pilot.",
                     source="https://synthetic.example/case-studies/bakery")
    index = EvidenceIndex(EvidenceLedger(entries=[entry]))
    assert not evidence_gate(entry.verbatim, index).advisory
    assert evidence_gate("DoughMeter gets you 20% less waste.", index).advisory
    feature = Evidence(id="E2", kind=EvidenceKind.METRIC, claim="20 formats",
                       verbatim="ExportGate supports 20 formats.", source="https://synthetic.example/help")
    assert not evidence_gate("ExportGate supports 20 formats.", EvidenceIndex(EvidenceLedger(entries=[feature]))).advisory


@pytest.mark.parametrize("heading_style", ["bold", "heading"])
def test_plan_section_does_not_establish_a_separate_feature_price(heading_style):
    feature = "**Custom domains**" if heading_style == "bold" else "### Custom domains"
    second = "**Team workspaces**" if heading_style == "bold" else "### Team workspaces"
    source = f"## RelayDesk Team\n$29/month or $290/year\n\n{feature}\nIncluded.\n\n{second}\nIncluded."
    index = EvidenceIndex(EvidenceLedger(), source)
    report = evidence_gate("Custom domains cost $29/month.", index)
    assert any("separate feature price" in issue.detail for issue in report.advisory)
    assert not evidence_gate("Custom domains are included in the $29/month Team plan.", index).advisory


def test_legacy_rival_price_requires_attribution_until_independently_documented():
    comparison = Evidence(
        id="E1", kind=EvidenceKind.PRICE, claim="CompetitorBox costs $39/month",
        verbatim="| Monthly plan | $29/mo | $39/mo |",
        source="https://maker.example/help/compare",
    )
    index = EvidenceIndex(EvidenceLedger(entries=[comparison]))
    assert evidence_gate("CompetitorBox costs $39/month.", index).advisory
    assert not evidence_gate("According to Maker's published comparison, CompetitorBox costs $39/month.", index).advisory
    direct = Evidence(id="E2", kind=EvidenceKind.PRICE, claim="CompetitorBox costs $39/month",
                      verbatim="CompetitorBox costs $39/month.", source="https://competitor.example/pricing")
    assert not evidence_gate("CompetitorBox costs $39/month.", EvidenceIndex(
        EvidenceLedger(entries=[comparison, direct])
    )).advisory
