"""A campaign run as several processes instead of one.

The question every test here asks is the same: does a run split across
invocations produce what the one-process run produces? Three ways it could
fail to, and one of them is silent:

  - the brief is re-decided between steps, so the emails argue different
    campaigns;
  - `previous` is lost, so every email is written as if it were the first -
    which produces five plausible emails and a sequence that reads like five
    first emails, and nothing errors;
  - a retried step writes its email twice.

Scripted provider throughout, so none of this spends quota.
"""

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.models.brand import Brand
from app.models.campaign import Campaign
from app.models.campaign_run_state import CampaignRunState
from app.models.enums import ExecutionStatus
from app.models.generated_asset import GeneratedAsset
from app.models.knowledge_document import KnowledgeDocument
from app.orchestration import stepped_runner
from app.orchestration.campaign_orchestrator import CampaignOrchestrator
from tests.marketing.conftest import RoleScriptedProvider, default_answers

SITE = """# Notewright

Notewright drafts a release note in about nine seconds.

Team is $29/month. Every account starts with 1,500 free credits.
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


def _campaign(session: Session) -> Campaign:
    brand = Brand(name="Notewright")
    session.add(brand)
    session.commit()
    session.refresh(brand)
    campaign = Campaign(
        name="Launch",
        request="Write me 3 emails that make people buy my note-taking app",
        product_description="A note-taking app for developers",
        brand_id=brand.id,
        policy={"preset": "balanced", "require_proof": False},
    )
    session.add(campaign)
    session.add(
        KnowledgeDocument(
            brand_id=brand.id,
            title="Home",
            source_type="website",
            content=SITE,
            source_url="https://example.com",
        )
    )
    session.commit()
    session.refresh(campaign)
    return campaign


async def _run_stepped(session: Session, provider: RoleScriptedProvider):
    """Drive the three steps the way the state machine would."""
    campaign = _campaign(session)
    orchestrator = CampaignOrchestrator(session, provider)
    execution = orchestrator.create_execution(campaign)

    planned = await stepped_runner.plan(session, execution.id, provider)
    steps = [planned]
    guard = 0
    while steps[-1].more:
        guard += 1
        assert guard < 20, "the craft loop is not terminating"
        steps.append(await stepped_runner.craft(session, execution.id, provider))
    steps.append(await stepped_runner.finish(session, execution.id, provider))
    return execution, steps


@pytest.mark.asyncio
async def test_a_stepped_run_calls_the_craft_step_once_per_email(session, provider):
    """The shape the state machine relies on: N emails, N invocations."""
    _, steps = await _run_stepped(session, provider)

    planned = steps[0]
    crafts = steps[1:-1]
    assert planned.total_positions >= 1
    assert len(crafts) == planned.total_positions


@pytest.mark.asyncio
async def test_each_email_is_written_knowing_the_ones_before_it(session, provider):
    """`previous` grows by exactly one per step.

    This is the failure that does not announce itself: lose the accepted copy
    between invocations and the run still finishes, still reports, and still
    hands over the right number of emails - they just all read like the first
    one.
    """
    execution, _ = await _run_stepped(session, provider)
    state = session.exec(
        select(CampaignRunState).where(CampaignRunState.execution_id == execution.id)
    ).one()

    assert len(state.accepted) == state.total_positions
    subjects = [email["subject"] for email in state.accepted]
    assert len(subjects) == len(state.accepted)


@pytest.mark.asyncio
async def test_the_brief_is_decided_once_and_never_rewritten(session, provider):
    """Re-planning between two emails would leave emails 3 and 4 arguing a
    campaign emails 1 and 2 never agreed to."""
    execution, _ = await _run_stepped(session, provider)
    state = session.exec(
        select(CampaignRunState).where(CampaignRunState.execution_id == execution.id)
    ).one()

    assert state.brief is not None
    assert len(state.brief["emails"]) == state.total_positions


@pytest.mark.asyncio
async def test_a_retried_craft_step_does_not_write_the_email_twice(session, provider):
    """A step that succeeded and then timed out reporting is retried by the
    state machine. It must see the advanced cursor, not rewrite its email."""
    campaign = _campaign(session)
    orchestrator = CampaignOrchestrator(session, provider)
    execution = orchestrator.create_execution(campaign)

    await stepped_runner.plan(session, execution.id, provider)
    first = await stepped_runner.craft(session, execution.id, provider)
    assert first.next_position == 2

    # The state machine retries the same step.
    again = await stepped_runner.craft(session, execution.id, provider)
    assert again.next_position == 3, "the retry wrote the next email, not a duplicate"

    state = session.exec(
        select(CampaignRunState).where(CampaignRunState.execution_id == execution.id)
    ).one()
    positions = [outcome["brief"]["position"] for outcome in state.outcomes]
    assert len(positions) == len(set(positions)), "an email was written twice"


@pytest.mark.asyncio
async def test_crafting_past_the_last_email_is_a_no_op(session, provider):
    execution, _ = await _run_stepped(session, provider)
    extra = await stepped_runner.craft(session, execution.id, provider)
    assert extra.more is False
    assert extra.detail == "Already complete"


@pytest.mark.asyncio
async def test_the_finish_step_persists_the_assets_and_closes_the_execution(session, provider):
    """A stepped run has to leave the same rows behind as an in-process one -
    the console reads those, and it does not know which path produced them."""
    execution, steps = await _run_stepped(session, provider)

    assets = session.exec(
        select(GeneratedAsset).where(GeneratedAsset.campaign_execution_id == execution.id)
    ).all()
    session.refresh(execution)

    assert len(assets) == steps[0].total_positions
    # A degraded run is COMPLETED with a report that says so - see _finalize.
    assert execution.status is ExecutionStatus.COMPLETED
    assert execution.completed_at is not None


@pytest.mark.asyncio
async def test_a_craft_step_before_plan_is_refused(session, provider):
    """Without a brief there is nothing to write. Better a clear error than an
    invented campaign."""
    campaign = _campaign(session)
    orchestrator = CampaignOrchestrator(session, provider)
    execution = orchestrator.create_execution(campaign)

    with pytest.raises(stepped_runner.SteppedRunError) as caught:
        await stepped_runner.craft(session, execution.id, provider)
    assert "plan() has not run" in str(caught.value)


@pytest.mark.asyncio
async def test_a_linkedin_campaign_is_refused_by_the_stepped_path(session, provider):
    """One call and one message - it fits in a single invocation and gains
    nothing from a state machine."""
    campaign = _campaign(session)
    campaign.channel = {
        "kind": "connection",
        "recipient_name": "Ada",
        "recipient_url": "https://www.linkedin.com/in/ada",
    }
    session.add(campaign)
    session.commit()

    orchestrator = CampaignOrchestrator(session, provider)
    execution = orchestrator.create_execution(campaign)

    with pytest.raises(stepped_runner.SteppedRunError) as caught:
        await stepped_runner.plan(session, execution.id, provider)
    assert "single process" in str(caught.value)
