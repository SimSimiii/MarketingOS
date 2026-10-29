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
    ReaderAssessment,
    personas_for,
    pull_from_clicks,
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


def test_the_floor_is_a_number_the_reader_was_told_the_meaning_of():
    """The decision threshold belongs to the stated editorial rubric."""
    prompt = PromptEngine(PROMPTS_DIR).render(
        "reader", {"reader_profile": SEGMENT.name, "email": "Subject: anything"}
    )
    assert PULL_THRESHOLD == 7
    assert "7–8" in prompt
    assert "uncalibrated" in prompt
    assert "opens_in_100" not in prompt
    assert "clicks_in_100" not in prompt


def test_new_reader_contract_does_not_request_predicted_open_or_click_counts():
    properties = ReaderAssessment.model_json_schema()["properties"]
    assert "pull" in properties
    assert "opens_in_100" not in properties
    assert "clicks_in_100" not in properties
    # Historical data stays readable without making the old scale a prediction.
    assert pull_from_clicks(2) == 4
    assert pull_from_clicks(0) == 0


def test_a_reader_who_scores_the_floor_and_would_click_has_landed():
    assert read(PULL_THRESHOLD).landed is True


def test_a_reader_below_the_floor_has_not_landed_however_keen_they_sound():
    assert read(PULL_THRESHOLD - 1, would_act=True).landed is False


# ------------------------------------------------- the score is derived, not given


def test_the_score_comes_off_the_click_frequency():
    """Reported as "how many of a hundred", turned into 0-10 here. The mapping
    is in code because it has a correct answer, and asking every reader to
    apply it themselves is asking each call to re-derive the same table."""
    assert BlindRead(opens_in_100=30, clicks_in_100=0).pull == 0
    assert BlindRead(opens_in_100=30, clicks_in_100=2).pull < PULL_THRESHOLD
    assert BlindRead(opens_in_100=30, clicks_in_100=6).pull >= PULL_THRESHOLD


def test_a_reader_cannot_be_clicked_by_more_people_than_opened_it():
    """Two numbers of which only the first is about the subject line. Clamped
    rather than rejected: the rest of the report is still worth having, and a
    read thrown away costs a whole pass."""
    read_back = BlindRead(opens_in_100=4, clicks_in_100=40)

    assert read_back.clicks_in_100 == 4
    assert read_back.pull == pull_from_clicks(4)


def test_a_reader_nobody_opens_cannot_have_landed():
    """The old rule said this in an `and` clause. Now it falls out of the
    arithmetic, which is the better place for it to live."""
    assert BlindRead(opened=False, opens_in_100=0, clicks_in_100=9, would_act=True).landed is False


def test_a_hand_built_read_keeps_the_score_it_was_given():
    """Nothing in the run builds one of these - every read comes back from a
    model with both frequencies. Tests and older stored reads do, and silently
    zeroing their score would make a fixture mean the opposite of what it
    says."""
    assert BlindRead(pull=9).pull == 9


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


def test_one_reader_is_reported_as_an_uncalibrated_editorial_assessment():
    assert PanelRead(reads=[read(8)]).verdict_line() == "AI simulation assessment 8/10 (uncalibrated)"
    assert PanelRead(reads=[read(3)]).verdict_line() == "AI simulation assessment 3/10 (uncalibrated)"


def test_a_panel_reports_its_editorial_median_without_prediction():
    panel = PanelRead(reads=[read(8), read(8), read(3)])
    assert panel.verdict_line() == "AI simulation assessment 8/10 (uncalibrated)"


def test_a_panel_nobody_read_says_so_rather_than_reporting_a_refusal():
    assert PanelRead(reads=[no_verdict()]).verdict_line() == "nobody could read it"


def test_a_panel_that_estimated_a_frequency_is_reported_in_that_frequency():
    """"3 in 100" means something to somebody who has mailed a list. "5.0/10"
    does not, and it is the same measurement."""
    panel = PanelRead(
        reads=[
            BlindRead(opens_in_100=30, clicks_in_100=2),
            BlindRead(opens_in_100=25, clicks_in_100=3),
            BlindRead(opens_in_100=35, clicks_in_100=8),
        ]
    )

    assert panel.clicks_in_100 == 3
    assert "uncalibrated" in panel.verdict_line()
    assert "would click" not in panel.verdict_line()


# ----------------------------------------------------------------- who reads it


def test_without_a_panel_the_draft_is_read_by_the_chosen_segment():
    personas = personas_for(AudienceModel(segments=[SEGMENT]), SEGMENT, panel=False)
    assert len(personas) == 1
    assert SEGMENT.name in personas[0]
    assert SEGMENT.situation in personas[0]
    assert "inferred" in personas[0]


def test_a_panel_is_the_same_person_in_three_moods():
    personas = personas_for(AudienceModel(segments=[SEGMENT]), SEGMENT, panel=True)
    assert len(personas) == 3
    assert all(SEGMENT.name in persona for persona in personas)


def test_a_custom_audience_controls_every_reader_without_compiled_biography():
    custom = "Opted-in electronics hobbyists considering their first repair toolkit"
    personas = personas_for(AudienceModel(segments=[SEGMENT]), SEGMENT, True, custom)
    assert len(personas) == 3
    assert all(custom in persona for persona in personas)
    assert all(SEGMENT.name not in persona and SEGMENT.situation not in persona for persona in personas)


def test_qualified_scope_reaches_the_reader_but_does_not_override_explicit_user_audience():
    scope = "Teams choosing a form before any automation is installed"
    personas = personas_for(AudienceModel(segments=[SEGMENT]), SEGMENT, False, reader_scope=scope)
    assert scope in personas[0]
    custom = personas_for(AudienceModel(segments=[SEGMENT]), SEGMENT, False,
                          "An explicitly selected audience", reader_scope=scope)
    assert "An explicitly selected audience" in custom[0]
    assert scope not in custom[0]


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
