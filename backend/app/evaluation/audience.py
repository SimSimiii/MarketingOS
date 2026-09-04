"""Hand-written audience records, so the benchmark can ask what they are worth.

**Everything in this file is a test fixture. None of it is research.** No web
search produced any of it, nothing here was verified against a page anybody
fetched, and no part of it may be presented to a user as intelligence about
their market. It exists for one purpose: to hold the audience an evaluation
run is pointed at *constant and known*, so the same golden case can be run
several times with the audience as the only thing that changed.

The question these arms exist to answer
---------------------------------------

The golden benchmark measures the copy. It has never measured whether knowing
who the copy is for changes the copy, because an evaluation campaign is created
without a `brand_id` - and `_DbKnowledgeGateway.positioning()` and `.demand()`
are brand-scoped, so both answer `None` on every benchmark round that has ever
been made. The market package has therefore never been inside a measured run at
all.

That leaves the expensive question unanswered: is the rest of the pipeline able
to *use* a good audience record? A campaign that produces the same email
whether it knows its buyer well or badly is a campaign for which better
audience research buys nothing, however good the research is.

Three arms, and what is held constant
-------------------------------------

``none``
    Nothing is mapped. The run works from the audience the knowledge compiler
    read off the company's own website - which is what every benchmark round to
    date has done.

``current``
    A demand map in exactly the shape `AudienceCartographer` produces today,
    stored through `MarketStore.save_map` and chosen through
    `Campaign.audience_segment`, so the run reaches it by the production path
    and no other. Written to be what one search-driven pass honestly returns:
    complete-looking, plausible, and reasoned from what a model already
    believes about this market rather than from anything it read.

``researched_fixture``
    The same buyer, known properly. Situation as behaviour rather than as a
    category, the thing they do about the problem today, the event that starts
    them looking, and the objection only this person holds - written the way
    they would put it. A hand-written estimate of a ceiling, not a product: it
    stands in for what an evidence-grounded research stage could ideally
    provide, and its only job is to say whether the pipeline downstream would
    make any use of one.

Two controls are deliberate and worth stating, because without them the
experiment measures something other than what it claims.

**`current` and `researched_fixture` point at the same segment, with the same
`fit`.** The variable is how well that buyer is known, not which buyer was
picked, and not what the strategist was told their odds were. A researched
stage that also picked a *better* segment would be a second effect on top of
this one, and mixing them would make the result uninterpretable in the
direction that matters. What that means this experiment cannot tell you is
printed in the benchmark's own output.

**No fixture contains a numeral the source material does not.** `evidence_gate`
licenses every figure in a draft against the ledger and the corpus, so an
audience record carrying invented numbers would make a writer that echoed them
fail a gate - and the arm with the richer persona would collect gate failures
caused by the fixture rather than by the condition. Specificity here is
behaviour and language, never arithmetic.
"""

from dataclasses import dataclass
from enum import StrEnum

from app.knowledge.artifacts import Sophistication
from app.market.demand import AudienceSegment, DemandMap, SegmentKind


class AudienceCondition(StrEnum):
    """The one thing that changes between two runs of the same golden case."""

    #: No demand map and no chosen segment. What every benchmark round before
    #: this one did, whether or not anybody meant it to.
    NONE = "none"
    #: A map of the kind the shipped `AudienceCartographer` returns.
    CURRENT = "current"
    #: The hand-written ceiling. Never production intelligence - see the module
    #: docstring.
    RESEARCHED = "researched_fixture"


#: Arms in the order a report reads them, worst-informed first.
CONDITIONS: tuple[AudienceCondition, ...] = (
    AudienceCondition.NONE,
    AudienceCondition.CURRENT,
    AudienceCondition.RESEARCHED,
)


@dataclass(frozen=True)
class AudienceArm:
    """One condition, ready to be written into a benchmark's disposable database."""

    condition: AudienceCondition
    #: What gets stored for the brand. `None` is the whole of the `none` arm.
    demand: DemandMap | None = None
    #: What the campaign row points at. Empty for `none`.
    chosen: str = ""
    #: Verbatim strings that appear in this arm's record and in no other. The
    #: benchmark greps every rendered prompt for them, which is what turns "the
    #: segment reached the writer" from a belief into a measurement - see
    #: `app.evaluation.probe`. Each is asserted to be a real substring of the
    #: record it belongs to, so a fixture cannot drift away from its markers.
    markers: tuple[tuple[str, str], ...] = ()

    @property
    def segment(self) -> AudienceSegment | None:
        if self.demand is None or not self.chosen:
            return None
        return self.demand.named(self.chosen)

    def render(self) -> str:
        """The record, as the strategist would be shown it. For `--dry-run`."""
        if self.demand is None:
            return "No demand map. The run works from the company's own idea of its buyer."
        return self.demand.render_for_strategy(self.chosen)


#: The arm that changes nothing, for any case. One object, because there is
#: nothing case-specific about having no audience intelligence.
_NO_AUDIENCE = AudienceArm(condition=AudienceCondition.NONE)


# --------------------------------------------------------------- Notewright

#: Both Notewright arms point here. Not the core segment on purpose: a campaign
#: aimed at the buyer already on the homepage produces merged artifacts nearly
#: identical to the compiled ones, and the experiment would be asking whether
#: restating the compiler changes anything.
_NOTEWRIGHT_CHOSEN = "Agencies that ship releases for several client codebases"

_NOTEWRIGHT_CURRENT = DemandMap(
    reading=(
        "Demand for release-note tooling sits with teams that ship often and have somebody "
        "downstream who needs to know what changed. Agencies are an efficient way in, "
        "because one relationship covers several codebases."
    ),
    searched=[
        "release notes tool for agencies",
        "who writes release notes",
        "changelog automation developer teams",
    ],
    segments=[
        AudienceSegment(
            name=_NOTEWRIGHT_CHOSEN,
            kind=SegmentKind.CHANNEL,
            who=(
                "a development agency that maintains software for several clients and has to "
                "keep each of them informed about what changed"
            ),
            why_them=(
                "they write release notes repeatedly for different audiences, so a tool that "
                "drafts them saves time across every client they hold"
            ),
            pains=[
                "writing release notes takes time away from billable work",
                "clients complain when communication is thin",
            ],
            objection="they may worry it will not match each client's tone",
            angle="one tool, every client's release notes",
            sophistication=Sophistication.PROBLEM_AWARE,
            fit=0.25,
            basis=(
                "agencies manage multiple codebases and are generally receptive to tooling "
                "that saves time; developer tools see good adoption in this segment"
            ),
            population="unknown",
            signals=["has a services page", "lists several clients"],
            where=["agency directories", "developer communities"],
        ),
        AudienceSegment(
            name="Engineering teams that ship weekly",
            kind=SegmentKind.CORE,
            who="a product engineering team that deploys on a regular cadence",
            why_them="they already write release notes and would like to write them faster",
            pains=["release notes are written at the end of a long week"],
            objection="we already have a script for this",
            angle="the note writes itself from the commits you already merged",
            sophistication=Sophistication.SOLUTION_AWARE,
            fit=0.18,
            basis=(
                "this is who the company's own website addresses, so the fit is real but the "
                "segment is crowded"
            ),
            population="unknown",
            signals=["publishes a changelog"],
            where=["developer communities"],
        ),
        AudienceSegment(
            name="Open-source maintainers",
            kind=SegmentKind.ADJACENT,
            who="a maintainer who tags releases and writes the notes for each one",
            why_them="release notes are the main way their users learn what changed",
            pains=["notes are written last and often skipped"],
            objection="budget",
            angle="the tag is done, the note is not",
            sophistication=Sophistication.PROBLEM_AWARE,
            fit=0.12,
            basis="maintainers publish notes constantly and rarely have budget",
            population="unknown",
            signals=["tags releases on a public repository"],
            where=["package registries"],
        ),
    ],
)

_NOTEWRIGHT_RESEARCHED = DemandMap(
    reading=(
        "The people who feel this most are not the teams who publish a changelog because "
        "they like to - they are the ones for whom the write-up is owed to somebody else and "
        "is the only part of the work nobody pays for. Agency retainers are the purest case: "
        "the deploy is billable, the summary that goes with it is not, and it is still "
        "contractually due."
    ),
    searched=["(fixture - nothing was searched)"],
    segments=[
        AudienceSegment(
            name=_NOTEWRIGHT_CHOSEN,
            kind=SegmentKind.CHANNEL,
            who=(
                "runs a small Rails shop on maintenance retainers. On release day she opens a "
                "separate doc per client and rewrites the same deploy summary once in each "
                "client's voice - one of them reads it in a board pack, another forwards it "
                "straight to their own support desk, and none of them want the same level of "
                "detail"
            ),
            why_them=(
                "for two of her retainers the note is a named deliverable in the contract, so "
                "it is the one piece of writing she cannot skip and the one nobody has "
                "budgeted an hour for - and drafting it from the merged commits is the only "
                "part of the retainer that is identical work for every client she has"
            ),
            trigger=(
                "a client asked her in a review meeting why their own support desk heard "
                "about a breaking change before they did"
            ),
            pains=[
                "she bills for the deploy and eats the write-up",
                (
                    "the summary goes out days after the change is already live, which is "
                    "after the client's users have hit it"
                ),
                (
                    "the same change gets described differently to different clients and one "
                    "of those descriptions is wrong"
                ),
                "the client who forwards it to support gets a note written for a board pack",
            ],
            objection=(
                "tone is the thing she is actually selling - if it writes every client the "
                "same way she has to rewrite it anyway, and then she has done the job twice"
            ),
            angle="the deploy is billable, the write-up is not",
            sophistication=Sophistication.PROBLEM_AWARE,
            # Held identical to the `current` arm on purpose. See the module
            # docstring: the variable is how well the buyer is known, and a
            # different rate would tell the strategist it was holding a
            # different bet.
            fit=0.25,
            basis=(
                "fixture. Written to describe a buyer whose situation is behaviour rather "
                "than category, at the same rate the current arm claims, so the rate cannot "
                "be what moved the run"
            ),
            population="unknown - fixture",
            signals=[
                "a maintenance or retainer page rather than a projects page",
                "client work under a shared repository owner",
                "publishes per-client changelogs on separate domains",
            ],
            where=["(fixture - no real directory named)"],
        ),
        AudienceSegment(
            name="Engineering teams that ship weekly",
            kind=SegmentKind.CORE,
            who="a product engineering team that deploys on a regular cadence",
            why_them="they already write release notes and would like to write them faster",
            pains=["release notes are written at the end of a long week"],
            objection="we already have a script for this",
            angle="the note writes itself from the commits you already merged",
            sophistication=Sophistication.SOLUTION_AWARE,
            fit=0.18,
            basis=(
                "fixture. Carried unchanged from the current arm so the contrast the "
                "strategist is shown is the same contrast in both arms"
            ),
            population="unknown",
            signals=["publishes a changelog"],
            where=["developer communities"],
        ),
        AudienceSegment(
            name="Open-source maintainers",
            kind=SegmentKind.ADJACENT,
            who="a maintainer who tags releases and writes the notes for each one",
            why_them="release notes are the main way their users learn what changed",
            pains=["notes are written last and often skipped"],
            objection="budget",
            angle="the tag is done, the note is not",
            sophistication=Sophistication.PROBLEM_AWARE,
            fit=0.12,
            basis="fixture. Carried unchanged from the current arm",
            population="unknown",
            signals=["tags releases on a public repository"],
            where=["package registries"],
        ),
    ],
)


# ------------------------------------------------------------------ Portway

_PORTWAY_CHOSEN = "Operations leads who inherited somebody else's shared drive"

_PORTWAY_CURRENT = DemandMap(
    reading=(
        "Search across scattered files is bought by small companies whose storage has grown "
        "faster than anybody's ability to organise it. Operations people feel it first, "
        "because they are the ones asked where things are."
    ),
    searched=[
        "file search tool small teams",
        "shared drive search",
        "who buys enterprise search",
    ],
    segments=[
        AudienceSegment(
            name=_PORTWAY_CHOSEN,
            kind=SegmentKind.TRIGGERED,
            who=(
                "an operations lead at a small company who took over responsibility for a "
                "shared drive that somebody else set up"
            ),
            why_them=(
                "they are accountable for files they did not organise, so search is more "
                "valuable to them than tidying would be"
            ),
            trigger="they changed role, or the person who owned the drive left",
            pains=[
                "people ask them where things are",
                "the folder structure does not match how anyone works",
            ],
            objection="they may think it needs the drive tidied up first",
            angle="you do not have to tidy it to find things in it",
            sophistication=Sophistication.PROBLEM_AWARE,
            fit=0.30,
            basis=(
                "operations roles are commonly the buyer for tools of this kind and the "
                "problem is widely complained about"
            ),
            population="unknown",
            signals=["has an operations or office manager role"],
            where=["operations communities", "small business forums"],
        ),
        AudienceSegment(
            name="Teams with files spread across several tools",
            kind=SegmentKind.CORE,
            who="a team keeping documents in more than one storage product",
            why_them="one search box across all of them",
            pains=["nobody remembers which tool a file is in"],
            objection="another subscription",
            angle="one search box for the tools you already pay for",
            sophistication=Sophistication.SOLUTION_AWARE,
            fit=0.20,
            basis="this is the audience the website already addresses",
            population="unknown",
            signals=["uses more than one storage product"],
            where=["software review sites"],
        ),
    ],
)

_PORTWAY_RESEARCHED = DemandMap(
    reading=(
        "The buyer is not the person who wants the drive tidy - it is the person who has "
        "become the search index. They inherited a structure they did not design, they are "
        "interrupted for it all day, and every attempt to fix it properly has stalled because "
        "reorganising live files is a project nobody can schedule."
    ),
    searched=["(fixture - nothing was searched)"],
    segments=[
        AudienceSegment(
            name=_PORTWAY_CHOSEN,
            kind=SegmentKind.TRIGGERED,
            who=(
                "took over the shared drive when the person who built it left. She has a "
                "pinned message of folder paths she keeps re-sending, and a private habit of "
                "opening a file, copying its link and pasting it into a chat rather than "
                "explaining where it lives - because fetching it is faster than explaining"
            ),
            why_them=(
                "she is the index. Somebody asks her where something is every hour, and the "
                "answer lives in her head rather than in the folder names, so the cost of the "
                "mess is paid entirely by her attention and by nobody else's"
            ),
            trigger=(
                "the person who owned the drive left, and the handover was the drive itself "
                "with no explanation of how it had been arranged"
            ),
            pains=[
                (
                    "she is asked where things are all day and answers by fetching, not by "
                    "pointing"
                ),
                (
                    "she has started a reorganisation twice and abandoned it both times, "
                    "because moving live files breaks the links people have already sent "
                    "each other"
                ),
                "every new starter asks her the questions the last new starter asked",
                "she cannot delegate the answer, so she cannot take a week off cleanly",
            ],
            objection=(
                "she assumes a tool like this needs the drive tidied first, and tidying it is "
                "the project she has already failed to finish twice"
            ),
            angle="you are the search index, and you did not apply for the job",
            sophistication=Sophistication.PROBLEM_AWARE,
            fit=0.30,
            basis=(
                "fixture. The same rate as the current arm, so the strategist is holding the "
                "same bet and only the description of the person differs"
            ),
            population="unknown - fixture",
            signals=[
                "an operations person listed as the contact for internal systems",
                "a recent departure in an ops or office-management role",
            ],
            where=["(fixture - no real directory named)"],
        ),
        AudienceSegment(
            name="Teams with files spread across several tools",
            kind=SegmentKind.CORE,
            who="a team keeping documents in more than one storage product",
            why_them="one search box across all of them",
            pains=["nobody remembers which tool a file is in"],
            objection="another subscription",
            angle="one search box for the tools you already pay for",
            sophistication=Sophistication.SOLUTION_AWARE,
            fit=0.20,
            basis="fixture. Carried unchanged from the current arm",
            population="unknown",
            signals=["uses more than one storage product"],
            where=["software review sites"],
        ),
    ],
)


# -------------------------------------------------------------------- index

#: Markers are picked by hand rather than sliced out of the record, because a
#: probe looking for a phrase that also appears in the other arm measures
#: nothing. `tests/marketing/test_audience_benchmark.py` asserts every one of
#: these is a real substring of the arm it belongs to, and of no other.
_NOTEWRIGHT_CURRENT_MARKERS = (
    ("segment", _NOTEWRIGHT_CHOSEN),
    ("situation", "keep each of them informed about what changed"),
    ("why", "saves time across every client"),
)
_NOTEWRIGHT_RESEARCHED_MARKERS = (
    ("segment", _NOTEWRIGHT_CHOSEN),
    ("situation", "rewrites the same deploy summary"),
    ("trigger", "heard about a breaking change before they did"),
    ("pain", "bills for the deploy and eats the write-up"),
    ("objection", "she has to rewrite it anyway"),
)
_PORTWAY_CURRENT_MARKERS = (
    ("segment", _PORTWAY_CHOSEN),
    ("situation", "took over responsibility for a shared drive"),
    ("why", "search is more valuable to them than tidying"),
)
_PORTWAY_RESEARCHED_MARKERS = (
    ("segment", _PORTWAY_CHOSEN),
    ("situation", "pinned message of folder paths"),
    ("trigger", "the handover was the drive itself"),
    ("pain", "abandoned it both times"),
    ("objection", "already failed to finish twice"),
)


def _arms(
    current: DemandMap,
    researched: DemandMap,
    chosen: str,
    current_markers: tuple[tuple[str, str], ...],
    researched_markers: tuple[tuple[str, str], ...],
) -> dict[AudienceCondition, AudienceArm]:
    return {
        AudienceCondition.NONE: _NO_AUDIENCE,
        AudienceCondition.CURRENT: AudienceArm(
            condition=AudienceCondition.CURRENT,
            demand=current,
            chosen=chosen,
            markers=current_markers,
        ),
        AudienceCondition.RESEARCHED: AudienceArm(
            condition=AudienceCondition.RESEARCHED,
            demand=researched,
            chosen=chosen,
            markers=researched_markers,
        ),
    }


#: Keyed by golden case name. Only the cases with a human-written control are
#: here: the control is the one measurement with a referent outside the system,
#: and an arm comparison without it can say the copy changed but not whether it
#: got better.
ARMS: dict[str, dict[AudienceCondition, AudienceArm]] = {
    name: _arms(
        _NOTEWRIGHT_CURRENT,
        _NOTEWRIGHT_RESEARCHED,
        _NOTEWRIGHT_CHOSEN,
        _NOTEWRIGHT_CURRENT_MARKERS,
        _NOTEWRIGHT_RESEARCHED_MARKERS,
    )
    for name in ("rich-single", "rich-sequence")
}
ARMS["onboarding"] = _arms(
    _PORTWAY_CURRENT,
    _PORTWAY_RESEARCHED,
    _PORTWAY_CHOSEN,
    _PORTWAY_CURRENT_MARKERS,
    _PORTWAY_RESEARCHED_MARKERS,
)


def arm_for(case: str, condition: AudienceCondition) -> AudienceArm | None:
    """The record one arm of one case runs against.

    `none` is available for every case, fixture or not - having no audience
    intelligence is not case-specific, and a case with no hand-written arms can
    still be run as the control it always was.
    """
    if condition is AudienceCondition.NONE:
        return _NO_AUDIENCE
    return ARMS.get(case, {}).get(condition)


def cases_with_fixtures() -> tuple[str, ...]:
    """Golden cases that can run all three arms."""
    return tuple(ARMS)


#: Prefix for a phrase both informed arms carry. Exactly one does - the segment
#: name, which is shared on purpose, because the arms are the same buyer known
#: two different ways. Labelling it as neither arm's own is what stops the
#: report reading "the researched fixture reached the writer" on a run of the
#: current arm.
SHARED = "shared"


def all_markers(case: str) -> dict[str, str]:
    """Every arm's markers for one case, labelled `<condition>.<what>`.

    Handed to the probe whatever arm is running, so the `none` arm is checked
    for the *absence* of the other arms' phrases rather than merely not being
    checked. An arm that silently fell back to compiled audience data would
    otherwise look exactly like an arm that worked.

    A phrase more than one arm carries is labelled `shared.<what>` and counted
    for neither: it says an audience record reached the run, and nothing about
    which one.
    """
    owners: dict[str, list[tuple[str, str]]] = {}
    for condition, arm in ARMS.get(case, {}).items():
        for label, phrase in arm.markers:
            owners.setdefault(phrase, []).append((str(condition), label))
    found: dict[str, str] = {}
    for phrase, carriers in owners.items():
        if len({label for _, label in carriers}) == 1 and len(carriers) > 1:
            found[f"{SHARED}.{carriers[0][1]}"] = phrase
            continue
        for condition, label in carriers:
            found[f"{condition}.{label}"] = phrase
    return found


def persona_conditions(case: str) -> dict[AudienceCondition, AudienceSegment]:
    """The two segments Experiment 2 reads the same drafts as.

    The same fixtures as Experiment 1, deliberately: the second experiment is
    the first one's reader half run without paying to rewrite anything, so a
    persona that is generic here has to be the same generic persona there.
    """
    found: dict[AudienceCondition, AudienceSegment] = {}
    for condition in (AudienceCondition.CURRENT, AudienceCondition.RESEARCHED):
        arm = arm_for(case, condition)
        if arm is not None and (segment := arm.segment) is not None:
            found[condition] = segment
    return found
