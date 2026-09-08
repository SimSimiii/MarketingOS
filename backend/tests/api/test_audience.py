"""The demand side over HTTP: a mapped audience, a prospect list, and an export.

Everything here is scoped to a brand, like the rest of the market. The tests
worth reading are the last two: the export is the only route in the system
that hands a user data to send mail with, and what it is allowed to contain -
reviewed rows only, verified contacts only - is a product promise rather than
an implementation detail.
"""

import asyncio
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.ai.base import ResearchTool
from app.ai.factory import get_ai_provider
from app.core.database import get_session
from app.main import app
from app.market.audience_research import AudienceResearch
from app.market.demand import AudienceSegment, DemandMap, MapOptions, Prospect, SegmentKind
from app.market.qualification import CompanyQualification
from app.market.store import MarketStore
from app.models.campaign import Campaign
from app.models.market import ProspectRow
from app.orchestration.campaign_orchestrator import _DbKnowledgeGateway
from app.services.market_service import JobStatus, MarketService, _run_audience_map, job_for
from tests.api.test_knowledge_base import compile_for_brand
from tests.marketing.conftest import default_answers


def make_brand(client: TestClient, name: str) -> dict:
    response = client.post("/api/brands", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()


def segment(name: str = "Independent repair shops", **overrides: object) -> AudienceSegment:
    payload: dict = {
        "name": name,
        "kind": SegmentKind.ADJACENT,
        "who": "a three-person shop answering warranty questions by hand",
        "fit": 0.3,
        "basis": "they complain about it publicly",
        "signals": ["a warranty page with an email address"],
        "where": ["UK repair association member directory"],
    }
    payload.update(overrides)
    return AudienceSegment(**payload)


def store_map(engine, brand_id: str, *segments: AudienceSegment) -> None:
    with Session(engine) as session:
        MarketStore(session).save_map(
            UUID(brand_id),
            DemandMap(segments=list(segments), reading="one industry over"),
        )


def store_prospect(engine, brand_id: str, **overrides: object) -> ProspectRow:
    payload: dict = {
        "brand_id": UUID(brand_id),
        "segment": "Independent repair shops",
        "name": "Northgate Repairs",
        "url": "https://northgate-repairs.example",
        "what_they_do": "refurbishes business laptops",
        "why_them": "they answer warranty questions by hand",
        "fit": 0.85,
        "verified": True,
        "contacts": [
            {
                "kind": "email",
                "value": "hello@northgate-repairs.example",
                "label": "general enquiries",
                "source": "https://northgate-repairs.example/contact",
                "verified": True,
            }
        ],
    }
    payload.update(overrides)
    row = ProspectRow(**payload)
    with Session(engine) as session:
        session.add(row)
        session.commit()
        session.refresh(row)
    return row


def test_an_unmapped_brand_says_why_it_is_empty(client: TestClient):
    """A blank page reads as a broken feature; a sentence about what has not
    happened yet reads as a button to press."""
    brand = make_brand(client, "Helpdesk")

    body = client.get(f"/api/market/{brand['id']}/audience").json()

    assert body["map"] is None
    assert "Nobody has mapped" in body["note"]


def test_unreadable_v2_company_has_qualification_but_no_match_percentage(
    client: TestClient, engine
):
    brand = make_brand(client, "Helpdesk")
    store_prospect(
        engine,
        brand["id"],
        name="Directory-only Dental AI",
        verified=False,
        pages_read=0,
        qualification={
            "classification": "UNVERIFIED",
            "audience_structure_fit": "unknown",
            "product_capability_fit": "unknown",
            "evidence_completeness": "missing",
            "reachability": "unknown",
            "reason_codes": ["site_unreadable"],
        },
    )

    response = client.get(f"/api/market/{brand['id']}/prospects")

    assert response.status_code == 200
    prospect = response.json()[0]
    assert prospect["qualification"]["classification"] == "UNVERIFIED"
    assert prospect["fit"] is None


def test_researchability_ties_preserve_order_without_guessed_fit(client: TestClient, engine):
    brand = make_brand(client, "Helpdesk")
    store_map(
        engine,
        brand["id"],
        segment(
            "Core buyers",
            kind=SegmentKind.CORE,
            who="e-commerce support teams triaging order questions across a shared queue",
            signals=["job postings for e-commerce support agents"],
            where=["G2 reviews for customer support tools"],
            fit=0.15,
        ),
        segment("Independent repair shops", fit=0.34),
    )

    body = client.get(f"/api/market/{brand['id']}/audience").json()

    assert [item["name"] for item in body["map"]["segments"]] == [
        "Core buyers",
        "Independent repair shops",
    ]
    # The flag the page sorts and filters by, and the reason to have run this
    # at all - it is a property on the domain model, so it has to be carried
    # explicitly or it silently ships as absent.
    assert body["map"]["segments"][0]["unobvious"] is False
    assert body["map"]["segments"][1]["unobvious"] is True
    assert body["map"]["segments"][0]["researchable"] is True
    assert body["map"]["segments"][0]["researchability"] == "low"
    assert body["map"]["segments"][0]["researchability_reasons"]


def test_the_api_ranks_researchability_before_fit(client: TestClient, engine):
    brand = make_brand(client, "Helpdesk")
    store_map(
        engine,
        brand["id"],
        segment("Repair shops answering warranty requests", fit=0.9),
        segment(
            "SaaS teams shipping their first AI feature",
            who="small SaaS engineering teams shipping their first customer-facing AI feature",
            signals=[
                "job postings for AI platform engineers",
                "GitHub issues discussing production evaluation failures",
            ],
            where=["r/devops", "GitHub issues in LangChain repositories"],
            trigger="their first AI feature recently entered customer beta",
            population="roughly 3,000 seed-stage SaaS companies",
            fit=0.1,
        ),
    )

    body = client.get(f"/api/market/{brand['id']}/audience").json()

    assert [item["researchability"] for item in body["map"]["segments"]] == [
        "high",
        "low",
    ]


def test_the_market_page_counts_the_demand_side_without_fetching_it(
    client: TestClient, engine
):
    brand = make_brand(client, "Helpdesk")
    store_map(engine, brand["id"], segment())
    store_prospect(engine, brand["id"])

    body = client.get(f"/api/market/{brand['id']}").json()

    assert body["audience_segments"] == 1
    assert body["prospects"] == 1


def test_one_brand_never_sees_another_s_prospects(client: TestClient, engine):
    first = make_brand(client, "Helpdesk")
    second = make_brand(client, "Foldwork")
    store_prospect(engine, first["id"])

    body = client.get(f"/api/market/{second['id']}/audience").json()

    assert body["prospects"] == []


def test_prospects_can_be_narrowed_to_one_segment(client: TestClient, engine):
    brand = make_brand(client, "Helpdesk")
    store_prospect(engine, brand["id"], name="Northgate", segment="Independent repair shops")
    store_prospect(engine, brand["id"], name="Wholesale Co", segment="Distributors")

    body = client.get(
        f"/api/market/{brand['id']}/audience", params={"segment": "Distributors"}
    ).json()

    assert [item["name"] for item in body["prospects"]] == ["Wholesale Co"]


def test_a_prospect_can_be_kept_or_dismissed(client: TestClient, engine):
    brand = make_brand(client, "Helpdesk")
    row = store_prospect(engine, brand["id"])

    kept = client.post(
        f"/api/market/{brand['id']}/prospects/{row.id}", json={"status": "kept"}
    )

    assert kept.status_code == 200, kept.text
    assert kept.json()["status"] == "kept"
    assert kept.json()["decided_at"] is not None


def test_a_stale_prospect_reread_updates_evidence_without_losing_the_user_decision(
    client: TestClient, engine
) -> None:
    brand = make_brand(client, "Helpdesk")
    existing = store_prospect(
        engine,
        brand["id"],
        status="kept",
        qualification={
            "classification": "UNVERIFIED",
            "audience_structure_fit": "unknown",
            "product_capability_fit": "unknown",
            "evidence_completeness": "missing",
            "reachability": "unknown",
            "reason_codes": ["company_qualification_stale"],
        },
    )
    refreshed_qualification = CompanyQualification(
        classification="EXCLUDED",
        audience_structure_fit="unknown",
        product_capability_fit="mismatch",
        evidence_completeness="missing",
        reachability="reachable",
        reason_codes=["unsupported_required_capability:warehouse_robotics"],
        hard_disqualifiers_triggered=[
            "unsupported_required_capability:warehouse_robotics"
        ],
    )

    with Session(engine) as session:
        stored = MarketStore(session).record_prospects(
            UUID(brand["id"]),
            [
                Prospect(
                    name=existing.name,
                    url=existing.url,
                    segment=existing.segment,
                    what_they_do="Freshly verified company description",
                    verified=True,
                    pages_read=3,
                    qualification=refreshed_qualification,
                )
            ],
        )[0]

        assert stored.id == existing.id
        assert stored.status == "kept"
        assert stored.what_they_do == "Freshly verified company description"
        assert stored.qualification["classification"] == "EXCLUDED"
        assert len(MarketStore(session).prospects(UUID(brand["id"]))) == 1


def test_an_unknown_decision_is_refused_rather_than_stored(client: TestClient, engine):
    brand = make_brand(client, "Helpdesk")
    row = store_prospect(engine, brand["id"])

    response = client.post(
        f"/api/market/{brand['id']}/prospects/{row.id}", json={"status": "maybe"}
    )

    assert response.status_code == 422


def test_a_prospect_belonging_to_another_brand_is_a_404(client: TestClient, engine):
    first = make_brand(client, "Helpdesk")
    second = make_brand(client, "Foldwork")
    row = store_prospect(engine, first["id"])

    response = client.post(
        f"/api/market/{second['id']}/prospects/{row.id}", json={"status": "kept"}
    )

    assert response.status_code == 404


def test_mapping_without_compiled_knowledge_is_refused_before_anything_is_spent(
    client: TestClient,
):
    brand = make_brand(client, "Helpdesk")

    response = client.post(f"/api/market/{brand['id']}/audience/map", json={})

    assert response.status_code == 409
    assert "knowledge" in response.json()["detail"].lower()


def test_a_segment_that_is_not_on_the_map_is_refused_at_the_request(
    client: TestClient, engine
):
    """A 409 the user can act on beats a job that starts, spends a search call
    and reports the same thing two minutes later."""
    brand = make_brand(client, "Helpdesk")
    compile_for_brand(engine, brand["id"])
    store_map(engine, brand["id"], segment())

    response = client.post(
        f"/api/market/{brand['id']}/audience/prospects",
        json={"segment": "People who do not exist"},
    )

    assert response.status_code == 409
    assert "audience map" in response.json()["detail"]


def test_an_unresearchable_segment_is_refused_before_a_search_can_spend(
    client: TestClient, engine
):
    brand = make_brand(client, "Helpdesk")
    compile_for_brand(engine, brand["id"])
    store_map(
        engine,
        brand["id"],
        segment(
            "developers",
            who="",
            signals=["uses software"],
            where=["LinkedIn"],
        ),
    )

    response = client.post(
        f"/api/market/{brand['id']}/audience/prospects",
        json={"segment": "developers"},
    )

    assert response.status_code == 409
    assert "not researchable" in response.json()["detail"]
    assert "no prospect search was started" in response.json()["detail"].lower()


def test_audience_research_rejects_missing_unknown_and_unadmitted_candidates(
    client: TestClient, engine
):
    brand = make_brand(client, "Helpdesk research admission")
    store_map(
        engine,
        brand["id"],
        segment(
            "developers",
            who="",
            signals=["uses software"],
            where=["LinkedIn"],
        ),
    )

    missing = client.post(f"/api/market/{brand['id']}/audience/research", json={})
    unknown = client.post(
        f"/api/market/{brand['id']}/audience/research",
        json={"segment": "not on the map"},
    )
    unadmitted = client.post(
        f"/api/market/{brand['id']}/audience/research",
        json={"segment": "developers"},
    )

    assert missing.status_code == 422
    assert unknown.status_code == 409
    assert "current audience map" in unknown.json()["detail"]
    assert unadmitted.status_code == 409
    assert "No useful observable signal" in unadmitted.json()["detail"]


def test_api_returns_the_latest_persisted_audience_research(client: TestClient, engine):
    brand = make_brand(client, "Helpdesk researched")
    chosen = segment()
    store_map(engine, brand["id"], chosen)
    with Session(engine) as session:
        store = MarketStore(session)
        for _ in range(2):
            store.save_research(
                UUID(brand["id"]),
                AudienceResearch(
                    audience_name=chosen.name,
                    candidate_kind=str(chosen.kind),
                ),
                store.latest_map_row(UUID(brand["id"])),
            )

    latest = client.get(
        f"/api/market/{brand['id']}/audience/research/latest",
        params={"segment": chosen.name},
    )
    audience = client.get(f"/api/market/{brand['id']}/audience")

    assert latest.status_code == 200
    assert latest.json()["version"] == 2
    assert latest.json()["audience_name"] == chosen.name
    assert [item["version"] for item in audience.json()["research"]] == [2]


def test_the_export_carries_only_the_rows_a_human_kept(client: TestClient, engine):
    """`new` means nobody has looked at it. A file that quietly includes
    unreviewed rows defeats the review it came from - the user believes they
    exported the ones they checked."""
    brand = make_brand(client, "Helpdesk")
    kept = store_prospect(engine, brand["id"], name="Northgate Repairs")
    store_prospect(engine, brand["id"], name="Unreviewed Ltd", url="https://unreviewed.example")
    store_prospect(
        engine,
        brand["id"],
        name="Dismissed Ltd",
        url="https://dismissed.example",
        status="dismissed",
    )
    client.post(f"/api/market/{brand['id']}/prospects/{kept.id}", json={"status": "kept"})

    response = client.get(f"/api/market/{brand['id']}/prospects.csv")

    assert response.status_code == 200
    body = response.content.decode("utf-8-sig")
    assert "Northgate Repairs" in body
    assert "Unreviewed Ltd" not in body
    assert "Dismissed Ltd" not in body
    # Every address travels with the page it was read on: this list is about
    # to be mailed, and a contact whose provenance was dropped at the door is
    # one nobody downstream can check.
    assert "https://northgate-repairs.example/contact" in body


def test_the_export_never_carries_an_unverified_contact(client: TestClient, engine):
    brand = make_brand(client, "Helpdesk")
    row = store_prospect(
        engine,
        brand["id"],
        contacts=[
            {
                "kind": "email",
                "value": "real@northgate-repairs.example",
                "source": "https://northgate-repairs.example/contact",
                "verified": True,
            },
            {
                "kind": "email",
                "value": "guessed@northgate-repairs.example",
                "source": "",
                "verified": False,
            },
        ],
    )
    client.post(f"/api/market/{brand['id']}/prospects/{row.id}", json={"status": "kept"})

    body = client.get(f"/api/market/{brand['id']}/prospects.csv").content.decode("utf-8-sig")

    assert "real@northgate-repairs.example" in body
    assert "guessed@northgate-repairs.example" not in body


# ------------------------------------------------- aiming a campaign at one


def test_a_campaign_can_be_created_against_a_mapped_segment(
    client: TestClient, engine
):
    brand = make_brand(client, "Helpdesk")
    store_map(engine, brand["id"], segment())

    created = client.post(
        "/api/campaigns",
        json={
            "name": "Repair shops",
            "request": "Write exactly 1 email that sells my product",
            "product_description": "answers repetitive customer questions",
            "brand_id": brand["id"],
            "audience_segment": "Independent repair shops",
        },
    )

    assert created.status_code == 201, created.text
    assert created.json()["audience_segment"] == "Independent repair shops"


def test_the_chosen_segment_reaches_the_run_as_its_primary_reader(
    client: TestClient, engine
):
    """The whole point of the field, asserted where it actually takes effect.

    The gateway is what a run reads its knowledge through, so this is the
    join between a form field and the person every draft is written to and
    graded by - and it works by rewriting the audience model rather than by
    adding a special case anywhere downstream.
    """
    brand = make_brand(client, "Helpdesk")
    compile_for_brand(engine, brand["id"])
    store_map(engine, brand["id"], segment())

    created = client.post(
        "/api/campaigns",
        json={
            "name": "Repair shops",
            "request": "Write exactly 1 email that sells my product",
            "product_description": "answers repetitive customer questions",
            "brand_id": brand["id"],
            "audience_segment": "Independent repair shops",
        },
    ).json()

    with Session(engine) as session:
        campaign = session.get(Campaign, UUID(created["id"]))
        stored = _DbKnowledgeGateway(session, campaign).load()

    assert stored is not None
    primary = stored.artifacts.audience.primary()
    assert primary is not None
    assert primary.name == "Independent repair shops"
    # The compile is untouched: the merge happens at read time, so a campaign
    # aimed at one buyer does not retarget every other campaign on the brand.
    assert stored.fingerprint == "fp"


def test_a_campaign_that_named_nobody_reads_the_compiled_audience(
    client: TestClient, engine
):
    brand = make_brand(client, "Helpdesk")
    compile_for_brand(engine, brand["id"])
    store_map(engine, brand["id"], segment())

    created = client.post(
        "/api/campaigns",
        json={
            "name": "Everybody",
            "request": "Write exactly 1 email that sells my product",
            "product_description": "answers repetitive customer questions",
            "brand_id": brand["id"],
        },
    ).json()

    with Session(engine) as session:
        campaign = session.get(Campaign, UUID(created["id"]))
        gateway = _DbKnowledgeGateway(session, campaign)
        stored = gateway.load()

    assert created["audience_segment"] is None
    assert gateway.audience_choice() == ""
    assert stored is not None
    assert stored.artifacts.audience.primary() is None


# ------------------------------------------------- audiences you add yourself


#: The whole required form. Four lines, and they are four rather than one
#: because they are exactly what `AudienceSegment.admission` reads as a
#: situation rather than a category.
MINIMUM = {
    "name": "Shopify warranty desks",
    "organization": "three-person Shopify stores selling refurbished laptops",
    "workflow": "answering warranty questions by hand out of a shared inbox",
    "need": "cut the time each warranty ticket takes",
}

#: The same audience with the two things a search can actually be spent on.
RESEARCHABLE = {
    **MINIMUM,
    "signals": ["their storefront has a published warranty page with an email address"],
    "where": ["Shopify app store reviews for warranty apps"],
}


def add_audience(client: TestClient, brand_id: str, payload: dict | None = None) -> dict:
    response = client.post(
        f"/api/market/{brand_id}/audience/segments", json=payload or MINIMUM
    )
    assert response.status_code == 201, response.text
    return response.json()


def mapped_names(client: TestClient, brand_id: str) -> list[str]:
    body = client.get(f"/api/market/{brand_id}/audience").json()
    return [item["name"] for item in (body["map"] or {"segments": []})["segments"]]


def test_an_audience_can_be_added_without_a_map_or_a_search(client: TestClient):
    """The point of the feature: knowing your buyer already is a valid state.

    Nothing here compiles knowledge, scans a market or maps demand, so a user
    who can describe their audience reaches research without buying a
    discovery run to be told what they already knew."""
    brand = make_brand(client, "Warranty desk")
    assert client.get(f"/api/market/{brand['id']}/audience").json()["map"] is None

    added = add_audience(client, brand["id"])

    body = client.get(f"/api/market/{brand['id']}/audience").json()
    assert added["name"] == MINIMUM["name"]
    assert added["added_by"] == "user"
    assert [item["name"] for item in body["map"]["segments"]] == [MINIMUM["name"]]
    assert "you described yourself" in body["map"]["validation_note"]


def test_the_minimum_form_saves_and_says_what_research_still_needs(client: TestClient):
    """A half-written audience is savable, and the receipt is the teacher.

    The alternative - refusing to store anything until the form is complete -
    duplicates `admission` in a validator and loses the idea the user was in
    the middle of having."""
    brand = make_brand(client, "Warranty desk")

    added = add_audience(client, brand["id"])

    assert added["researchable"] is False
    assert added["researchability"] == "unresearchable"
    assert added["researchability_reasons"] == [
        "No useful observable signal identifies this audience.",
        "No specific venue or source says where this audience can be found.",
    ]


def test_one_signal_and_one_venue_make_it_researchable(client: TestClient):
    brand = make_brand(client, "Warranty desk")

    added = add_audience(client, brand["id"], RESEARCHABLE)

    assert added["researchable"] is True
    assert added["researchability"] == "low"


def test_a_hand_written_audience_never_claims_verified_evidence(client: TestClient):
    """Saying who your buyer is is a claim about your intent, not a reading of
    the market. It may never outrank an audience somebody actually checked."""
    brand = make_brand(client, "Warranty desk")

    added = add_audience(client, brand["id"], RESEARCHABLE)

    assert added["assessment"]["evidence"] == []
    assert added["assessment"]["evidence_strength"] == "absent"
    assert added["assessment"]["priority"] == "hypothesis"
    assert any(
        "nothing on the open web has been checked" in reason
        for reason in added["assessment"]["reasons"]
    )


def test_research_actually_starts_on_an_audience_the_user_added(web_client: TestClient):
    """The other half of the feature: the analysis has to run on it."""
    brand = make_brand(web_client, "Warranty desk")
    add_audience(web_client, brand["id"], RESEARCHABLE)

    response = web_client.post(
        f"/api/market/{brand['id']}/audience/research",
        json={"segment": RESEARCHABLE["name"]},
    )

    assert response.status_code == 202, response.text
    assert response.json()["kind"] == "audience_research"
    assert job_for(UUID(brand["id"])) is not None


def test_prospecting_starts_on_an_audience_the_user_added(
    web_client: TestClient, engine
):
    brand = make_brand(web_client, "Warranty desk")
    compile_for_brand(engine, brand["id"])
    add_audience(web_client, brand["id"], RESEARCHABLE)

    response = web_client.post(
        f"/api/market/{brand['id']}/audience/prospects",
        json={"segment": RESEARCHABLE["name"]},
    )

    assert response.status_code == 202, response.text
    assert job_for(UUID(brand["id"])) is not None


def test_an_added_audience_survives_a_remap_that_replaces_the_list(
    client: TestClient, engine
):
    """The reason these are rows rather than part of the map payload.

    A refresh replaces the compiled map wholesale. An audience written into
    that payload would be gone the first time somebody pressed rescan, taking
    the research and the prospects pointing at its name with it."""
    brand = make_brand(client, "Warranty desk")
    add_audience(client, brand["id"], RESEARCHABLE)
    store_map(engine, brand["id"], segment("Independent repair shops"))
    store_map(engine, brand["id"], segment("Refurbishers"))

    assert mapped_names(client, brand["id"]) == [RESEARCHABLE["name"], "Refurbishers"]


def test_a_remap_reads_the_cartographer_s_own_last_map_not_the_merged_one(
    client: TestClient, engine
):
    """`previous` is what an explore run retains into its next payload. Merged
    audiences reaching it would be copied into the compiled map, where the
    following refresh would silently drop them again."""
    brand = make_brand(client, "Warranty desk")
    add_audience(client, brand["id"], RESEARCHABLE)
    store_map(engine, brand["id"], segment("Independent repair shops"))

    with Session(engine) as session:
        store = MarketStore(session)
        compiled = store.compiled_map(UUID(brand["id"]))
        merged = store.latest_map(UUID(brand["id"]))

    assert [item.name for item in compiled.segments] == ["Independent repair shops"]
    assert [item.name for item in merged.segments] == [
        RESEARCHABLE["name"],
        "Independent repair shops",
    ]


def test_your_own_audience_wins_a_name_collision_with_a_mapped_one(
    client: TestClient, engine
):
    """On the subject of their own buyer the user is the authority - the same
    rule the rival list follows when a scan re-proposes a muted competitor."""
    brand = make_brand(client, "Warranty desk")
    add_audience(client, brand["id"], RESEARCHABLE)
    store_map(engine, brand["id"], segment(RESEARCHABLE["name"], who="found by the map"))

    body = client.get(f"/api/market/{brand['id']}/audience").json()

    assert len(body["map"]["segments"]) == 1
    assert body["map"]["segments"][0]["added_by"] == "user"
    assert body["map"]["segments"][0]["organization"] == RESEARCHABLE["organization"]


def test_a_second_audience_with_the_same_name_is_refused(client: TestClient):
    brand = make_brand(client, "Warranty desk")
    add_audience(client, brand["id"])

    again = client.post(
        f"/api/market/{brand['id']}/audience/segments",
        json={**MINIMUM, "name": "  shopify WARRANTY desks "},
    )

    assert again.status_code == 409
    assert "already added" in again.json()["detail"]


def test_an_edit_fills_in_what_the_receipt_asked_for(client: TestClient):
    brand = make_brand(client, "Warranty desk")
    add_audience(client, brand["id"])

    edited = client.patch(
        f"/api/market/{brand['id']}/audience/segments", json=RESEARCHABLE
    )

    assert edited.status_code == 200, edited.text
    assert edited.json()["researchable"] is True
    assert mapped_names(client, brand["id"]) == [MINIMUM["name"]]


def test_deleting_an_audience_leaves_the_research_it_already_paid_for(
    client: TestClient, engine
):
    """Those calls cost real quota and remain readable on their own. Taking
    them along would be a decision the user did not make."""
    brand = make_brand(client, "Warranty desk")
    add_audience(client, brand["id"], RESEARCHABLE)
    with Session(engine) as session:
        MarketStore(session).save_research(
            UUID(brand["id"]),
            AudienceResearch(audience_name=RESEARCHABLE["name"], candidate_kind="core"),
            None,
        )

    removed = client.delete(
        f"/api/market/{brand['id']}/audience/segments",
        params={"name": RESEARCHABLE["name"]},
    )

    body = client.get(f"/api/market/{brand['id']}/audience").json()
    assert removed.status_code == 204
    assert body["map"] is None
    assert [item["audience_name"] for item in body["research"]] == [RESEARCHABLE["name"]]


def test_only_an_audience_you_added_can_be_edited_or_removed(client: TestClient, engine):
    brand = make_brand(client, "Warranty desk")
    store_map(engine, brand["id"], segment())

    edited = client.patch(
        f"/api/market/{brand['id']}/audience/segments",
        json={**MINIMUM, "name": segment().name},
    )
    removed = client.delete(
        f"/api/market/{brand['id']}/audience/segments",
        params={"name": segment().name},
    )

    assert edited.status_code == 404
    assert removed.status_code == 404
    assert mapped_names(client, brand["id"]) == [segment().name]


def test_a_blank_required_line_is_refused_rather_than_stored(client: TestClient):
    brand = make_brand(client, "Warranty desk")

    for field in ("name", "organization", "workflow", "need"):
        response = client.post(
            f"/api/market/{brand['id']}/audience/segments",
            json={**MINIMUM, field: "   "},
        )
        assert response.status_code == 422, field

    assert client.get(f"/api/market/{brand['id']}/audience").json()["map"] is None


def test_one_brand_never_sees_another_s_added_audiences(client: TestClient):
    mine = make_brand(client, "Warranty desk")
    theirs = make_brand(client, "Somebody else")
    add_audience(client, mine["id"])

    assert client.get(f"/api/market/{theirs['id']}/audience").json()["map"] is None


# --------------------------------------------------------- launching the job


@pytest.fixture
def web_client(engine, provider):
    """A client whose provider declares web access.

    The default scripted provider offers no `ResearchTool` at all, so every
    market job is refused by `_require_web` before it starts - which is why
    nothing in this suite reached `asyncio.create_task` until these tests, and
    why a launch route that could not spawn a task at all passed CI.
    """

    class WebScriptedProvider(type(provider)):
        def available_tools(self, model: str | None = None) -> frozenset[ResearchTool]:
            return frozenset({ResearchTool.WEB_SEARCH, ResearchTool.WEB_FETCH})

    web_provider = WebScriptedProvider(default_answers())

    def session_override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_ai_provider] = lambda: web_provider
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_mapping_the_audience_actually_starts_a_job(web_client: TestClient, engine):
    """The regression test for `RuntimeError: no running event loop`.

    A sync FastAPI handler runs in a worker thread with no event loop, so the
    `asyncio.create_task` inside it could never spawn anything - the launch
    routes have to be `async def`. Asserting the 202 is not enough on its own:
    the exception was raised *by* the handler, so this passes only if the task
    was really created.
    """
    brand = make_brand(web_client, "Helpdesk")
    compile_for_brand(engine, brand["id"])

    response = web_client.post(f"/api/market/{brand['id']}/audience/map", json={})

    assert response.status_code == 202, response.text
    assert job_for(UUID(brand["id"])) is not None


def test_map_route_passes_scope_without_spending_quota(client, monkeypatch):
    brand = make_brand(client, "Scoped discovery")
    captured = []

    def launch(self, brand, provider, engine, options=None):
        captured.append(options)
        return JobStatus(kind="audience", brand_id=brand.id)

    monkeypatch.setattr(MarketService, "launch_audience_map", launch)
    response = client.post(f"/api/market/{brand['id']}/audience/map", json={
        "geography": "France", "language": "Français", "objective": "partners",
        "exclusions": "Healthcare", "mode": "explore",
    })
    assert response.status_code == 202
    assert captured[0].geography == "France"
    assert captured[0].objective == "partners"
    assert captured[0].mode == "explore"
    bad = client.post(f"/api/market/{brand['id']}/audience/map", json={"objective": "invent"})
    assert bad.status_code == 422
    assert len(captured) == 1


def test_map_job_supplies_current_product_truth_and_persists_scope(
    client, engine, provider, monkeypatch
):
    from app.market.demand import AudienceCartographer

    brand = make_brand(client, "Validated discovery")
    compile_for_brand(engine, brand["id"])
    store_map(engine, brand["id"], segment())
    options = MapOptions(geography="France")
    captured = []

    async def mapped(self, artifacts, **kwargs):
        captured.append(kwargs)
        kwargs["progress"]("Checked the test corpus")
        return DemandMap(segments=[segment()], options=kwargs["options"], validation_note="Checked")

    monkeypatch.setattr(AudienceCartographer, "map", mapped)
    status = JobStatus(kind="audience", brand_id=UUID(brand["id"]))
    asyncio.run(_run_audience_map(UUID(brand["id"]), provider, engine, status, options))
    assert status.state == "done", status.error
    assert captured[0]["capability_profile"].knowledge_id
    assert captured[0]["previous"].segments[0].name == segment().name
    body = client.get(f"/api/market/{brand['id']}/audience").json()
    assert body["map"]["options"]["geography"] == "France"
    assert body["map"]["validation_note"] == "Checked"


def test_an_admitted_audience_research_actually_starts_a_job(
    web_client: TestClient, engine
):
    brand = make_brand(web_client, "Helpdesk audience research")
    chosen = segment()
    store_map(engine, brand["id"], chosen)

    response = web_client.post(
        f"/api/market/{brand['id']}/audience/research",
        json={"segment": chosen.name},
    )

    assert response.status_code == 202, response.text
    assert response.json()["kind"] == "audience_research"
    assert job_for(UUID(brand["id"])) is not None


def test_a_scan_starts_a_job_too(web_client: TestClient, engine):
    """The same bug lived in the older launch routes, unreached by any test."""
    brand = make_brand(web_client, "Helpdesk")
    compile_for_brand(engine, brand["id"])

    response = web_client.post(
        f"/api/market/{brand['id']}/scan", json={"discover": True}
    )

    assert response.status_code == 202, response.text
    assert job_for(UUID(brand["id"])) is not None
