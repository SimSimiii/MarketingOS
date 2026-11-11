"""The persistence adapter: what a run leaves behind in the database.

The orchestrator makes no decisions - these tests are about what is recorded,
and about the one thing that makes compiled knowledge worth compiling: the
second campaign for a brand does not pay for it again.
"""

import hashlib
from datetime import UTC, datetime

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.knowledge.artifacts import CallToAction
from app.knowledge.ledger import Evidence, EvidenceKind
from app.market.audience_research import FetchedSource, SourceTier
from app.market.material_research import MaterialRecovery
from app.marketing.briefs import CampaignBrief, EmailBrief
from app.marketing.email_copy import parse_email
from app.models.agent_execution import AgentExecution
from app.models.brand import Brand
from app.models.campaign import Campaign
from app.models.campaign_execution import CampaignExecution
from app.models.enums import AssetType, ExecutionStatus
from app.models.execution_log import ExecutionLog
from app.models.generated_asset import GeneratedAsset
from app.models.knowledge_artifacts import KnowledgeArtifactSet
from app.models.knowledge_document import KnowledgeDocument
from app.orchestration.campaign_orchestrator import CampaignOrchestrator, _DbKnowledgeGateway
from tests.marketing.conftest import (
    CRITIQUE_REVISE,
    RoleScriptedProvider,
    artifacts_fixture,
    campaign_brief,
    default_answers,
    email_draft,
)

SITE = """# Notewright

Notewright drafts a release note in about nine seconds.

Team is $29/month. Every account starts with 1,500 free credits.
"""

PRICING = """# Pricing

Solo is $9/month. Team is $29/month. Enterprise is quoted.
"""


@pytest.mark.parametrize("scheme", ["https", "HTTPS"])
def test_render_uses_only_the_resolved_button_destination(session, provider, scheme):
    wrong = "https://canny.io/pricing"
    correct = f"{scheme}://canny.io/integrations/intercom"
    campaign = make_campaign(session)
    orchestrator = CampaignOrchestrator(session, provider)
    email = parse_email(email_draft(cta="Connect Intercom to Autopilot"), 1)
    brief = EmailBrief(call_to_action=f"Review the documentation: {wrong}")
    artifacts = artifacts_fixture()
    artifacts.offer.calls_to_action.append(CallToAction(label="See pricing", url=wrong))
    plain, html, _ = orchestrator.render_email(campaign, email, brief, artifacts)
    assert wrong not in plain and wrong not in html
    brief.next_step_url = correct
    plain, html, _ = orchestrator.render_email(campaign, email, brief, artifacts)
    assert correct in plain
    assert f'href="{correct}"' in html
    assert wrong not in html


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def provider() -> RoleScriptedProvider:
    return RoleScriptedProvider(default_answers())


def make_campaign(session: Session, brand: Brand | None = None, **overrides) -> Campaign:
    # These tests are about what a run records, not about whether it should
    # have started. Most of them attach no material at all, which compiles to
    # no evidence at all - the one case the preflight stop exists for, and it
    # would end every one of them before the first role turn. Merged rather
    # than defaulted so a test that passes its own policy still gets it; the
    # stop has its own tests, which set it back on.
    policy = {"preset": "balanced", "require_proof": False, **(overrides.pop("policy", None) or {})}
    campaign = Campaign(
        name="Launch",
        request="Write me 3 emails that make people buy my note-taking app",
        product_description="A note-taking app for developers",
        brand_id=brand.id if brand else None,
        policy=policy,
        **overrides,
    )
    session.add(campaign)
    session.commit()
    session.refresh(campaign)
    return campaign


def add_document(
    session: Session,
    campaign: Campaign | None,
    brand: Brand | None,
    content: str = SITE,
    title: str = "Home",
) -> None:
    session.add(
        KnowledgeDocument(
            campaign_id=campaign.id if campaign else None,
            brand_id=brand.id if brand else None,
            title=title,
            source_type="website",
            content=content,
            source_url="https://example.com",
        )
    )
    session.commit()


def test_automatically_recovered_material_is_filed_and_reused(
    session: Session,
):
    brand = Brand(name="Notewright")
    session.add(brand)
    session.commit()
    session.refresh(brand)
    add_document(session, None, brand)
    campaign = make_campaign(session, brand=brand)
    page = "The native integration fills the SMTP settings automatically."
    source = FetchedSource(
        requested_url="https://docs.example.com/integration",
        final_url="https://docs.example.com/integration",
        title="Official integration",
        tier=SourceTier.INTERPRETATION,
        venue="Example",
        fetched_at=datetime.now(UTC),
        content_hash=hashlib.sha256(page.encode("utf-8")).hexdigest(),
        content=page,
    )
    recovery = MaterialRecovery(
        gap="The exact SMTP integration path is absent.",
        sources=[source],
        evidence=[
            Evidence(
                id="R1",
                kind=EvidenceKind.INTEGRATION,
                claim="the native integration fills the SMTP settings",
                verbatim=page,
                source=source.final_url,
            )
        ],
    )
    artifacts = artifacts_fixture()
    artifacts.evidence.entries.extend(recovery.evidence)

    gateway = _DbKnowledgeGateway(session, campaign)
    stored = gateway.commit_recovered_material(recovery, artifacts)

    recovered = session.exec(
        select(KnowledgeDocument).where(KnowledgeDocument.source_url == source.final_url)
    ).one()
    assert recovered.document_metadata["automatically_discovered"] is True
    assert stored.artifacts.evidence.get("R1").document_id == str(recovered.id)
    assert page in gateway.corpus().text


@pytest.mark.asyncio
async def test_a_run_records_every_role_turn_and_the_emails_that_shipped(
    session: Session, provider: RoleScriptedProvider
):
    campaign = make_campaign(session)
    execution = await CampaignOrchestrator(session, provider).run(campaign)

    assert execution.status == ExecutionStatus.COMPLETED
    assert execution.total_input_tokens > 0
    assert execution.estimated_cost_usd > 0

    rows = session.exec(select(AgentExecution)).all()
    # `inbox_scanner` is deliberately absent: it runs inside the subject
    # writer's turn, the way the cold reader runs inside the bake-off's. One
    # decision, one row - the timeline is a list of judgments made, not of
    # model calls billed.
    assert {row.agent_id for row in rows} == {
        "claim_reviewer",
        "strategist",
        "email_writer",
        "blind_reader",
        "conversion_critic",
        "sequence_reviewer",
        "preference_judge",
        "subject_writer",
    }
    assert all(row.status == ExecutionStatus.COMPLETED for row in rows)
    # Steps are numbered in the order they happened, one per role turn.
    assert [row.sequence_order for row in rows] == list(range(1, len(rows) + 1))

    assets = session.exec(select(GeneratedAsset)).all()
    assert len(assets) == 3, "one row per email, not one per draft"
    assert all(asset.asset_type == AssetType.EMAIL for asset in assets)
    assert all(asset.content.startswith("Subject: ") for asset in assets)
    assert {asset.position for asset in assets} == {1, 2, 3}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("intent", "expected"),
    [(None, "branded"), ({"reader_relationship": "cold"}, "plain")],
)
async def test_with_no_tier_chosen_the_writer_and_the_renderer_agree_on_one(
    session: Session, provider: RoleScriptedProvider, intent, expected
):
    """A brand writing to readers who are not cold comes out branded, cold
    outreach stays plain - and the writer is told the same answer the
    renderer draws, so a headline is never written for a layout that drops
    it."""
    brand = Brand(name="Notewright", website_url="https://notewright.example/")
    session.add(brand)
    session.commit()
    session.refresh(brand)
    add_document(session, None, brand)
    campaign = make_campaign(session, brand=brand, intent=intent)

    await CampaignOrchestrator(session, provider).run(campaign)

    assets = session.exec(select(GeneratedAsset)).all()
    assert assets
    assert {asset.asset_metadata["tier"] for asset in assets} == {expected}
    prompt = provider.requests_for("email_writer")[0].system_prompt or ""
    if expected == "branded":
        assert "laid out as mail from the company" in prompt
        assert all('href="https://notewright.example/"' in asset.content_html for asset in assets)
    else:
        assert "laid out as a plain letter" in prompt
        assert all("notewright.example" not in asset.content_html for asset in assets)


def test_a_branded_email_shows_the_photograph_of_the_page_its_button_leads_to(
    session: Session, provider: RoleScriptedProvider
):
    """The crawler recorded the product page's own photograph; the email whose
    button leads there shows it, and no other email does."""
    brand = Brand(name="Cabaia", website_url="https://www.cabaia.fr/")
    session.add(brand)
    session.commit()
    session.refresh(brand)
    session.add(
        KnowledgeDocument(
            brand_id=brand.id, title="Duffle", source_type="website", content=SITE,
            source_url="https://www.cabaia.fr/products/duffle",
            document_metadata={"identity": {
                "image_url": "https://cdn.example/duffle.jpg", "image_alt": "Duffle Adventurer",
                "image_width": 1200, "image_height": 1200,
            }},
        )
    )
    session.commit()
    brief = CampaignBrief.model_validate_json(campaign_brief(count=1)).emails[0]
    email = parse_email(email_draft(), 1)
    orchestrator = CampaignOrchestrator(session, provider)

    def rendered(**overrides) -> str:
        campaign = make_campaign(session, brand=brand, **overrides)
        _, html, _ = orchestrator.render_email(campaign, email, brief, None)
        return html or ""

    shown = rendered(cta_url="https://cabaia.fr/products/duffle/?variant=2")
    assert 'src="https://cdn.example/duffle.jpg"' in shown
    assert 'alt="Duffle Adventurer"' in shown
    assert "duffle.jpg" not in rendered(
        cta_url="https://www.cabaia.fr/products/duffle", intent={"reader_relationship": "cold"}
    ), "cold mail is a letter, and a letter has no product shot"
    assert "<img" not in rendered(cta_url="https://www.cabaia.fr/products/tote")


@pytest.mark.asyncio
async def test_every_draft_is_recorded_in_full_including_the_ones_that_lost(
    session: Session, provider: RoleScriptedProvider
):
    """A writer turn used to leave a subject line behind and nothing else.

    That makes the only question worth asking about a rewrite - what changed,
    and did it help - unanswerable from the record, which is how four attempts
    can circle back to a draft that was already read and thrown away without
    anyone being able to see it happen.
    """
    campaign = make_campaign(
        session,
        policy={"preset": "balanced", "draft_candidates": 3},
    )
    execution = await CampaignOrchestrator(session, provider).run(campaign)

    drafts = session.exec(
        select(ExecutionLog).where(
            ExecutionLog.campaign_execution_id == execution.id,
            ExecutionLog.event_type == "draft",
        )
    ).all()

    assert len(drafts) >= 9, "three emails, three candidate openings each"
    assert all(draft.data["body"] for draft in drafts), "the body is the point"
    assert all(draft.step is not None for draft in drafts), "each belongs to a writer turn"
    assert {draft.data["position"] for draft in drafts} == {1, 2, 3}


@pytest.mark.asyncio
async def test_every_cold_reader_is_recorded_not_only_the_first(
    session: Session, provider: RoleScriptedProvider
):
    """A panel of three used to be reported as the panel's score beside the
    first reader's verdict, with the other two dropped - which is exactly the
    disagreement the panel is paid for."""
    campaign = make_campaign(
        session, policy={"preset": "balanced", "reader_panel": True, "draft_candidates": 1}
    )
    execution = await CampaignOrchestrator(session, provider).run(campaign)

    reviews = session.exec(
        select(ExecutionLog).where(
            ExecutionLog.campaign_execution_id == execution.id,
            ExecutionLog.event_type == "review",
        )
    ).all()

    assert reviews
    for review in reviews:
        readers = review.data["readers"]
        assert len(readers) == 3
        assert all(reader["persona"] for reader in readers)
        assert len({reader["persona"] for reader in readers}) == 3


@pytest.mark.asyncio
async def test_a_critique_records_the_edits_it_asked_for(
    session: Session, provider: RoleScriptedProvider
):
    """"10 edit(s) requested" with no way to read the ten edits is a summary
    of work the user paid for and cannot inspect."""
    provider.set_default("conversion_critic", CRITIQUE_REVISE)
    campaign = make_campaign(session)
    execution = await CampaignOrchestrator(session, provider).run(campaign)

    critiques = session.exec(
        select(ExecutionLog).where(
            ExecutionLog.campaign_execution_id == execution.id,
            ExecutionLog.event_type == "critique",
        )
    ).all()

    assert critiques
    edits = critiques[0].data["edits"]
    assert edits and all(edit["problem"] and edit["fix"] for edit in edits)
    assert critiques[0].data["failure_mode"] == "copy"
    assert critiques[0].data["strategy_gap"] == ""
    assert critiques[0].data["unspent_evidence"] == ["E1"]
    assert critiques[0].data["brief_drift"]


@pytest.mark.asyncio
async def test_the_run_stores_the_report_and_the_brief_it_worked_from(
    session: Session, provider: RoleScriptedProvider
):
    campaign = make_campaign(session)
    campaign.cta_url = "https://notewright.test/signup"
    execution = await CampaignOrchestrator(session, provider).run(campaign)

    assert execution.result is not None
    assert execution.result["run_status"] == "completed"
    assert execution.result["report"]["delivered"] == 3
    assert execution.result["brief"]["emails"][0]["single_idea"]


@pytest.mark.asyncio
async def test_a_second_campaign_for_the_same_brand_reuses_the_compiled_knowledge(
    session: Session, provider: RoleScriptedProvider
):
    """The point of compiling: the second campaign starts from everything the
    first one learned instead of re-reading the same site."""
    brand = Brand(name="Notewright")
    session.add(brand)
    session.commit()
    session.refresh(brand)
    add_document(session, None, brand)

    first = make_campaign(session, brand=brand)
    await CampaignOrchestrator(session, provider).run(first)
    compiles_after_first = provider.calls_by_role["knowledge_compiler"]
    assert compiles_after_first > 0, "the first run has to read the site"

    second = make_campaign(session, brand=brand)
    await CampaignOrchestrator(session, provider).run(second)

    assert provider.calls_by_role["knowledge_compiler"] == compiles_after_first
    # One artifact set, shared - not one per campaign.
    assert len(session.exec(select(KnowledgeArtifactSet)).all()) == 1


@pytest.mark.asyncio
async def test_changed_material_is_recompiled(session: Session, provider: RoleScriptedProvider):
    brand = Brand(name="Notewright")
    session.add(brand)
    session.commit()
    session.refresh(brand)
    add_document(session, None, brand)

    await CampaignOrchestrator(session, provider).run(make_campaign(session, brand=brand))
    after_first = provider.calls_by_role["knowledge_compiler"]

    # The user uploads their pricing page: a page the compiler has not read.
    add_document(session, None, brand, content=PRICING, title="Pricing")
    await CampaignOrchestrator(session, provider).run(make_campaign(session, brand=brand))

    assert provider.calls_by_role["knowledge_compiler"] > after_first
    versions = session.exec(select(KnowledgeArtifactSet)).all()
    assert sorted(row.version for row in versions) == [1, 2], "versions are kept, not overwritten"


@pytest.mark.asyncio
async def test_the_same_page_filed_twice_is_not_new_material(
    session: Session, provider: RoleScriptedProvider
):
    """Adding a brand's website is not a one-time act - it happens again every
    time a campaign is created for that brand. A second, identical copy of a
    page the compiler has already read is not a reason to read it again, and
    treating it as one is how "reuse what's already compiled" ended up
    recompiling anyway."""
    brand = Brand(name="Notewright")
    session.add(brand)
    session.commit()
    session.refresh(brand)
    add_document(session, None, brand)

    await CampaignOrchestrator(session, provider).run(make_campaign(session, brand=brand))
    after_first = provider.calls_by_role["knowledge_compiler"]
    assert after_first > 0, "the first run has to read the site"

    add_document(session, None, brand)  # the same home page, word for word
    await CampaignOrchestrator(session, provider).run(make_campaign(session, brand=brand))

    assert provider.calls_by_role["knowledge_compiler"] == after_first
    assert len(session.exec(select(KnowledgeArtifactSet)).all()) == 1


@pytest.mark.asyncio
async def test_a_campaign_without_a_brand_keeps_its_knowledge_to_itself(
    session: Session, provider: RoleScriptedProvider
):
    first = make_campaign(session)
    add_document(session, first, None)
    await CampaignOrchestrator(session, provider).run(first)

    second = make_campaign(session)
    add_document(session, second, None)
    await CampaignOrchestrator(session, provider).run(second)

    rows = session.exec(select(KnowledgeArtifactSet)).all()
    assert len(rows) == 2
    assert {row.campaign_id for row in rows} == {first.id, second.id}
    assert all(row.brand_id is None for row in rows)


@pytest.mark.asyncio
async def test_a_failed_run_is_persisted_as_a_failure_rather_than_swallowed(
    session: Session, provider: RoleScriptedProvider
):
    provider.set_default("strategist", "I cannot help with that.")
    campaign = make_campaign(session)

    execution = await CampaignOrchestrator(session, provider).run(campaign)

    assert execution.status == ExecutionStatus.FAILED
    assert execution.error_message
    assert session.exec(select(GeneratedAsset)).all() == []


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["exception", "restart"])
async def test_accepted_emails_survive_a_failure_before_sequence_review(session, provider, monkeypatch, failure):
    from app.core import database
    from app.marketing.pipeline import EmailCampaignPipeline
    from app.orchestration.execution_manager import reap_orphaned_executions

    class ProcessStopped(BaseException):
        pass

    async def stop(*args, **kwargs):
        if failure == "exception":
            raise RuntimeError("Sequence step crashed")
        raise ProcessStopped("Process terminated")

    monkeypatch.setattr(EmailCampaignPipeline, "_phase_sequence", stop)
    campaign = make_campaign(session, cta_url="https://example.com/product")
    orchestrator = CampaignOrchestrator(session, provider)
    if failure == "exception":
        execution = await orchestrator.run(campaign)
    else:
        with pytest.raises(ProcessStopped):
            await orchestrator.run(campaign)
        monkeypatch.setattr(database, "engine", session.get_bind())
        assert reap_orphaned_executions() == 1
        assert reap_orphaned_executions() == 0
        session.expire_all()
        execution = session.exec(select(CampaignExecution)).one()
    assert execution.status == ExecutionStatus.COMPLETED
    assert execution.result["run_status"] == "degraded"
    assert execution.error_message
    assets = session.exec(select(GeneratedAsset)).all()
    assert len(assets) == 3
    assert {asset.position for asset in assets} == {1, 2, 3}
    assert all(asset.asset_metadata["sequence_review_pending"] for asset in assets)
    assert all(asset.content.startswith("Subject:") for asset in assets)
    assert all("https://example.com/product" in asset.content for asset in assets)


@pytest.mark.asyncio
async def test_normal_completion_discards_checkpoints_and_produces_only_final_assets(session, provider):
    execution = await CampaignOrchestrator(session, provider).run(make_campaign(session))
    assets = session.exec(select(GeneratedAsset)).all()
    assert len(assets) == 3
    assert "accepted_checkpoints" not in execution.result
    assert all(not asset.asset_metadata.get("checkpoint") for asset in assets)
