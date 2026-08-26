"""The persistence adapter: what a run leaves behind in the database.

The orchestrator makes no decisions - these tests are about what is recorded,
and about the one thing that makes compiled knowledge worth compiling: the
second campaign for a brand does not pay for it again.
"""

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.models.agent_execution import AgentExecution
from app.models.brand import Brand
from app.models.campaign import Campaign
from app.models.enums import AssetType, ExecutionStatus
from app.models.execution_log import ExecutionLog
from app.models.generated_asset import GeneratedAsset
from app.models.knowledge_artifacts import KnowledgeArtifactSet
from app.models.knowledge_document import KnowledgeDocument
from app.orchestration.campaign_orchestrator import CampaignOrchestrator
from tests.marketing.conftest import CRITIQUE_REVISE, RoleScriptedProvider, default_answers

SITE = """# Notewright

Notewright drafts a release note in about nine seconds.

Team is $29/month. Every account starts with 1,500 free credits.
"""

PRICING = """# Pricing

Solo is $9/month. Team is $29/month. Enterprise is quoted.
"""


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
async def test_every_draft_is_recorded_in_full_including_the_ones_that_lost(
    session: Session, provider: RoleScriptedProvider
):
    """A writer turn used to leave a subject line behind and nothing else.

    That makes the only question worth asking about a rewrite - what changed,
    and did it help - unanswerable from the record, which is how four attempts
    can circle back to a draft that was already read and thrown away without
    anyone being able to see it happen.
    """
    campaign = make_campaign(session)
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
    assert critiques[0].data["unspent_evidence"] == ["E1"]
    assert critiques[0].data["brief_drift"]


@pytest.mark.asyncio
async def test_the_run_stores_the_report_and_the_brief_it_worked_from(
    session: Session, provider: RoleScriptedProvider
):
    campaign = make_campaign(session)
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
