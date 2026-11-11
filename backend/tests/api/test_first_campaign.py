"""A continuation spends no calls repeating a completed empty research pass."""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlmodel import Session

from app.market.relevance import (
    CampaignReadiness,
    CampaignRecommendation,
    FirstEmailScope,
    RecommendationState,
)
from app.models.brand import Brand
from app.services import first_campaign as flow
from app.services.market_service import JobStatus


@pytest.mark.asyncio
@pytest.mark.parametrize("second_ready,elapsed,expected,optional_gap,decisive_gap", [
    (True, 1, "campaign", False, False), (True, 1, "campaign", True, False),
    (False, 1, "no_campaign", False, False), (True, 901, "budget", False, False),
    (True, 1, "campaign", False, True),
])
async def test_continue_reuses_empty_research_and_keeps_the_negative_first_audience(
    engine, monkeypatch, second_ready, elapsed, expected, optional_gap, decisive_gap,
):
    brand = Brand(name="Recorded brand", website_url="https://example.com/")
    brand_id = brand.id
    with Session(engine) as db:
        db.add(brand)
        db.commit()
    candidates = [SimpleNamespace(name=name, assessment=SimpleNamespace(compatibility="supported"))
                  for name in ("Needs unverified attribution", "Documented workflow")]
    demand = SimpleNamespace(ranked=candidates,
                             admission_for=lambda *a, **kw: SimpleNamespace(researchable=True))
    created = []
    checked = []
    verification = []
    question = "Can an agency see one client's tasks separately?"
    campaign_id = uuid4()

    class Artifacts:
        def __init__(self, _):
            pass

        def source_documents(self, _):
            return ["already read"]

        def load(self, _):
            return SimpleNamespace(fingerprint="same")

    class Knowledge:
        def __init__(self, _):
            pass

        async def refresh_imported_logo(self, _):
            return False

    class Market:
        def __init__(self, _):
            # Empty but completed, current research is still a reusable result.
            self.store = SimpleNamespace(latest_research=lambda *a: (None, SimpleNamespace(problems=[])))

        def snapshot(self, _):
            return object()

        def demand(self, _):
            return demand

        def relevance_status(self, _, name):
            checked.append(name)
            ready = second_ready and name == candidates[1].name and (not decisive_gap or verification)
            question_scope = decisive_gap and name == candidates[0].name
            readiness = CampaignReadiness.GO_NARROW if ready or question_scope else CampaignReadiness.DISCOVERY_ONLY
            return SimpleNamespace(status="current", dossier=SimpleNamespace(
                product_gaps_to_verify=(lambda: ["Unverified causal attribution."])
                if second_ready and (not ready or optional_gap) else list,
                verified_product_questions=[],
                knowledge_id=brand_id,
                orientation="Source-backed workflow",
                first_email_scope=FirstEmailScope(
                    request="Write exactly one email. Introduce the verified workflow.",
                    audience_decision_question=question,
                ) if question_scope else None,
                recommendation=CampaignRecommendation(
                    state=RecommendationState.RECOMMENDED_NARROW if ready or question_scope
                    else RecommendationState.DISCOVERY_ONLY,
                    readiness=readiness,
                    recommended_next_action="Verify missing attribution.", unresolved_objections=[], reasons=[],
                ),
            ))

    class Campaigns:
        def __init__(self, *a):
            pass

        def create_campaign(self, request):
            created.append(request)
            return SimpleNamespace(id=campaign_id)

    async def no_new_research(*a, **kw):
        pytest.fail("A completed empty research pass must not be repurchased")

    async def verify_product_gap(brand, provider, engine, job, **kwargs):
        assert decisive_gap
        verification.append(kwargs["product_gaps"])
        job.state = "done"

    monkeypatch.setattr(flow, "ArtifactStore", Artifacts)
    monkeypatch.setattr(flow, "fingerprint_documents", lambda _: "same")
    monkeypatch.setattr(flow, "KnowledgeService", Knowledge)
    monkeypatch.setattr(flow, "MarketService", Market)
    monkeypatch.setattr(flow, "CampaignService", Campaigns)
    monkeypatch.setattr(flow, "_run_audience_research", no_new_research)
    monkeypatch.setattr(flow, "_run_relevance_dossier", verify_product_gap if decisive_gap else no_new_research)
    monkeypatch.setattr(flow, "_require_search", lambda *args: None)
    times = iter([0, elapsed, elapsed, elapsed])
    monkeypatch.setattr(flow, "monotonic", lambda: next(times))
    status = JobStatus(kind="first_campaign", brand_id=brand_id)
    await flow.prepare_first_campaign(brand_id, object(), engine, status, "Introduce the verified workflow.")

    assert status.calls == 0
    assert verification == ([[question]] if decisive_gap else [])
    if expected == "campaign":
        assert status.state == "done" and status.campaign_id == campaign_id
        assert created[0].audience_segment == candidates[1].name
        assert created[0].policy_preset == "fast"
        assert candidates[0].name in checked
        assert status.audience == candidates[1].name
    elif expected == "no_campaign":
        assert status.state == "done" and not created and status.campaign_id is None
        assert set(checked) == {candidates[0].name, candidates[1].name}
    else:
        assert status.state == "failed" and not created
        assert "time budget" in status.error
