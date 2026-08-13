"""What the writer is actually holding when it writes the first sentence.

The system compiles a real model of the buyer - situation, job to be done,
trigger, pains with provenance, awareness stage, objections with evidence-
linked answers - on the most expensive tier available, and then handed the
writer two sentences of it beside twenty thousand characters about the
product. A prompt's centre of gravity decides the copy's, which is why the
emails read as product descriptions.

These tests are about transport, not taste: they assert that what the
compiler learned reaches the role that writes the sentences.
"""

from dataclasses import replace

import pytest

from app.knowledge.artifacts import Fact, Grounding, Objection, Segment, Sophistication
from app.knowledge.ledger import (
    MAX_EVIDENCE_IN_PROMPT,
    Evidence,
    EvidenceKind,
    EvidenceLedger,
)
from app.marketing.policy import PRESETS
from app.marketing.request import CampaignRequest
from app.marketing.strategist import MAX_EVIDENCE_PER_EMAIL
from tests.marketing.conftest import (
    RoleScriptedProvider,
    artifacts_fixture,
    campaign_brief,
)
from tests.marketing.test_pipeline import build


def _one_email(request_fixture: CampaignRequest) -> CampaignRequest:
    return replace(request_fixture, request="Write me 1 email that sells my app")


def _rich_artifacts():
    """The fixture, plus the audience detail a real compile produces."""
    artifacts = artifacts_fixture()
    artifacts.audience.segments = [
        Segment(
            name="a developer who ships weekly and writes release notes by hand",
            situation="ships every Friday, writes the note on Friday afternoon",
            job_to_be_done="tell customers what changed without losing the afternoon",
            trigger="a customer heard about a breaking change from support first",
            sophistication=Sophistication.SOLUTION_AWARE,
            pains=[
                Fact(statement="the note goes out late or goes out thin", grounding=Grounding.GROUNDED)
            ],
        )
    ]
    artifacts.audience.objections = [
        Objection(
            objection="we already have a script for this",
            severity="strong",
            answer="the script assembles commits but cannot say why any of them matter",
            evidence_ids=["E1"],
        )
    ]
    return artifacts


def _writer_prompt(provider: RoleScriptedProvider) -> str:
    calls = provider.requests_for("email_writer")
    assert calls, "the writer never ran"
    return calls[0].system_prompt or ""


@pytest.mark.asyncio
async def test_the_writer_is_told_who_it_is_writing_to(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """Everything the compiler learned about the person, verbatim - not the
    one line the strategist wrote about them."""
    provider.set_default("strategist", campaign_brief(1))
    pipeline, _ = build(
        provider,
        PRESETS["balanced"].model_copy(update={"draft_candidates": 1, "max_revisions": 0}),
        artifacts=_rich_artifacts(),
    )
    await pipeline.run(_one_email(request_fixture))

    prompt = _writer_prompt(provider)
    assert "writes the note on Friday afternoon" in prompt
    assert "tell customers what changed without losing the afternoon" in prompt
    assert "a customer heard about a breaking change from support first" in prompt
    assert "the note goes out late or goes out thin" in prompt


@pytest.mark.asyncio
async def test_the_writer_is_told_where_it_may_start(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """Awareness decides where an email can open, and "solution_aware" is not
    an instruction anybody can act on."""
    provider.set_default("strategist", campaign_brief(1))
    pipeline, _ = build(
        provider,
        PRESETS["balanced"].model_copy(update={"draft_candidates": 1, "max_revisions": 0}),
        artifacts=_rich_artifacts(),
    )
    await pipeline.run(_one_email(request_fixture))

    assert "Explaining what the category is loses them" in _writer_prompt(provider)


@pytest.mark.asyncio
async def test_the_writer_is_told_what_answers_the_objection_not_only_what_it_is(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """A writer told to answer the no, and given only the no, writes around
    it."""
    provider.set_default("strategist", campaign_brief(1))
    pipeline, _ = build(
        provider,
        PRESETS["balanced"].model_copy(update={"draft_candidates": 1, "max_revisions": 0}),
        artifacts=_rich_artifacts(),
    )
    await pipeline.run(_one_email(request_fixture))

    assert (
        "the script assembles commits but cannot say why any of them matter"
        in _writer_prompt(provider)
    )


# ------------------------------------------------------------ evidence slice


def _big_ledger(count: int = 120) -> EvidenceLedger:
    return EvidenceLedger(
        entries=[
            Evidence(
                id=f"E{index}",
                kind=EvidenceKind.FEATURE,
                claim=f"feature number {index} exists",
                verbatim=f"Feature number {index} exists.",
            )
            for index in range(1, count + 1)
        ]
    )


def test_a_slice_always_contains_what_the_email_was_assigned():
    """The one thing that must never be dropped: an email whose own assigned
    proof is missing from its evidence list has nothing to argue from."""
    ledger = _big_ledger()

    sliced = ledger.slice_for(["E90", "E7"], objection="")

    assert [entry.id for entry in sliced.entries][:2] == ["E90", "E7"]


def test_a_slice_is_capped_however_much_is_true():
    assert len(_big_ledger().slice_for([], "").entries) == MAX_EVIDENCE_IN_PROMPT


def test_a_slice_keeps_what_answers_the_objection():
    ledger = EvidenceLedger(
        entries=[
            Evidence(id="E1", kind=EvidenceKind.FEATURE, claim="dark mode", verbatim="Dark mode."),
            Evidence(
                id="E2",
                kind=EvidenceKind.GUARANTEE,
                claim="migration takes an afternoon, not a week",
                verbatim="Most teams finish their migration in an afternoon.",
            ),
        ]
    )

    sliced = ledger.slice_for([], objection="switching would mean a migration week")

    assert sliced.entries[0].id == "E2"


def test_a_slice_prefers_proof_over_another_feature():
    """Between two facts that fit, the one a cold reader moves on wins."""
    ledger = EvidenceLedger(
        entries=[
            *_big_ledger(20).entries,
            Evidence(
                id="T1",
                kind=EvidenceKind.TESTIMONIAL,
                claim="Basecamp uses it daily",
                verbatim="We use it every day. - Basecamp",
            ),
        ]
    )

    assert "T1" in {entry.id for entry in ledger.slice_for([], "").entries}


def test_the_full_ledger_still_licenses_the_copy():
    """The saving must not narrow what the writer is *allowed* to say - the
    evidence gate reads the finished draft against everything true, for free,
    which is why slicing the prompt costs no correctness."""
    from app.knowledge.ledger import EvidenceIndex

    ledger = _big_ledger()
    index = EvidenceIndex(ledger, source_text="")

    # A fact outside any 15-entry slice is still licensed in the copy.
    assert not index.unsupported("feature number 118 exists")


@pytest.mark.asyncio
async def test_the_writer_is_not_handed_the_whole_inventory(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """The measured effect: a real business compiles ~120 facts and every
    writer call used to carry all of them."""
    artifacts = _rich_artifacts()
    artifacts.evidence = _big_ledger()
    provider.set_default("strategist", campaign_brief(1))

    pipeline, _ = build(
        provider,
        PRESETS["balanced"].model_copy(update={"draft_candidates": 1, "max_revisions": 0}),
        artifacts=artifacts,
    )
    await pipeline.run(_one_email(request_fixture))

    prompt = _writer_prompt(provider)
    listed = sum(1 for line in prompt.splitlines() if line.startswith("- [E"))
    # The slice, plus the assigned facts - which are deliberately repeated in
    # their own block, because "these are the facts you may use" and "this is
    # the fact this email is built on" are different instructions.
    assert listed <= MAX_EVIDENCE_IN_PROMPT + MAX_EVIDENCE_PER_EMAIL, (
        f"{listed} facts reached the writer"
    )
    assert "feature number 118 exists" not in prompt
