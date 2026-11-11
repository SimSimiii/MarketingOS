"""The email's job is the sale, and each part of the loop has to know it.

Cabaia's Duffle email of 31 October sold a verification: "Vérifier le Duffle",
"« 14 pouces » ne précise pas les dimensions internes". It was written from one
fact while the price, 4.83/5 on 82 reviews and free returns sat on the page it
linked to, the writer was handed the list of what the page does not prove, and
the score that picked the draft asked whether it was adequate rather than
whether anybody wanted the bag. These pin the four things that changed.
"""

from types import SimpleNamespace

import pytest

from app.core.config import PROMPTS_DIR
from app.knowledge.ledger import Evidence, EvidenceContext, EvidenceKind, EvidenceLedger
from app.market.relevance import ClaimContract, ContractClaim
from app.marketing.briefs import CampaignBrief
from app.marketing.craft import EmailVersion, better_of
from app.marketing.critic import ConversionCritic
from app.marketing.email_copy import parse_email
from app.marketing.gates import GateReport
from app.marketing.reader import BlindRead, PanelRead
from app.marketing.request import CampaignRequest
from app.marketing.steering import release_selling_facts
from app.marketing.writer import EmailWriter
from tests.marketing.conftest import (
    CRITIQUE_SHIP,
    RoleScriptedProvider,
    artifacts_fixture,
    campaign_brief,
    email_draft,
    make_session,
)

PAGE = "https://shop.example/products/duffle"
BAG = "Duffle Adventurer Reykjavik"


def fact(
    id_: str, kind: EvidenceKind, verbatim: str, *, subject: str = BAG, source: str = PAGE,
    source_kind: str = "vendor_statement",
) -> Evidence:
    return Evidence(
        id=id_, kind=kind, claim=verbatim, verbatim=verbatim, source=source,
        context=EvidenceContext(subject=subject, source_kind=source_kind),
    )


def review(id_: str, verbatim: str) -> Evidence:
    return fact(id_, EvidenceKind.TESTIMONIAL, verbatim, subject="a customer",
                source_kind="customer_statement")


def shop_artifacts():
    artifacts = artifacts_fixture()
    artifacts.evidence = EvidenceLedger(entries=[
        fact("PRICE", EvidenceKind.PRICE, f"# {BAG} 120€"),
        fact("OTHER_PRICE", EvidenceKind.PRICE, "Valise souple XS Berlin 130€",
             subject="Valise souple XS Berlin"),
        fact("SIZE", EvidenceKind.METRIC, "29cm x 30cm x 45cm Dimensions"),
        fact("RATING", EvidenceKind.METRIC, "4.83/5 (82 avis)"),
        fact("PRESS", EvidenceKind.METRIC, "9.1/10 selon Le Comparateur",
             source_kind="third_party"),
        fact("AWARD", EvidenceKind.AWARD, "Best seller Bagage Cabine"),
        review("SHORT", "5/5 Patricia B publié le 22/08/2026 Très spacieux"),
        review("LONG", "5/5 Michelle A publié le 17/07/2026 rien à redire toujours parfait"),
        review("BAD", "3/5 Alice M publié le 12/08/2026 Pas reçu encore"),
        fact("RETURNS", EvidenceKind.GUARANTEE, "Retours gratuits dans un délai de 14 jours.",
             subject="Retours Cabaia"),
        fact("WIDE", EvidenceKind.FEATURE, "Ouverture grand angle"),
        fact("OTHER_FEATURE", EvidenceKind.FEATURE, "Quatre roues silencieuses",
             subject="Valise souple XS Berlin"),
        fact("ELSEWHERE", EvidenceKind.PRICE, f"{BAG} 90€ chez un revendeur",
             source="https://shop.example/products/tote"),
    ])
    return artifacts


def test_the_page_sells_on_its_own_price_rating_reviews_and_guarantees():
    picked = shop_artifacts().selling_facts(PAGE).entries

    assert [entry.id for entry in picked] == [
        "PRICE", "AWARD", "RATING", "SIZE", "LONG", "SHORT", "RETURNS", "WIDE",
    ]


def test_another_product_on_the_same_page_lends_it_nothing():
    """A shop's page lists other products with their prices: quoting one of
    those as this bag's price is the one mistake that would cost a sale."""
    ids = shop_artifacts().selling_facts(PAGE).ids

    assert not ids & {"OTHER_PRICE", "OTHER_FEATURE", "ELSEWHERE"}


def test_a_bad_review_and_a_third_party_are_not_selling_points():
    ids = shop_artifacts().selling_facts(PAGE).ids

    assert not ids & {"BAD", "PRESS"}


def test_what_the_brief_forbids_stays_forbidden():
    ids = shop_artifacts().selling_facts(PAGE, excluded_ids=frozenset({"RATING"})).ids

    assert "RATING" not in ids


@pytest.mark.parametrize("destination", ["", "https://shop.example/", "not a url"])
def test_a_page_nothing_was_read_from_has_nothing_to_sell_on(destination):
    assert shop_artifacts().selling_facts(destination).entries == []


async def writer_prompt(destination: str = PAGE, **brief_fields) -> str:
    provider = RoleScriptedProvider({"email_writer": email_draft()})
    campaign = CampaignBrief.model_validate_json(campaign_brief(count=1))
    brief = campaign.emails[0].model_copy(update={"next_step_url": destination, **brief_fields})
    await EmailWriter(make_session(provider)).draft(
        brief=brief, campaign=campaign,
        request=CampaignRequest(name="Duffle", request="Write one acquisition email"),
        artifacts=shop_artifacts(), previous=[],
    )
    return provider.requests_for("email_writer")[0].system_prompt or ""


@pytest.mark.asyncio
async def test_the_writer_is_told_to_sell_and_handed_what_sells():
    prompt = await writer_prompt()

    assert prompt.index("Your job is to sell") < prompt.index("# The request this campaign")
    sells = prompt[prompt.index("# What sells this"):prompt.index("# Everything else")]
    assert "[RATING]" in sells and "[PRICE]" in sells
    assert '"5/5 Michelle A publié le 17/07/2026 rien à redire toujours parfait"' in sells, (
        "a quotation has to reach the writer word for word"
    )


@pytest.mark.asyncio
async def test_a_page_with_nothing_on_it_adds_no_empty_section():
    assert "# What sells this" not in await writer_prompt("https://shop.example/unread")


@pytest.mark.asyncio
async def test_the_writer_never_sees_what_the_step_does_not_prove():
    """Handed that line, it published it. `must_not_say` is what keeps the
    claim out, and it stays."""
    prompt = await writer_prompt(
        next_step_limit="La fiche ne documente pas les dimensions internes.",
        must_not_say=["La poche accueille tous les ordinateurs de 14 pouces."],
    )

    assert "dimensions internes" not in prompt
    assert "What the step does not validate" not in prompt
    assert "La poche accueille tous les ordinateurs de 14 pouces." in prompt


@pytest.mark.asyncio
async def test_the_critic_still_sees_the_limit_and_the_same_facts_as_the_writer():
    """It has to catch a promise past the limit, and to know the price in the
    draft was handed over rather than invented."""
    provider = RoleScriptedProvider({"conversion_critic": CRITIQUE_SHIP})
    campaign = CampaignBrief.model_validate_json(campaign_brief(count=1))
    brief = campaign.emails[0].model_copy(update={
        "next_step_url": PAGE, "next_step_limit": "La fiche ne documente pas les dimensions internes.",
    })

    await ConversionCritic(make_session(provider)).critique(
        email=parse_email(email_draft(), 1), brief=brief, campaign=campaign,
        artifacts=shop_artifacts(), read=PanelRead(), gates=GateReport(),
    )

    prompt = provider.requests_for("conversion_critic")[0].system_prompt or ""
    assert "dimensions internes" in prompt
    assert "[RATING]" in prompt


def version(attempt: int, *, pull: int, clicks: int) -> EmailVersion:
    reads = [BlindRead(pull=pull, would_act=reader < clicks) for reader in range(3)]
    return EmailVersion(
        attempt=attempt, email=parse_email(email_draft(), 1), gates=GateReport(),
        read=PanelRead(reads=reads),
    )


def test_a_draft_more_readers_would_click_beats_one_they_merely_rate_higher():
    clicked, admired = version(1, pull=7, clicks=2), version(2, pull=8, clicks=1)

    assert clicked.measured > admired.measured
    assert clicked.score > admired.score
    assert better_of(admired, clicked) is clicked


def test_with_the_same_clicks_the_one_they_want_more_wins():
    wanted, tepid = version(1, pull=8, clicks=2), version(2, pull=6, clicks=2)

    assert better_of(tepid, wanted) is wanted


def test_nobody_reporting_back_is_no_click_rather_than_a_crash():
    assert PanelRead().acting == 0.0


def test_the_score_asks_whether_they_want_it():
    template = (PROMPTS_DIR / "reader.md").read_text(encoding="utf-8")

    assert "how much this email makes you want what it is" in " ".join(template.split())
    assert "adequacy" not in template


def boundary_brief(forbidden: list[str]) -> CampaignBrief:
    campaign = CampaignBrief.model_validate_json(campaign_brief(count=1))
    campaign.emails[0].next_step_url = PAGE
    campaign.emails[0].forbidden_evidence_ids = forbidden
    return campaign


def test_the_boundary_gives_back_the_page_s_reasons_to_buy_and_nothing_false():
    """A price the dossier never ranked is withheld, not untrue. The proof of a
    capability nobody verified is untrue until somebody does."""
    contract = ClaimContract(forbidden_claims=[
        ContractClaim(id="c", text="Do not claim it.", evidence_ids=["RETURNS"]),
    ])
    brief = boundary_brief(["PRICE", "RATING", "RETURNS", "OTHER_PRICE", "ELSEWHERE"])

    release_selling_facts(brief, shop_artifacts(), SimpleNamespace(claim_contract=contract))

    assert brief.emails[0].forbidden_evidence_ids == ["RETURNS", "OTHER_PRICE", "ELSEWHERE"]


def test_a_fixed_destination_decides_which_page_sells():
    brief = boundary_brief(["PRICE"])
    brief.fixed_cta_url = "https://shop.example/unread"
    brief.emails[0].next_step_url = PAGE

    release_selling_facts(brief, shop_artifacts(), SimpleNamespace(claim_contract=ClaimContract()))

    assert brief.emails[0].forbidden_evidence_ids == ["PRICE"]


def test_destination_price_with_unknown_payment_conditions_stays_outside_boundary():
    artifacts = shop_artifacts()
    artifacts.evidence.get("PRICE").context = EvidenceContext(
        claim_scope="offer", limitations="Billing terms not specified.",
    )
    brief = boundary_brief(["PRICE"])
    release_selling_facts(brief, artifacts, SimpleNamespace(claim_contract=ClaimContract()))
    assert brief.emails[0].forbidden_evidence_ids == ["PRICE"]


def test_a_legacy_dossier_has_no_line_to_read_so_its_boundary_stands():
    brief = boundary_brief(["PRICE"])

    release_selling_facts(brief, shop_artifacts(), SimpleNamespace(claim_contract=None))
    release_selling_facts(brief, shop_artifacts(), None)

    assert brief.emails[0].forbidden_evidence_ids == ["PRICE"]
