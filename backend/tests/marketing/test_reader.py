"""The cold read: the instrument every quality number in the system comes off.

These deserve their own file because a miscalibrated grader does not fail like
a bug. It fails as four rewrites that each score the same, a campaign reported
as degraded, and a receipt telling the user their copy did not land - none of
which point at the grader. Two failures of that kind are pinned here: a scale
whose anchors contradicted the threshold read off it, and a panel containing a
reader whose score no rewrite could move.
"""

from app.core.config import PROMPTS_DIR
from app.knowledge.artifacts import AudienceModel, Segment
from app.marketing.reader import (
    PULL_THRESHOLD,
    BlindRead,
    PanelRead,
    personas_for,
)
from app.runtime.prompt_engine import PromptEngine


def read(pull: int, would_act: bool | None = None, **overrides) -> BlindRead:
    """One reader's report, self-consistent by default: `would_act` follows the
    rubric unless a test is specifically about the two disagreeing."""
    return BlindRead(
        opened=True,
        pull=pull,
        would_act=pull >= PULL_THRESHOLD if would_act is None else would_act,
        **overrides,
    )


def no_verdict() -> BlindRead:
    return BlindRead(reported=False, persona="one who never came back")


SEGMENT = Segment(
    name="a developer who ships weekly",
    situation="ships every Friday and writes the note by hand",
)


# ------------------------------------------------------- the scale and the floor


def test_the_rubric_and_the_threshold_agree_on_what_seven_means():
    """The floor is only meaningful if the reader's scale puts the same event
    at the same number.

    It did not: the ladder anchored 7 at "you would click if the week were
    calmer" while `landed` also required "would click today", so a reader
    answering both honestly could never satisfy them at once and the real
    floor was an 8 nobody had written down.
    """
    prompt = PromptEngine(PROMPTS_DIR).render(
        "reader", {"reader_profile": SEGMENT.name, "email": "Subject: anything"}
    )
    assert f"{PULL_THRESHOLD} or higher means yes" in prompt


def test_a_reader_who_scores_the_floor_and_would_click_has_landed():
    assert read(PULL_THRESHOLD).landed is True


def test_a_reader_below_the_floor_has_not_landed_however_keen_they_sound():
    assert read(PULL_THRESHOLD - 1, would_act=True).landed is False


def test_a_reader_who_never_opened_it_has_not_landed():
    assert BlindRead(opened=False, pull=9, would_act=True).landed is False


# -------------------------------------------------------------- the panel's number


def test_the_panel_reports_its_middle_reader_not_its_average():
    """A mean lets one reader who scores everything low set the number that
    decides which rewrite is kept."""
    panel = PanelRead(reads=[read(9), read(7), read(2)])
    assert panel.pull == 7, "the median; the mean here is 6 and nobody said 6"


def test_one_reader_is_their_own_median():
    assert PanelRead(reads=[read(8)]).pull == 8


def test_a_reader_who_never_came_back_is_left_out_of_the_number():
    panel = PanelRead(reads=[read(8), no_verdict(), read(8)])
    assert panel.pull == 8
    assert panel.has_verdict is True


def test_a_panel_nobody_reported_on_has_no_verdict_rather_than_a_zero():
    panel = PanelRead(reads=[no_verdict(), no_verdict()])
    assert panel.has_verdict is False
    assert panel.pull == 0.0
    assert panel.landed is False


def test_the_hardest_verdict_is_one_that_was_actually_given():
    """A reader who never reported carries pull 0 and would otherwise be
    mistaken for the harshest one in the room."""
    panel = PanelRead(reads=[read(8), no_verdict(), read(4)])
    assert panel.worst.pull == 4


# --------------------------------------------------------------- when it landed


def test_a_draft_lands_when_most_of_the_panel_would_click():
    assert PanelRead(reads=[read(8), read(8), read(3)]).landed is True


def test_a_draft_does_not_land_when_most_of_the_panel_would_not():
    assert PanelRead(reads=[read(8), read(3), read(3)]).landed is False


def test_unanimity_is_not_required_because_nothing_could_ever_reach_it():
    """The old rule gave every reader a veto. Paired with a panel built to
    contain a hard one, that made the floor unreachable by construction - and
    "the loop ran out of rewrites" reached the user as if it were a score."""
    panel = PanelRead(reads=[read(9), read(8), read(6)])
    assert panel.landed is True
    assert panel.pull >= PULL_THRESHOLD


def test_readers_who_never_came_back_do_not_count_against_the_majority():
    assert PanelRead(reads=[read(8), no_verdict(), read(3)]).landed is False
    assert PanelRead(reads=[read(8), no_verdict()]).landed is True


# ------------------------------------------------------------ how it is reported


def test_one_reader_is_reported_as_a_person_not_a_tally():
    assert PanelRead(reads=[read(8)]).verdict_line() == "they would click today"
    assert PanelRead(reads=[read(3)]).verdict_line() == "they would not click"


def test_a_panel_is_reported_as_how_many_of_them_would_click():
    panel = PanelRead(reads=[read(8), read(8), read(3)])
    assert panel.verdict_line() == "2 of 3 would click today"


def test_a_panel_nobody_read_says_so_rather_than_reporting_a_refusal():
    assert PanelRead(reads=[no_verdict()]).verdict_line() == "nobody could read it"


# ----------------------------------------------------------------- who reads it


def test_without_a_panel_the_draft_is_read_by_the_chosen_segment():
    personas = personas_for(AudienceModel(segments=[SEGMENT]), SEGMENT, panel=False)
    assert personas == [f"{SEGMENT.name}. {SEGMENT.situation}"]


def test_a_panel_is_the_same_person_in_three_moods():
    personas = personas_for(AudienceModel(segments=[SEGMENT]), SEGMENT, panel=True)
    assert len(personas) == 3
    assert all(SEGMENT.name in persona for persona in personas)


def test_no_reader_is_defined_by_rejecting_the_medium():
    """A reader skeptical of cold email is answering a question no rewrite can
    move. They reject the envelope, so their score is a constant that drags
    every draft in the run down and, under the old unanimity rule, vetoed
    every one of them. Dispositions have to be about the claim."""
    personas = personas_for(AudienceModel(segments=[SEGMENT]), SEGMENT, panel=True)
    assert not any("cold email" in persona.lower() for persona in personas)


def test_a_campaign_with_no_audience_at_all_still_gets_a_reader():
    personas = personas_for(AudienceModel(), None, panel=False)
    assert len(personas) == 1 and personas[0]
