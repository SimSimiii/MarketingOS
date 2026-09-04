"""The audience experiment's own correctness, checked for free.

Experiment 1 costs three campaigns per golden case and Experiment 2 costs a
panel per draft, so both run rarely - and a benchmark that runs rarely is
exactly the kind of code that quietly stops working. Worse, an audience
experiment fails *silently*: if the arm that was supposed to carry a demand map
does not, three runs still complete, still produce three different sets of
numbers (the pipeline is stochastic), and a reader looking at pull would read
that noise as an effect.

So these tests do not check that the benchmark runs. They check the thing that
makes it an experiment: that the arms differ where they claim to, that the arm
which claims to change nothing changes nothing, and that the second experiment
really does hold the copy still.

The first test in the file is the finding the whole exercise rests on.
"""

import json
import tempfile
from collections import Counter
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.ai.model_router import ModelRouter
from app.core.config import PROMPTS_DIR
from app.evaluation.audience import (
    ARMS,
    AudienceCondition,
    all_markers,
    arm_for,
    cases_with_fixtures,
    persona_conditions,
)
from app.evaluation.audience_bench import render_case
from app.evaluation.golden import case_named
from app.evaluation.persona_bench import built_in_drafts, panel_for, run_persona_bench
from app.evaluation.probe import PromptProbe
from app.evaluation.record import RunRecord, record_from
from app.evaluation.scaffold import PROBED_ROLES, UnknownArm, prepare_case
from app.knowledge.store import ArtifactScope, ArtifactStore
from app.marketing.email_copy import render_email
from app.marketing.pipeline import EmailCampaignPipeline
from app.marketing.policy import PRESETS
from app.marketing.reader import BlindReader
from app.marketing.request import CampaignRequest
from app.models.knowledge_document import KnowledgeDocument
from app.orchestration.campaign_orchestrator import _DbKnowledgeGateway
from app.runtime.events import EventBus
from app.runtime.model_session import ModelSession
from app.runtime.prompt_engine import PromptEngine
from tests.marketing.conftest import (
    RoleScriptedProvider,
    artifacts_fixture,
    campaign_brief,
    default_answers,
    make_session,
)

CASE = "rich-single"


@pytest.fixture
def db():
    """A benchmark's disposable database, built the way the runner builds it.

    File-backed rather than in-memory for the reason `tests/api/conftest.py`
    gives: these tests hold a session open across a pipeline run, and one
    shared connection turns two sessions into one transaction.
    """
    with tempfile.TemporaryDirectory() as workspace:
        engine = create_engine(f"sqlite:///{Path(workspace) / 'eval.db'}")
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            yield session
        # Windows will not delete a file a connection still holds, and the
        # pool holds one until it is told otherwise - without this the
        # temporary directory's own cleanup raises and every test using this
        # fixture errors in teardown having already passed.
        engine.dispose()


def _gateway(session: Session, condition: AudienceCondition | None):
    campaign = prepare_case(session, case_named(CASE), "balanced", condition)
    return campaign, _DbKnowledgeGateway(session, campaign)


# ----------------------------------------------------- the finding itself


def test_the_benchmark_as_it_was_could_not_reach_any_market_intelligence(db):
    """The premise of the whole experiment, asserted rather than believed.

    `runner.run_case` created its campaign with no `brand_id`, and both market
    reads on the gateway are brand-scoped. Every golden round ever run
    therefore planned its strategy against `positioning=None, demand=None` and
    an empty audience choice - and nothing in the record said so, because the
    record had no field for it.
    """
    campaign, gateway = _gateway(db, None)

    assert campaign.brand_id is None
    assert gateway.positioning() is None
    assert gateway.demand() is None
    assert gateway.audience_choice() == ""


def test_the_legacy_path_still_owns_its_documents(db):
    """Backwards compatibility, at the row level: a run with no condition is
    campaign-scoped exactly as it was."""
    campaign, gateway = _gateway(db, None)

    documents = db.exec(KnowledgeDocument.__table__.select()).all()

    assert gateway.scope == ArtifactScope(campaign_id=campaign.id)
    assert documents and all(row.campaign_id == campaign.id for row in documents)
    assert all(row.brand_id is None for row in documents)


# ------------------------------------------------------------- the arms


def test_a_brand_scoped_case_resolves_the_audience_map(db):
    """What the experiment had to make possible: an evaluation campaign that
    can see a demand map at all."""
    campaign, gateway = _gateway(db, AudienceCondition.CURRENT)

    demand = gateway.demand()

    assert campaign.brand_id is not None
    assert demand is not None
    assert gateway.audience_choice() == arm_for(CASE, AudienceCondition.CURRENT).chosen
    assert demand.named(gateway.audience_choice()) is not None


def test_arm_none_carries_the_scaffolding_and_none_of_the_intelligence(db):
    """The control arm is brand-scoped too.

    If only the audience arms had a brand, the comparison would confound the
    audience with where knowledge is stored, what `prior_learnings` reads and
    whether approved proof is merged. All three are held constant instead, and
    the arm still answers None to everything the experiment is about.
    """
    campaign, gateway = _gateway(db, AudienceCondition.NONE)

    assert campaign.brand_id is not None
    assert gateway.scope.is_brand
    assert gateway.demand() is None
    assert gateway.positioning() is None
    assert gateway.audience_choice() == ""


@pytest.mark.parametrize(
    ("condition", "marker"),
    [
        (AudienceCondition.CURRENT, "keep each of them informed about what changed"),
        (AudienceCondition.RESEARCHED, "rewrites the same deploy summary"),
    ],
)
def test_the_chosen_segment_reaches_the_compiled_audience(db, condition, marker):
    """The production merge, exercised through the production gateway.

    `_with_market` puts the chosen segment at the head of the audience model on
    every read, which is what carries a market decision into a pipeline that
    knows nothing about the market package. If this stopped working, arms B and
    C would silently become arm A with extra rows in the database.
    """
    _, gateway = _gateway(db, condition)

    stored = gateway.save(artifacts_fixture(), gateway.fingerprint())

    primary = stored.artifacts.audience.primary()
    assert primary is not None
    assert primary.name == arm_for(CASE, condition).chosen
    assert marker in primary.situation


def test_an_arm_a_case_has_no_fixture_for_is_refused_rather_than_faked(db):
    """`thin-evidence` has no control email and no hand-written audience. A
    benchmark that silently ran it with no map would report a three-arm
    comparison in which two arms were the same arm."""
    with pytest.raises(UnknownArm):
        prepare_case(db, case_named("thin-evidence"), "balanced", AudienceCondition.CURRENT)


# --------------------------------------------------- downstream transport


def _scripted(condition: AudienceCondition) -> RoleScriptedProvider:
    """A provider whose strategist behaves like a real one for this arm.

    The one thing scripted here is the strategist naming the segment it was
    pointed at - the decision a real strategist makes when the map arrives with
    `<- THIS CAMPAIGN` beside one entry, and the one decision a fixed script
    cannot make for itself. Everything downstream of it is the system's own
    wiring, which is what this test is about: what the *writer* and the *cold
    readers* end up holding is decided by `merge_audience` and `personas_for`,
    not by anything below.
    """
    provider = RoleScriptedProvider(default_answers())
    arm = arm_for(CASE, condition)
    provider.set_default(
        "strategist",
        campaign_brief(1, reader_segment=arm.chosen if arm else ""),
    )
    return provider


async def _run_arm(condition: AudienceCondition) -> tuple[PromptProbe, list[str]]:
    """One arm of the experiment, end to end, against the scripted provider."""
    case = case_named(CASE)
    provider = _scripted(condition)
    probe = PromptProbe(provider, all_markers(CASE))
    policy = PRESETS["balanced"].model_copy(
        update={
            "draft_candidates": 1,
            "max_revisions": 0,
            "subject_variants": 0,
            "tournament": False,
        }
    )
    with tempfile.TemporaryDirectory() as workspace:
        engine = create_engine(f"sqlite:///{Path(workspace) / 'arm.db'}")
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            campaign = prepare_case(session, case, "balanced", condition)
            pipeline = EmailCampaignPipeline(
                session=ModelSession(
                    provider=probe,
                    prompt_engine=PromptEngine(PROMPTS_DIR),
                    events=EventBus(),
                    model_router=ModelRouter(None),
                    execution_id=f"test-{condition}",
                ),
                knowledge=_DbKnowledgeGateway(session, campaign),
                policy=policy,
            )
            result = await pipeline.run(
                CampaignRequest(
                    name=campaign.name,
                    request=case.request,
                    product_description=case.product_description,
                    target_market=case.target_market,
                    goals=case.goals,
                )
            )
        engine.dispose()  # see the `db` fixture: Windows holds the file open
    from app.evaluation.runner import personas_used

    return probe, personas_used(result, policy)


@pytest.mark.asyncio
async def test_arm_none_shows_no_fixture_phrase_to_any_role():
    """The control arm, proved to be a control.

    Probed for the *other* arms' markers, not merely left unprobed: an arm that
    was supposed to change nothing and an arm that failed to change anything
    look identical from the outside, and only this distinguishes them.
    """
    probe, _ = await _run_arm(AudienceCondition.NONE)

    assert probe.reached(*PROBED_ROLES) == {role: [] for role in PROBED_ROLES}


@pytest.mark.asyncio
async def test_the_current_arm_reaches_the_roles_that_write_and_judge():
    probe, personas = await _run_arm(AudienceCondition.CURRENT)
    reached = probe.reached(*PROBED_ROLES)

    assert "shared.segment" in reached["strategist"]
    assert "current.situation" in reached["email_writer"]
    assert "current.situation" in reached["blind_reader"]
    # Nothing that belongs only to the other arm. The segment name is shared by
    # design - it is what makes the two arms the same buyer - so it is labelled
    # as neither arm's and cannot fake this assertion into passing.
    assert not any(
        label.startswith("researched_fixture.")
        for labels in reached.values()
        for label in labels
    )
    assert all("keep each of them informed" in persona for persona in personas)


@pytest.mark.asyncio
async def test_the_researched_arm_reaches_them_by_the_same_path():
    probe, personas = await _run_arm(AudienceCondition.RESEARCHED)
    reached = probe.reached(*PROBED_ROLES)

    assert "researched_fixture.trigger" in reached["strategist"]
    assert "researched_fixture.situation" in reached["email_writer"]
    assert "researched_fixture.situation" in reached["blind_reader"]
    assert "shared.segment" in reached["strategist"]
    assert not any(
        label.startswith("current.") for labels in reached.values() for label in labels
    )
    assert all("rewrites the same deploy summary" in persona for persona in personas)


@pytest.mark.asyncio
async def test_the_audience_that_reaches_the_pipeline_differs_between_arms():
    """The experiment's validity condition, in one assertion.

    Three arms that hand the same person to the writer and the same panel to
    the reader are three samples of one condition, however different their
    numbers come back.
    """
    arms = {
        condition: await _run_arm(condition)
        for condition in (
            AudienceCondition.NONE,
            AudienceCondition.CURRENT,
            AudienceCondition.RESEARCHED,
        )
    }

    reached = {
        condition: json.dumps(probe.reached(*PROBED_ROLES), sort_keys=True)
        for condition, (probe, _) in arms.items()
    }
    personas = {condition: tuple(people) for condition, (_, people) in arms.items()}

    assert len(set(reached.values())) == 3, reached
    assert len(set(personas.values())) == 3, personas


# ------------------------------------------------------ experiment two


@pytest.mark.asyncio
async def test_both_personas_read_the_identical_drafts(provider: RoleScriptedProvider):
    """Experiment 2's whole premise: the copy does not move between arms.

    Asserted off the prompts that actually went out rather than off the objects
    handed in - the drafts could be identical and the reader still be shown
    something re-rendered, and it is what reached the model that decides what
    the experiment measured.
    """
    case = case_named(CASE)
    drafts = built_in_drafts(case)
    segments = persona_conditions(CASE)

    arms = await run_persona_bench(
        BlindReader(make_session(provider)), drafts, segments, panel=False
    )

    prompts = [call.system_prompt or "" for call in provider.requests_for("blind_reader")]
    assert len(prompts) == len(drafts.drafts) * len(segments)
    # Each draft was put in front of exactly one reader per persona, and the
    # text it was shown as was the same both times.
    shown = Counter(
        label
        for prompt in prompts
        for label, email in drafts.drafts
        if render_email(email) in prompt
    )
    assert shown == Counter({label: len(segments) for label, _ in drafts.drafts})
    # And the only thing that differed is who was reading.
    current = sum(1 for prompt in prompts if "keep each of them informed" in prompt)
    researched = sum(1 for prompt in prompts if "rewrites the same deploy summary" in prompt)
    assert current == researched == len(drafts.drafts)
    assert {arm.shown for arm in arms} == {drafts.fingerprint}


def test_a_persona_is_built_by_the_function_the_craft_loop_uses():
    """The personas under test have to be the ones production would build, or
    the experiment measures a persona shape the system never uses."""
    segment = persona_conditions(CASE)[AudienceCondition.RESEARCHED]

    people = panel_for(segment, panel=True)

    assert len(people) == 3
    assert all(segment.name in person for person in people)
    # The aperture: `personas_for` reads a segment's name and situation and
    # nothing else, which is why the researched fixtures put their detail in
    # `who`. If this ever widens, the fixtures can widen with it.
    assert segment.trigger not in people[0]


def test_the_ranking_is_the_comparison_the_loop_makes(provider: RoleScriptedProvider):
    """Comprehension before pull, ties in input order - `EmailVersion.measured`
    without the terms this experiment holds constant."""
    from app.evaluation.persona_bench import PersonaArm
    from app.marketing.reader import BlindRead, PanelRead

    labels = ("a", "b", "c")
    arm = PersonaArm(
        condition="x",
        reads={
            "a": PanelRead(reads=[BlindRead(clicks_in_100=25, understood=False)]),
            "b": PanelRead(reads=[BlindRead(clicks_in_100=3)]),
            "c": PanelRead(reads=[BlindRead(clicks_in_100=9)]),
        },
    )

    assert arm.ordered(labels) == ["c", "b", "a"]
    assert arm.winner(labels) == "c"


# --------------------------------------------------------- the fixtures


@pytest.mark.parametrize("case", sorted(ARMS), ids=lambda name: name)
def test_every_marker_is_a_real_phrase_from_its_own_arm_and_no_other(case):
    """A marker that is not in the record it names measures nothing, and one
    that is in both arms' records measures the wrong thing. Both failures are
    invisible until a billed round comes back reporting that no arm reached
    anything - so they are caught here."""
    rendered = {
        condition: arm.render() for condition, arm in ARMS[case].items() if arm.demand
    }
    for condition, arm in ARMS[case].items():
        for label, phrase in arm.markers:
            assert phrase in rendered[condition], f"{case}/{condition}/{label}"
            others = [
                other
                for other, text in rendered.items()
                if other != condition and phrase in text
            ]
            # The segment name is deliberately shared - it is what makes the
            # two arms the same buyer. Everything else must separate them.
            if label != "segment":
                assert not others, f"{case}/{condition}/{label} also in {others}"


@pytest.mark.parametrize("case", sorted(ARMS), ids=lambda name: name)
def test_the_two_informed_arms_are_the_same_bet_described_differently(case):
    """The experiment's controls, asserted. A different segment or a different
    fit would mean the strategist was holding a different bet, and the run
    would answer a question about targeting rather than about description."""
    current = arm_for(case, AudienceCondition.CURRENT).segment
    researched = arm_for(case, AudienceCondition.RESEARCHED).segment

    assert current is not None and researched is not None
    assert current.name == researched.name
    assert current.fit == researched.fit
    assert current.kind is researched.kind
    assert current.who != researched.who


@pytest.mark.parametrize("case", sorted(ARMS), ids=lambda name: name)
def test_no_fixture_smuggles_a_figure_into_the_copy(case):
    """`evidence_gate` licenses every figure in a draft against the ledger and
    the corpus. A fixture carrying invented numbers would make the arm with the
    richer persona fail gates because of the fixture rather than because of the
    condition - so the fixtures carry none."""
    for condition, arm in ARMS[case].items():
        if arm.demand is None:
            continue
        from app.knowledge.ledger import ClaimKind, extract_claims

        figures = [
            claim.text
            for claim in extract_claims(arm.render())
            if claim.kind is not ClaimKind.QUOTE
        ]
        # The rendered map states each segment's own fit as a percentage; that
        # is the renderer's arithmetic, not a fact the fixture asserts, and no
        # writer is shown it.
        assert all("%" in figure for figure in figures), f"{case}/{condition}: {figures}"


def test_every_fixtured_case_has_a_human_control_to_be_measured_against():
    """An arm comparison with no control can say the copy changed and never
    whether it got better - which is the question the experiment exists for."""
    for name in cases_with_fixtures():
        assert case_named(name).control_email, name


# --------------------------------------------------- backwards compatible


def test_a_record_written_before_the_experiment_still_loads():
    """Two rounds are compared by loading records written by an earlier version
    of the file, and the audience round must not orphan them."""
    old = json.dumps(
        {"case": "rich-single", "request": "r", "preset": "balanced", "cost_usd": 1.5}
    )

    record = RunRecord.model_validate_json(old)

    assert record.audience_condition == ""
    assert record.audience_reached == {}
    assert record.reader_personas == []
    assert record.emails == []


@pytest.mark.asyncio
async def test_a_run_outside_the_experiment_records_no_condition(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """`record_from` gained four arguments and every one of them defaults to
    the answer a run outside the experiment gives."""
    from dataclasses import replace

    from tests.marketing.test_pipeline import build

    provider.set_default("strategist", campaign_brief(1))
    pipeline, _ = build(
        provider,
        PRESETS["balanced"].model_copy(update={"draft_candidates": 1, "max_revisions": 0}),
    )
    result = await pipeline.run(
        replace(request_fixture, request="Write me 1 email that sells my app")
    )

    record = record_from("fixture", "balanced", result, duration_seconds=1.0)

    assert record.audience_condition == ""
    assert record.audience_segment == ""
    assert record.audience_reached == {}
    # And the record now carries the copy, which is what lets Experiment 2
    # re-read a draft somebody has already paid for.
    assert record.emails[0].email is not None
    assert record.emails[0].email.body == result.emails[0].body


def test_the_report_renders_a_partial_round():
    """One arm failing must still produce a readable table - a two-arm
    comparison is worth more than a stack trace."""
    arms = {
        "none": RunRecord(
            case=CASE, request="r", preset="balanced", audience_condition="none"
        ),
        "current": RunRecord(
            case=CASE,
            request="r",
            preset="balanced",
            audience_condition="current",
            audience_segment="Agencies",
            audience_reached={"strategist": ["current.segment"]},
            reader_personas=["Agencies. a development agency"],
        ),
    }

    rendered = render_case(CASE, arms)

    assert "NONE" in rendered and "CURRENT" in rendered
    assert "ok   none: no fixture phrase reached any role" in rendered
    assert "Validity" in rendered


def test_the_report_calls_out_an_arm_that_never_reached_the_run():
    """The failure this whole file exists to make loud."""
    arms = {
        "current": RunRecord(
            case=CASE,
            request="r",
            preset="balanced",
            audience_condition="current",
            audience_reached={role: [] for role in PROBED_ROLES},
        )
    }

    assert "FAIL current" in render_case(CASE, arms)


def test_the_artifact_store_is_untouched_by_the_experiment(db):
    """The arms write a brand, a map and a campaign. They must not leave
    compiled knowledge behind - a benchmark that seeded artifacts would make
    the next arm reuse them and skip its own compile."""
    _, _ = _gateway(db, AudienceCondition.RESEARCHED)

    assert ArtifactStore(db).load(ArtifactScope(brand_id=None, campaign_id=None)) is None
