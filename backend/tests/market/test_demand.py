"""Mapping demand, and believing only what a prospect's own pages contain.

The load-bearing tests here are the contact ones. Everything else in this
module is a judgment that a user can read and disagree with; a contact detail
is a thing the user will paste into a mail merge on Monday, and the only
difference between a real address and a fluent invention is that one of them
was on a page we fetched. `test_an_address_not_on_the_page_is_discarded` is
that difference, expressed.
"""

from uuid import uuid4

import pytest

from app.ai.base import ResearchTool
from app.knowledge.artifacts import (
    AudienceModel,
    BusinessProfile,
    Fact,
    Grounding,
    KnowledgeArtifacts,
    Objection,
    Segment,
    Sophistication,
)
from app.market.capabilities import ProductCapability, ProductCapabilityProfile
from app.market.demand import (
    MIN_USEFUL_FIT,
    AudienceCartographer,
    AudienceSegment,
    Contact,
    ContactKind,
    DemandMap,
    ProspectFinder,
    SegmentKind,
    contacts_of,
)
from app.market.qualification import QualificationClass
from app.market.store import merge_audience
from tests.market.conftest import ScriptedCrawler, ScriptedProvider

CONTACT_PAGE = (
    "# Contact us\n\n"
    "General enquiries: hello@northgate-repairs.example\n"
    "Warranty claims: warranty@northgate-repairs.example\n"
    "Call the shop on +44 (0)20 7946 0018, Monday to Friday.\n"
)

HOME_PAGE = (
    "# Northgate Repairs\n\n"
    "We refurbish and resell business laptops across the north of England.\n"
    "We handle around 60 warranty questions a week by hand.\n"
)

PAGES = {
    "https://northgate-repairs.example": [
        ("https://northgate-repairs.example", HOME_PAGE),
        ("https://northgate-repairs.example/contact", CONTACT_PAGE),
    ]
}


def artifacts() -> KnowledgeArtifacts:
    return KnowledgeArtifacts(
        business=BusinessProfile(
            company_name="Helpdesk",
            what_it_does="answers repetitive customer questions automatically",
            category="support automation",
        ),
        audience=AudienceModel(
            segments=[Segment(name="E-commerce support teams", situation="drowning in tickets")]
        ),
    )


def segment(**overrides: object) -> AudienceSegment:
    payload: dict = {
        "name": "Independent repair shops selling refurbished stock",
        "kind": SegmentKind.ADJACENT,
        "who": "a three-person shop answering 60 warranty questions a week by hand",
        "why_them": "the same forty questions, and nobody has ever pitched them this",
        "fit": 0.3,
        "basis": "they complain about it publicly and buy adjacent tools",
        "signals": ["a warranty or returns page with an email address on it"],
        "pains": ["an evening a week on the same questions"],
        "objection": "we are too small for software like this",
        "sophistication": Sophistication.UNAWARE,
    }
    payload.update(overrides)
    return AudienceSegment(**payload)


def map_payload(**overrides: object) -> dict:
    payload: dict = {
        "reading": "The demand is one industry over from where they are selling.",
        "searched": ["refurbished laptop shops warranty questions"],
        "segments": [
            segment().model_dump(mode="json"),
            segment(
                name="E-commerce support teams", kind=SegmentKind.CORE, fit=0.18
            ).model_dump(mode="json"),
        ],
    }
    payload.update(overrides)
    return payload


def read_payload(**overrides: object) -> dict:
    payload: dict = {
        "what_they_do": "refurbishes and resells business laptops",
        "why_them": "they answer warranty questions by hand",
        "verbatim": "We handle around 60 warranty questions a week by hand.",
        "fit": 0.85,
        "caveat": "they may already have somebody doing this",
        "contacts": [
            {
                "kind": "email",
                "value": "hello@northgate-repairs.example",
                "label": "general enquiries",
                "source": "https://northgate-repairs.example/contact",
            },
            {
                "kind": "phone",
                "value": "+442079460018",
                "label": "the shop",
                "source": "https://northgate-repairs.example/contact",
            },
        ],
    }
    payload.update(overrides)
    return payload


# ------------------------------------------------------------------ the map


@pytest.mark.asyncio
async def test_the_cartographer_reads_the_web(provider: ScriptedProvider, session):
    provider.push("audience_map", map_payload())

    demand = await AudienceCartographer(session).map(artifacts())

    assert next(item.name for item in demand.ranked).startswith("Independent repair shops")
    assert provider.tools_used_by("audience_map") == [
        ResearchTool.WEB_SEARCH,
        ResearchTool.WEB_FETCH,
    ]


@pytest.mark.asyncio
async def test_a_segment_below_the_fit_floor_is_not_offered(
    provider: ScriptedProvider, session
):
    """A rate can be accurate and still not be a campaign.

    The floor is about what a user is asked to choose between, not about what
    is true - see MIN_USEFUL_FIT.
    """
    provider.push(
        "audience_map",
        map_payload(
            segments=[
                segment(fit=0.4).model_dump(mode="json"),
                segment(name="Anybody with a laptop", fit=MIN_USEFUL_FIT / 2).model_dump(
                    mode="json"
                ),
            ]
        ),
    )

    demand = await AudienceCartographer(session).map(artifacts())

    assert [item.name for item in demand.segments] == [segment().name]


def test_the_summary_counts_what_the_company_could_not_have_found():
    """The whole product of the pass. A map of segments the user already knew
    is a map that cost them a search to restate their own homepage."""
    demand = DemandMap(segments=[segment(), segment(name="Theirs", kind=SegmentKind.CORE)])

    assert "1 of them nobody would have found" in demand.summary()


def test_a_chosen_segment_is_matched_forgivingly():
    demand = DemandMap(segments=[segment()])

    assert demand.named("  independent repair SHOPS selling refurbished stock ") is not None
    assert demand.named("independent repair shops") is not None
    assert demand.named("wholesalers") is None


def test_the_strategist_is_told_the_rate_is_an_estimate():
    """Nobody has sent these emails. A rate rendered as a result is a number
    the strategist has no way to discount, and it would end up in copy."""
    rendered = DemandMap(segments=[segment()]).render_for_strategy(segment().name)

    assert "estimate" in rendered
    assert "not a measured result" in rendered
    assert "<- THIS CAMPAIGN" in rendered


def test_an_unmapped_market_says_so_rather_than_reading_empty():
    rendered = DemandMap().render_for_strategy()

    assert "Nobody has mapped" in rendered
    assert "do not assume the field beyond it is empty" in rendered


# ------------------------------------------------------------ the prospects


@pytest.mark.asyncio
async def test_a_prospect_is_read_from_its_own_pages(provider: ScriptedProvider, session):
    provider.push(
        "prospect_hunt",
        {
            "leads": [
                {
                    "name": "Northgate Repairs",
                    "url": "https://northgate-repairs.example",
                    "why_them": "their warranty page lists an email address",
                }
            ],
            "searched": ["refurbished laptop resellers north england"],
        },
    )
    provider.push("prospect_read", read_payload())
    finder = ProspectFinder(session, crawler=ScriptedCrawler(PAGES))

    found = await finder.find(artifacts=artifacts(), segment=segment())

    assert len(found) == 1
    prospect = found[0]
    assert prospect.verified
    assert prospect.segment == segment().name
    assert prospect.fit == pytest.approx(0.85)
    assert [contact.value for contact in prospect.contacts] == [
        "hello@northgate-repairs.example",
        "+442079460018",
    ]
    assert all(contact.verified for contact in prospect.contacts)
    # The reading step gets no web access at all: everything it sees was
    # fetched by us, which is what makes the check below possible.
    assert provider.tools_used_by("prospect_read") == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("company_name", "quote"),
    [
        (
            "DentalReception AI",
            "Our AI receptionist answers phone calls for dental practices 24/7.",
        ),
        (
            "Orthia AI",
            "Orthia answers calls, books appointments, and verifies insurance 24/7.",
        ),
        ("Voice Agent Co", "voice agent"),
    ],
)
async def test_company_reader_maps_requirements_only_against_the_supplied_profile(
    provider: ScriptedProvider, session, company_name: str, quote: str
) -> None:
    url = "https://dental.example"
    provider.push(
        "prospect_hunt",
        {"leads": [{"name": company_name, "url": url}]},
    )
    provider.push(
        "prospect_read",
        read_payload(
            what_they_do=quote,
            verbatim=quote,
            contacts=[],
            company_requirements=[
                {
                    "capability_id": "voice_telephony",
                    "evidence_state": "direct",
                    "quote": quote,
                    "source_url": url,
                    "reasoning": "Answering calls requires the catalogued telephony runtime.",
                }
            ],
        ),
    )
    profile = ProductCapabilityProfile(
        version=7,
        knowledge_id=uuid4(),
        knowledge_version=3,
        capabilities=[
            ProductCapability(
                id="voice_telephony",
                label="Voice and telephony runtime",
                description="Runtime for agent-based inbound and outbound calling.",
                aliases=["call handling"],
                state="unsupported",
            )
        ],
    )

    prospect = (
        await ProspectFinder(
            session,
            crawler=ScriptedCrawler({url: [(url, quote)]}),
        ).find(
            artifacts=artifacts(),
            segment=segment(),
            capability_profile=profile,
        )
    )[0]

    assert prospect.qualification is not None
    assert prospect.qualification.classification is QualificationClass.EXCLUDED
    assert prospect.qualification.reason_codes[0] == (
        "unsupported_required_capability:voice_telephony"
    )
    assert prospect.qualification.identity.capability_profile_version == 7
    request = next(item for item in provider.requests if item.template == "prospect_read")
    assert "voice_telephony" in (request.system_prompt or "")
    assert "call handling" in (request.system_prompt or "")


@pytest.mark.asyncio
async def test_an_address_not_on_the_page_is_discarded(
    provider: ScriptedProvider, session
):
    """The one that matters.

    A model asked for a company's email address produces `contact@<domain>`
    with total fluency and no knowledge, and an invented address either
    bounces - taking the sender's domain reputation with it - or reaches a
    stranger. Neither is recoverable by any later step, so it never gets past
    here.
    """
    provider.push(
        "prospect_hunt",
        {
            "leads": [
                {"name": "Northgate Repairs", "url": "https://northgate-repairs.example"}
            ]
        },
    )
    provider.push(
        "prospect_read",
        read_payload(
            contacts=[
                {
                    "kind": "email",
                    "value": "hello@northgate-repairs.example",
                    "label": "general enquiries",
                },
                {
                    "kind": "email",
                    "value": "sales@northgate-repairs.example",
                    "label": "sales - a very plausible guess",
                },
            ]
        ),
    )
    finder = ProspectFinder(session, crawler=ScriptedCrawler(PAGES))

    prospect = (await finder.find(artifacts=artifacts(), segment=segment()))[0]

    assert [contact.value for contact in prospect.contacts] == [
        "hello@northgate-repairs.example"
    ]
    # Counted, not silently swallowed: a row that had to discard one is a row
    # whose other claims deserve the same suspicion, and the count is the only
    # way the user would ever know.
    assert prospect.invented_contacts == 1
    assert "nowhere on their site" in prospect.note


@pytest.mark.asyncio
async def test_a_phone_number_is_matched_on_its_digits(
    provider: ScriptedProvider, session
):
    """One number is written a dozen ways. Requiring the page's exact
    formatting would throw away correctly-read numbers at a rate that makes
    the field useless."""
    provider.push(
        "prospect_hunt",
        {
            "leads": [
                {"name": "Northgate Repairs", "url": "https://northgate-repairs.example"}
            ]
        },
    )
    provider.push(
        "prospect_read",
        read_payload(
            contacts=[
                {"kind": "phone", "value": "020 7946 0018", "label": "the shop"},
                {"kind": "phone", "value": "020 7946 9999", "label": "invented"},
            ]
        ),
    )
    finder = ProspectFinder(session, crawler=ScriptedCrawler(PAGES))

    prospect = (await finder.find(artifacts=artifacts(), segment=segment()))[0]

    assert [contact.value for contact in prospect.contacts] == ["020 7946 0018"]
    assert prospect.invented_contacts == 1


@pytest.mark.asyncio
async def test_a_reason_that_is_not_on_the_page_costs_the_row_its_confidence(
    provider: ScriptedProvider, session
):
    """Not deleted: the company was still found and read, and "we think so but
    cannot point at the sentence" is a state the user can judge. Deleting it
    would quietly turn a weak list into a short one."""
    provider.push(
        "prospect_hunt",
        {
            "leads": [
                {"name": "Northgate Repairs", "url": "https://northgate-repairs.example"}
            ]
        },
    )
    provider.push(
        "prospect_read",
        read_payload(verbatim="They process thousands of warranty claims every day."),
    )
    finder = ProspectFinder(session, crawler=ScriptedCrawler(PAGES))

    prospect = (await finder.find(artifacts=artifacts(), segment=segment()))[0]

    assert prospect.verbatim == ""
    assert prospect.fit <= 0.5
    assert "was not on their pages" in prospect.note


@pytest.mark.asyncio
async def test_a_site_that_cannot_be_read_is_kept_and_marked(
    provider: ScriptedProvider, session
):
    provider.push(
        "prospect_hunt",
        {"leads": [{"name": "Gone Ltd", "url": "https://gone.example"}]},
    )
    finder = ProspectFinder(session, crawler=ScriptedCrawler(PAGES))

    prospect = (await finder.find(artifacts=artifacts(), segment=segment()))[0]

    assert not prospect.verified
    assert not prospect.reachable
    assert "could not be read" in prospect.note
    assert provider.calls["prospect_read"] == 0


@pytest.mark.asyncio
async def test_names_only_reads_nobody(provider: ScriptedProvider, session):
    """Two different asks. Somebody checking whether a segment is real wants
    names; only somebody sending mail is worth four page reads per company."""
    provider.push(
        "prospect_hunt",
        {
            "leads": [
                {"name": "Northgate Repairs", "url": "https://northgate-repairs.example"}
            ]
        },
    )
    crawler = ScriptedCrawler(PAGES)

    found = await ProspectFinder(session, crawler=crawler).find(
        artifacts=artifacts(), segment=segment(), with_contacts=False
    )

    assert [item.name for item in found] == ["Northgate Repairs"]
    assert crawler.crawled == []
    assert provider.calls["prospect_read"] == 0


@pytest.mark.asyncio
async def test_an_organisation_already_on_the_list_is_not_returned_again(
    provider: ScriptedProvider, session
):
    provider.push(
        "prospect_hunt",
        {
            "leads": [
                {"name": "Northgate Repairs", "url": "https://northgate-repairs.example"},
                {"name": "Southgate Repairs", "url": "https://southgate.example"},
            ]
        },
    )
    provider.push("prospect_read", read_payload())

    found = await ProspectFinder(session, crawler=ScriptedCrawler(PAGES)).find(
        artifacts=artifacts(), segment=segment(), known=["northgate repairs"]
    )

    assert [item.name for item in found] == ["Southgate Repairs"]


def test_only_verified_contacts_reach_an_export():
    contacts = [
        Contact(kind=ContactKind.EMAIL, value="real@example.test", verified=True),
        Contact(kind=ContactKind.EMAIL, value="guess@example.test", verified=False),
        Contact(kind=ContactKind.PHONE, value="+441234567", verified=True),
    ]

    assert contacts_of(contacts, ContactKind.EMAIL) == "real@example.test"
    assert contacts_of(contacts, ContactKind.PHONE) == "+441234567"


# --------------------------------------------------- aiming a campaign at one


def test_a_chosen_segment_becomes_the_primary_reader():
    """The whole mechanism by which a market finding reaches the copy.

    Everything downstream - the brief, the cold reader panel, the critic - is
    keyed on the audience model, so a segment placed at its head retargets the
    run without any of them knowing this package exists.
    """
    merged = merge_audience(artifacts(), segment())

    primary = merged.audience.primary()
    assert primary is not None
    assert primary.name == segment().name
    assert primary.sophistication is Sophistication.UNAWARE
    assert [pain.grounding for pain in primary.pains] == [Grounding.INFERRED]
    # The company's own idea of its buyer is kept behind it: a strategist that
    # can see both is making a choice.
    assert [item.name for item in merged.audience.segments][1] == "E-commerce support teams"


def test_the_chosen_reader_s_objection_is_the_first_one_answered():
    merged = merge_audience(artifacts(), segment())

    assert merged.audience.objections[0].objection == "we are too small for software like this"
    assert merged.audience.objections[0].grounding is Grounding.INFERRED


def test_a_segment_the_compiler_already_knew_is_replaced_not_duplicated():
    """Two segments with one name is how the cold reader ends up decided by a
    coin flip - and the market's version is the one carrying the trigger and
    the pains that made it worth choosing."""
    base = artifacts()
    chosen = segment(name="E-commerce support teams", kind=SegmentKind.CORE)

    merged = merge_audience(base, chosen)

    names = [item.name for item in merged.audience.segments]
    assert names == ["E-commerce support teams"]
    assert merged.audience.segments[0].situation == chosen.who


def test_an_objection_the_compiler_already_recorded_is_not_added_twice():
    base = artifacts()
    base.audience.objections = [
        Objection(objection="We are too small for software like this", answer="the free tier")
    ]

    merged = merge_audience(base, segment())

    assert len(merged.audience.objections) == 1
    # The compiler's entry survives, because it is the one that knows what
    # answers the doubt.
    assert merged.audience.objections[0].answer == "the free tier"


def test_choosing_nothing_changes_nothing():
    base = artifacts()

    assert merge_audience(base, None) is base


def test_a_merged_audience_does_not_touch_the_stored_artifacts():
    """One campaign's targeting must not retarget every other campaign
    attached to the same brand."""
    base = artifacts()
    base.audience.segments = [Segment(name="Only this one", pains=[Fact(statement="x")])]

    merge_audience(base, segment())

    assert [item.name for item in base.audience.segments] == ["Only this one"]
