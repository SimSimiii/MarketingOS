"""The user-triggered relevance dossier HTTP lifecycle."""

import json
import time
from uuid import UUID

from fastapi.testclient import TestClient
from sqlmodel import Session

import app.api.routes.market as market_routes
from app.market.audience_research import AudienceProblem, AudienceResearch
from app.market.claims import ClaimAxis
from app.market.positioning import AxisReading, PositioningMap, Territory
from app.market.qualification import (
    AudienceDefinition,
    CompanyQualification,
    qualification_identity,
)
from app.market.radar import MarketSnapshot
from app.market.store import MarketStore
from app.models.market import ProspectRow
from app.services import market_service
from tests.api.conftest import await_terminal_status
from tests.api.test_knowledge_base import compile_for_brand


def make_brand(client: TestClient) -> dict:
    response = client.post("/api/brands", json={"name": "Relevance API"})
    assert response.status_code == 201, response.text
    return response.json()


def prepare_inputs(engine, brand_id: str) -> None:
    compile_for_brand(engine, brand_id)
    with Session(engine) as session:
        store = MarketStore(session)
        store.save_research(
            UUID(brand_id),
            AudienceResearch(
                audience_name="Repair shops",
                candidate_kind="adjacent",
                problems=[
                    AudienceProblem(
                        id="P1",
                        statement="Warranty questions consume the first hour of every day.",
                        cost="one hour every day",
                    )
                ],
            ),
            None,
        )
        store.save_scan(
            UUID(brand_id),
            MarketSnapshot(
                positioning=PositioningMap(
                    readings=[
                        AxisReading(
                            axis=ClaimAxis.SPEED, territory=Territory.OPEN
                        )
                    ],
                    rivals_profiled=2,
                )
            ),
        )


def await_market_job(client: TestClient, brand_id: str) -> dict:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        body = client.get(f"/api/market/{brand_id}/job").json()
        if body and body["state"] != "running":
            return body
        time.sleep(0.02)
    raise AssertionError("market job did not finish")


def answer() -> str:
    return json.dumps(
        {
            "orientation": "Release-note automation for teams losing time to manual updates.",
            "ranked_relevance": [
                {
                    "evidence_id": "E1",
                    "band": "LEAD",
                    "why": "The measured outcome directly addresses the researched time cost.",
                    "problem_ids": ["P1"],
                }
            ],
            "problem_fits": [
                {
                    "problem_id": "P1",
                    "verdict": "SOLVED",
                    "evidence_ids": ["E1"],
                }
            ],
        }
    )


def test_status_and_generation_report_all_missing_prerequisites(client: TestClient):
    brand = make_brand(client)

    status = client.get(
        f"/api/market/{brand['id']}/audience/relevance/status",
        params={"segment": "Repair shops"},
    )
    generate = client.post(
        f"/api/market/{brand['id']}/audience/relevance",
        json={"segment": "Repair shops"},
    )

    assert status.status_code == 200
    assert status.json()["status"] == "missing"
    assert {item["code"] for item in status.json()["missing_prerequisites"]} == {
        "knowledge",
        "audience_research",
        "market_scan",
    }
    assert generate.status_code == 409
    detail = generate.json()["detail"]
    assert "Product Knowledge" in detail
    assert "Deep Audience Research" in detail
    assert "Market Scan" in detail


def test_discovery_only_campaign_preflight_makes_zero_writer_calls(client, provider):
    brand = make_brand(client)
    campaign = client.post(
        "/api/campaigns",
        json={
            "name": "Unqualified discovery",
            "request": "Write exactly 1 email.",
            "product_description": "A text agent layer",
            "brand_id": brand["id"],
            "audience_segment": "An audience without a dossier",
        },
    )
    assert campaign.status_code == 201, campaign.text

    advice = client.get(
        f"/api/campaigns/{campaign.json()['id']}/generation-advice"
    )

    assert advice.status_code == 200
    assert advice.json()["readiness"] == "DISCOVERY_ONLY"
    assert advice.json()["override_required"] is True
    assert provider.calls_by_role["email_writer"] == 0


def test_capability_profile_is_versioned_editable_and_evidence_bounded(
    client: TestClient, engine
):
    brand = make_brand(client)
    prepare_inputs(engine, brand["id"])

    derived = client.post(
        f"/api/market/{brand['id']}/capability-profile/derive", json={}
    )
    assert derived.status_code == 200, derived.text
    first = derived.json()
    assert first["schema_version"] == 2
    assert first["version"] == 1

    capabilities = first["capabilities"]
    capabilities.append(
        {
            "id": "voice_telephony",
            "label": "Voice and telephony runtime",
            "description": "Answers and places calls through a telephony runtime.",
            "state": "verified",
            "evidence": [],
            "aliases": ["phone call handling"],
            "customer_copy_visibility": "internal",
            "note": "Explicit product boundary maintained by the user.",
        }
    )
    saved = client.post(
        f"/api/market/{brand['id']}/capability-profile",
        json={
            "capabilities": capabilities,
            "constraints": first["constraints"],
            "claims": [
                *first["claims"],
                {
                    "text": "Voice works everywhere.",
                    "visibility": "customer",
                    "evidence_ids": ["fabricated"],
                },
            ],
        },
    )

    assert saved.status_code == 200, saved.text
    second = saved.json()
    assert second["version"] == 2
    saved_voice = next(
        item for item in second["capabilities"] if item["id"] == "voice_telephony"
    )
    assert saved_voice["state"] == "unknown"
    assert saved_voice["description"].startswith("Answers and places calls")
    assert saved_voice["aliases"] == ["phone call handling"]
    assert "Voice works everywhere." not in [item["text"] for item in second["claims"]]
    latest = client.get(
        f"/api/market/{brand['id']}/capability-profile"
    ).json()
    assert latest["id"] == second["id"]


def test_pre_extractor_company_result_is_returned_as_stale_unverified(
    client: TestClient, engine
) -> None:
    brand = make_brand(client)
    prepare_inputs(engine, brand["id"])
    assert client.post(
        f"/api/market/{brand['id']}/capability-profile/derive", json={}
    ).status_code == 200
    old_result = CompanyQualification(
        classification="ADJACENT",
        audience_structure_fit="unknown",
        product_capability_fit="unknown",
        evidence_completeness="partial",
        reachability="reachable",
        reason_codes=["insufficient_direct_evidence_for_qualification"],
    )
    with Session(engine) as session:
        session.add(
            ProspectRow(
                brand_id=UUID(brand["id"]),
                segment="Repair shops",
                name="Old extraction",
                verified=True,
                pages_read=2,
                qualification=old_result.model_dump(mode="json"),
            )
        )
        session.commit()

    prospect = client.get(f"/api/market/{brand['id']}/prospects").json()[0]

    assert prospect["qualification"]["classification"] == "UNVERIFIED"
    assert prospect["qualification"]["reason_codes"][0] == "company_qualification_stale"
    assert "company_requirement_extractor_changed" in prospect["qualification"]["reason_codes"]


def test_generate_reuse_rebuild_retrieve_and_audience_listing(
    client: TestClient, engine, provider, monkeypatch
):
    monkeypatch.setattr(market_routes, "engine", engine)
    market_service._jobs.clear()
    brand = make_brand(client)
    prepare_inputs(engine, brand["id"])
    provider.set_default("relevance_analyst", answer())

    generated = client.post(
        f"/api/market/{brand['id']}/audience/relevance",
        json={"segment": "Repair shops"},
    )
    assert generated.status_code == 202, generated.text
    assert await_market_job(client, brand["id"])["state"] == "done"

    latest = client.get(
        f"/api/market/{brand['id']}/audience/relevance/latest",
        params={"segment": "Repair shops"},
    )
    status = client.get(
        f"/api/market/{brand['id']}/audience/relevance/status",
        params={"segment": "Repair shops"},
    )
    audience = client.get(f"/api/market/{brand['id']}/audience")
    assert latest.status_code == 200
    assert latest.json()["status"] == "current"
    assert latest.json()["generation_version"] == 1
    assert latest.json()["dossier"]["ranked_relevance"][0]["evidence_id"] == "E1"
    assert status.json()["dossier_id"] == latest.json()["dossier_id"]
    assert audience.json()["relevance"][0]["status"] == "current"
    assert provider.calls_by_role["relevance_analyst"] == 1

    reused = client.post(
        f"/api/market/{brand['id']}/audience/relevance",
        json={"segment": "Repair shops"},
    )
    assert reused.status_code == 202
    assert reused.json()["state"] == "done"
    assert reused.json()["calls"] == 0
    assert provider.calls_by_role["relevance_analyst"] == 1

    rebuilt = client.post(
        f"/api/market/{brand['id']}/audience/relevance/rebuild",
        json={"segment": "Repair shops"},
    )
    assert rebuilt.status_code == 202
    assert await_market_job(client, brand["id"])["state"] == "done"
    assert provider.calls_by_role["relevance_analyst"] == 2

    latest = client.get(
        f"/api/market/{brand['id']}/audience/relevance/latest",
        params={"segment": "Repair shops"},
    ).json()
    assert latest["generation_version"] == 2
    with Session(engine) as session:
        history = MarketStore(session).dossier_history(
            UUID(brand["id"]), "Repair shops"
        )
    assert [row.generation_version for row in history] == [2, 1]


def test_no_go_preflight_is_free_and_api_launch_remains_advisory(
    client: TestClient, engine, provider, monkeypatch
):
    monkeypatch.setattr(market_routes, "engine", engine)
    market_service._jobs.clear()
    brand = make_brand(client)
    prepare_inputs(engine, brand["id"])
    with Session(engine) as session:
        MarketStore(session).save_research(
            UUID(brand["id"]),
            AudienceResearch(
                audience_name="Repair shops",
                candidate_kind="adjacent",
                definition=AudienceDefinition(
                    required_product_capabilities=["full_saas_backend"]
                ),
                problems=[
                    AudienceProblem(
                        id="P1",
                        statement="Warranty questions consume the first hour of every day.",
                    )
                ],
            ),
            None,
        )
    provider.set_default("relevance_analyst", answer())

    generated = client.post(
        f"/api/market/{brand['id']}/audience/relevance",
        json={"segment": "Repair shops"},
    )
    assert generated.status_code == 202, generated.text
    assert await_market_job(client, brand["id"])["state"] == "done"

    campaign = client.post(
        "/api/campaigns",
        json={
            "name": "Unsafe fit",
            "request": "Write exactly 1 email about the warranty workflow.",
            "product_description": "A text agent layer",
            "brand_id": brand["id"],
            "audience_segment": "Repair shops",
        },
    )
    assert campaign.status_code == 201, campaign.text
    campaign_id = campaign.json()["id"]

    advice = client.get(
        f"/api/campaigns/{campaign_id}/generation-advice"
    ).json()
    assert advice["readiness"] == "NO_GO"
    assert advice["override_required"] is True

    assert provider.calls_by_role["email_writer"] == 0
    started = client.post(
        f"/api/campaigns/{campaign_id}/start",
        json={},
    )
    assert started.status_code == 202, started.text
    receipt = started.json()
    assert receipt["generated_despite_recommendation"] is True
    assert receipt["recommendation_snapshot"]["readiness"] == "NO_GO"
    assert receipt["recommendation_snapshot"]["override_explicit"] is False
    await_terminal_status(client, receipt["id"])


def test_go_narrow_rejects_a_selected_excluded_company_without_override(
    client: TestClient, engine, provider, monkeypatch
):
    monkeypatch.setattr(market_routes, "engine", engine)
    market_service._jobs.clear()
    brand = make_brand(client)
    prepare_inputs(engine, brand["id"])
    with Session(engine) as session:
        _, capability_profile = market_service.MarketService(
            session
        ).ensure_capability_profile(UUID(brand["id"]))
    identity = qualification_identity(capability_profile)

    qualified = CompanyQualification(
        classification="QUALIFIED",
        audience_structure_fit="strong",
        product_capability_fit="strong",
        evidence_completeness="complete",
        reachability="reachable",
        reason_codes=["all_required_signals_verified"],
        identity=identity,
        evidence=[
            {
                "code": "founder_led",
                "value": "true",
                "grounding": "direct",
                "quote": "Founder led and operated.",
                "source_identifier": "https://small.example/about",
            }
        ],
    )
    excluded = CompanyQualification(
        classification="EXCLUDED",
        audience_structure_fit="strong",
        product_capability_fit="mismatch",
        evidence_completeness="complete",
        reachability="reachable",
        reason_codes=["hard_disqualifier:platform_powered"],
        hard_disqualifiers_triggered=["platform_powered"],
        identity=identity,
        evidence=[
            {
                "code": "founder_led",
                "value": "true",
                "grounding": "direct",
                "quote": "Founder led and operated.",
                "source_identifier": "https://platform.example/about",
            },
            {
                "code": "platform_powered",
                "value": "true",
                "grounding": "direct",
                "quote": "Powered by another agent platform.",
                "source_identifier": "https://platform.example/product",
            },
        ],
    )
    with Session(engine) as session:
        MarketStore(session).save_research(
            UUID(brand["id"]),
            AudienceResearch(
                audience_name="Repair shops",
                candidate_kind="adjacent",
                    definition=AudienceDefinition(
                        required_structural_signals=[
                            {"code": "founder_led", "description": "A founder operates it."}
                        ],
                        hard_disqualifiers=[
                            {
                                "code": "platform_powered",
                                "description": "Depends on another platform.",
                                "outcome": "EXCLUDED",
                            }
                        ],
                    ),
                problems=[
                    AudienceProblem(id="P1", statement="Warranty questions consume time.")
                ],
            ),
            None,
        )
        rows = [
            ProspectRow(
                brand_id=UUID(brand["id"]),
                segment="Repair shops",
                name="Small Repair Co",
                verified=True,
                pages_read=2,
                qualification=qualified.model_dump(mode="json"),
            ),
            ProspectRow(
                brand_id=UUID(brand["id"]),
                segment="Repair shops",
                name="Repair Platform Inc",
                verified=True,
                pages_read=3,
                qualification=excluded.model_dump(mode="json"),
            ),
        ]
        session.add_all(rows)
        session.commit()
        excluded_id = rows[1].id

    provider.set_default("relevance_analyst", answer())
    generated = client.post(
        f"/api/market/{brand['id']}/audience/relevance",
        json={"segment": "Repair shops"},
    )
    assert generated.status_code == 202, generated.text
    assert await_market_job(client, brand["id"])["state"] == "done"

    campaign = client.post(
        "/api/campaigns",
        json={
            "name": "Narrow company test",
            "request": "Write exactly 1 email.",
            "product_description": "A text agent layer",
            "brand_id": brand["id"],
            "audience_segment": "Repair shops",
            "prospect_id": str(excluded_id),
        },
    )
    assert campaign.status_code == 201, campaign.text
    campaign_id = campaign.json()["id"]

    advice = client.get(
        f"/api/campaigns/{campaign_id}/generation-advice"
    ).json()
    assert advice["readiness"] == "GO_NARROW"
    assert advice["selected_company_qualification"]["classification"] == "EXCLUDED"
    assert advice["override_required"] is True

    assert advice["recommendation"]["qualified_companies"][0]["name"] == "Small Repair Co"
    assert advice["recommendation"]["excluded_companies"][0]["name"] == "Repair Platform Inc"
    assert provider.calls_by_role["email_writer"] == 0
