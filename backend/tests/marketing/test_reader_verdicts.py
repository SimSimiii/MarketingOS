"""The cold reader's report survives the run.

The system's most expensive judgment used to reach the user as a single digit.
A real run scored 4/10 and persisted exactly `{"pull": 4}` - while the same
model call had already reported what the reader thought the email was selling,
where they stopped reading, what was really stopping them clicking, and the one
thing the email would have had to say for them to click.

`reader.md` calls that last field the most valuable line in the report. It was
generated, paid for, and discarded at the end of the craft loop, so the user
was handed a number with no reason attached to it.
"""

import pytest

from app.marketing.policy import PRESETS, ExecutionPolicy
from app.marketing.report import ReaderVerdict
from app.marketing.request import CampaignRequest
from tests.marketing.conftest import RoleScriptedProvider, blind_read, campaign_brief
from tests.marketing.test_pipeline import build, refine_only


@pytest.mark.asyncio
async def test_the_receipt_carries_what_the_reader_actually_said(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
) -> None:
    provider.set_default("strategist", campaign_brief(1))
    provider.push(
        "blind_reader",
        blind_read(
            pull=8,
            what_it_sells="some kind of AI thing - I could not tell what it does",
            biggest_doubt="I have never heard of them and nobody vouches for them",
            stopped_at="orqAgent skips the build.",
            to_click_it_would_have_to="told me which companies like mine already use it",
            fixes=["cut the competitor line - it reads like a threat from a stranger"],
        ),
    )

    pipeline, _ = build(provider, refine_only())
    result = await pipeline.run(request_fixture)

    line = result.report.emails[0]
    assert len(line.reader_verdicts) == 1
    verdict = line.reader_verdicts[0]
    assert verdict.what_it_sells.startswith("some kind of AI thing")
    assert verdict.biggest_doubt
    assert verdict.stopped_at == "orqAgent skips the build."
    assert verdict.fixes
    # The frequencies, not only the derived score - "3 in 100" means something
    # to somebody who has mailed a list and "5/10" does not.
    assert verdict.opens_in_100 == 30
    assert verdict.clicks_in_100 is not None

    # And the one line that says what to write instead, surfaced on its own.
    assert line.what_would_have_worked == [
        "told me which companies like mine already use it"
    ]


@pytest.mark.asyncio
async def test_every_panel_member_is_kept_not_only_the_median(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
) -> None:
    """Copy one reader loved and another could not parse is not finished, and
    a single stored verdict hides exactly that."""
    provider.set_default("strategist", campaign_brief(1))
    provider.set_default("blind_reader", lambda call: blind_read(pull=8 if call % 2 else 4))

    pipeline, _ = build(
        provider,
        ExecutionPolicy(
            **{
                **refine_only().model_dump(),
                "reader_panel": True,
                "max_revisions": 0,
            }
        ),
    )
    result = await pipeline.run(request_fixture)

    verdicts = result.report.emails[0].reader_verdicts
    assert len(verdicts) == 3
    assert len({verdict.persona for verdict in verdicts}) == 3, (
        "each panel member is a different disposition and must be identifiable"
    )


@pytest.mark.asyncio
async def test_a_reader_that_never_came_back_leaves_no_verdict(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
) -> None:
    """A missing read is not a verdict of zero. Storing one would be a claim
    about the copy that nobody made."""
    provider.set_default("strategist", campaign_brief(1))
    provider.set_default("blind_reader", "this is not json")

    pipeline, _ = build(provider, refine_only())
    result = await pipeline.run(request_fixture)

    line = result.report.emails[0]
    assert line.read_reported is False
    assert line.reader_verdicts == []
    assert line.what_would_have_worked == []


#: A draft whose only defect is the one frame this whole check exists for.
#: Everything else about it is correct: the right length, the right shape, and
#: it spends the fact the fixture brief assigns - which is the point. Every
#: other check in the system passes this email.
_CLICHE_DRAFT = (
    "ROLE: hook\n"
    "SUBJECT: Your competitor is already shipping\n"
    "PREVIEW: three months is three months of ground lost\n"
    "GREETING: Hi there,\n"
    "CTA: Point it at a branch\n"
    "SIGNOFF: - the Notewright team\n"
    "PS:\n"
    "BODY:\n"
    "You wrote the same release note three times last month.\n\n"
    "Every one of them started as a changelog nobody read, and ended as a paragraph\n"
    "you rewrote twice before shipping it. The work was done on Tuesday, and\n"
    "describing it is the part nobody scheduled time for.\n\n"
    "Notewright turns commits you already pushed into that paragraph, in nine seconds.\n"
    "You edit it or you send it, and either way the afternoon is yours again.\n\n"
    "Most people ask whether it sounds like them. It reads your older notes first,\n"
    "so it does, and you can tell in one read whether that is true.\n"
)


@pytest.mark.asyncio
async def test_an_interchangeable_opening_is_sent_back_to_the_writer(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
) -> None:
    """The whole point of the check: a draft every other gate passes is
    stopped, and the writer is told which frame to replace."""
    provider.set_default("strategist", campaign_brief(1))
    provider.set_default("email_writer", _CLICHE_DRAFT)

    pipeline, _ = build(provider, refine_only())
    result = await pipeline.run(request_fixture)

    blocked = result.outcomes[0].versions[0].gates.blocking
    assert [issue.gate for issue in blocked] == ["sameness"]
    assert "own week" in blocked[0].detail, "the writer is told what to write instead"


@pytest.mark.asyncio
async def test_the_receipt_names_copy_a_competitor_could_have_sent(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
) -> None:
    """When the writer will not fix it and the run ships anyway, the finding
    reaches the receipt - it is the cheapest thing a user can fix by hand."""
    provider.set_default("strategist", campaign_brief(1))
    provider.set_default("email_writer", _CLICHE_DRAFT)

    pipeline, _ = build(provider, refine_only())
    result = await pipeline.run(request_fixture)

    line = result.report.emails[0]
    assert not line.clean, "an email shipped over a blocking check is not clean"
    assert line.sameness, "an interchangeable subject line must reach the receipt"
    assert any("competitor" in issue for issue in line.sameness)


def test_a_verdict_is_built_only_from_readers_who_reported() -> None:
    from app.marketing.reader import BlindRead, PanelRead

    panel = PanelRead(
        reads=[
            BlindRead(persona="a", clicks_in_100=6, what_it_sells="a thing"),
            BlindRead(persona="b", reported=False),
        ]
    )
    verdicts = ReaderVerdict.from_panel(panel)

    assert [verdict.persona for verdict in verdicts] == ["a"]
    assert verdicts[0].pull == 7


@pytest.mark.asyncio
async def test_a_starved_run_says_so_instead_of_blaming_the_copy(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
) -> None:
    """A 4/10 on the cheapest preset is a verdict on the run, not on the
    product - and the user has no way to know that unless it is said."""
    provider.set_default("strategist", campaign_brief(1))
    provider.set_default("blind_reader", blind_read(pull=4, would_act=False))

    pipeline, _ = build(provider, PRESETS["fast"])
    result = await pipeline.run(request_fixture)

    note = " ".join(result.report.notes)
    assert "under the floor" in note
    assert "one draft" in note
    assert "preset that buys them" in note


@pytest.mark.asyncio
async def test_a_full_run_that_scores_badly_blames_nothing(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
) -> None:
    """The note must never become an excuse. A run that bought every mechanism
    and still came in low has learned something real about the material."""
    provider.set_default("strategist", campaign_brief(1))
    provider.set_default("blind_reader", blind_read(pull=4, would_act=False))

    pipeline, _ = build(provider, PRESETS["maximum"])
    result = await pipeline.run(request_fixture)

    assert not any("preset" in note for note in result.report.notes)
