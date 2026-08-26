from typing import Literal

from pydantic import BaseModel, Field

from app.marketing.gates import DEFAULT_MERGE_FIELDS

PolicyPreset = Literal["fast", "balanced", "maximum"]


class ExecutionPolicy(BaseModel):
    """Execution-time knobs for one campaign run.

    Deliberately mechanism-shaped (how many rewrites, which judges run, what
    the budget is) rather than vague dials like "creativity level" - a slider
    like that only ever becomes "be more creative" injected into a prompt,
    which is the generic behavior the rest of this system exists to avoid.

    What a preset actually trades is judgment calls per email. `fast` writes
    one draft and reads it; `balanced` writes several openings, keeps the one
    a stranger responded to, and adds the critic and a rewrite; `maximum`
    widens both, and adds a panel of cold readers, because variance between
    readings is the signal a single read cannot give.
    """

    #: Rewrites per email after the first draft. Two is the point where a
    #: rewrite stops fixing the draft and starts sanding it.
    max_revisions: int = Field(default=2, ge=0, le=4)
    #: How many openings are written for each email before one is chosen. The
    #: cheapest quality in the system: a second candidate buys a different
    #: argument, where a second rewrite only buys the same argument sanded
    #: smoother. One disables the bake-off entirely.
    draft_candidates: int = Field(default=3, ge=1, le=4)
    #: The Conversion Critic. Off, the loop still catches everything
    #: deterministic and everything a cold reader feels - it loses brief drift
    #: and unspent evidence, which are the failures that look finished.
    critic_enabled: bool = True
    #: Several cold readers per draft instead of one.
    #:
    #: On by default since the reader became the instrument every other
    #: decision is read off. One reader is one sample of a stochastic judge:
    #: the median of three is what makes "this rewrite came back better" a
    #: measurement rather than a coin landing the same way twice, and a cold
    #: read is the cheapest call in the run.
    reader_panel: bool = True
    #: Put two drafts in front of the reader and ask which one they would act
    #: on, instead of comparing two absolute scores. Off, the loop falls back
    #: to comparing pull - which is the comparison that could not tell a
    #: rewrite that changed everything from one that changed nothing.
    tournament: bool = True
    #: Alternative subject lines written for the finished email and scored on
    #: the open decision alone. Zero disables it. The cheapest quality in the
    #: system after the bake-off: one writer turn and one reaction per reader,
    #: spent on the only sentence most recipients ever read.
    subject_variants: int = Field(default=4, ge=0, le=8)
    #: The whole-sequence read after every email passes individually.
    sequence_pass: bool = True
    #: Reworks driven by the sequence pass. Bounded separately: this one
    #: touches emails that already passed on their own.
    max_sequence_reworks: int = Field(default=2, ge=0, le=6)

    max_duration_seconds: int | None = Field(default=1_200, ge=30)
    #: Raised with `draft_candidates`: the budget guard degrades a run by
    #: dropping emails it never got to, so a budget set for one draft per
    #: email turns a quality change into a shorter campaign, silently.
    #:
    #: Re-baselined when the token meter was fixed. These numbers used to be
    #: compared against the uncached fraction of the input - a few dozen
    #: tokens per call - so they could never fire whatever they were set to.
    #: They are now compared against everything a run consumes, cached input
    #: included, which for a measured single-email maximum run was ~235,000.
    #: Set to roughly three times a full campaign of that shape, so the guard
    #: catches a runaway without ending a legitimately large campaign.
    max_total_tokens: int | None = Field(default=1_500_000, ge=1_000)

    #: Merge fields this campaign's email tool can fill. Everything else in
    #: braces or brackets is an unfinished placeholder - see gates.
    merge_fields: list[str] = Field(default_factory=lambda: list(DEFAULT_MERGE_FIELDS))
    #: Recompile the business's knowledge even when the material has not
    #: changed. The normal path reuses it.
    force_recompile: bool = False
    #: Stop before the strategist when the material contains nothing a stranger
    #: has any reason to believe - no named customer, no quote, no attributed
    #: outcome - and hand back the questions that would fix it.
    #:
    #: On by default because the alternative is what the system did before:
    #: plan an outcome-led campaign anyway, write it, have a cold reader
    #: disbelieve it, rewrite it, and have them disbelieve it again, since no
    #: rewrite has ever added a proof the material did not contain. That run
    #: costs real money to arrive at a conclusion `preflight.assess` reaches
    #: for nothing before the first call.
    require_proof: bool = True
    #: Pages the crawler may read when ingesting a website.
    max_crawl_pages: int = Field(default=12, ge=1, le=40)

    #: Per-role model overrides, e.g. {"*": "haiku"} for a cheap pass, or
    #: {"email_writer": "opus"} for one role - see app.ai.model_router.
    model_overrides: dict[str, str] = Field(default_factory=dict)


#: Every role whose work is judgment or craft, and therefore the only ones the
#: strongest preset should move onto the strongest model.
#:
#: `maximum` used to say `{"*": "opus"}`, and a blanket override wins over the
#: tier map outright (see ModelRouter.resolve), which quietly re-priced the
#: cheap roles as expensive ones. The cold reader asks for BALANCED because a
#: cold read is a reaction, not a deliberation - and in a measured maximum run
#: it made 21 of the 38 model calls. Running those on opus bought nothing a
#: reaction needs and was the single largest line on the bill.
#:
#: What `maximum` should widen is how much judgment is bought - more openings,
#: a full reader panel, more rewrites - not the price of a reaction.
#: The preference judge and the inbox scanner are deliberately absent, for the
#: same reason the cold reader is: a choice between two emails and a glance at
#: a subject line are reactions, and the strongest preset should widen how many
#: reactions are bought rather than what each one costs. The subject *writer*
#: is here - writing eight lines that are eight different bets is craft.
_DEEP_ROLES = (
    "strategist",
    "email_writer",
    "conversion_critic",
    "sequence_reviewer",
    "subject_writer",
)

PRESETS: dict[PolicyPreset, ExecutionPolicy] = {
    "fast": ExecutionPolicy(
        max_revisions=1,
        draft_candidates=1,
        critic_enabled=False,
        reader_panel=False,
        tournament=False,
        subject_variants=0,
        sequence_pass=False,
        max_sequence_reworks=0,
        max_duration_seconds=420,
        max_total_tokens=400_000,
        max_crawl_pages=5,
        require_proof=False,
        model_overrides={"*": "sonnet", "knowledge_compiler": "haiku"},
    ),
    # Rebalanced after a measured run in which a third of the budget bought
    # refinement that moved nothing: a critique whose edits were discarded, a
    # rewrite that came back level, and a second critique of that. The money
    # moved to the two places the same run showed were starved - how many
    # different arguments get written, and whether the instrument comparing
    # them can tell them apart.
    "balanced": ExecutionPolicy(),
    "maximum": ExecutionPolicy(
        max_revisions=3,
        draft_candidates=4,
        critic_enabled=True,
        reader_panel=True,
        tournament=True,
        subject_variants=6,
        sequence_pass=True,
        max_sequence_reworks=3,
        max_duration_seconds=2_400,
        max_total_tokens=4_000_000,
        max_crawl_pages=20,
        model_overrides={role: "opus" for role in _DEEP_ROLES},
    ),
}


def resolve_policy(preset: PolicyPreset | None, custom: dict | None = None) -> ExecutionPolicy:
    """`custom` (a partial dict of ExecutionPolicy field overrides) always
    wins field-by-field over the preset it's layered on, so "balanced but
    no critic" is one call, not a fourth preset."""
    base = PRESETS[preset or "balanced"]
    if not custom:
        return base.model_copy(deep=True)
    known = {key: value for key, value in custom.items() if key in ExecutionPolicy.model_fields}
    return base.model_copy(update=known, deep=True)
