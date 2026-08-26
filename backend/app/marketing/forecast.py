"""What a run will cost, worked out before it is bought.

This is only possible because nothing in the pipeline spends a model call
deciding what happens next. The order of work is fixed by data dependencies,
the loop's widths are numbers on `ExecutionPolicy`, and how many emails there
are was parsed out of the user's own sentence before anything ran - so the
shape of a run is arithmetic, and arithmetic has an answer.

That is worth having because quota is felt directly here: every call is billed
against a personal subscription, and the evaluation CLIs already print an
estimate before they spend anything. The application did not. A user picked
between three presets described as "cheaper models" and "most thorough
review" - two adjectives with no number attached - and found out what the
difference was on the receipt.

**A range, never a figure.** The floor is the run where every email lands
first time: the bake-off picks a winner, the critic ships it, nothing is
rewritten. The ceiling is the run that buys every rewrite it is allowed and
reworks every email the sequence pass can touch. Real runs sit between, and
quoting the middle as though it were the answer would be the same kind of lie
as a pull score nobody gave.

**Checked against a real run, not against itself.** `tests/marketing`
executes the pipeline with a scripted provider and compares the calls it
actually made against this arithmetic. An estimator validated only by its own
unit tests drifts the first time the loop changes shape, silently, and an
estimate nobody can trust is worse than no estimate.
"""

from dataclasses import dataclass

from app.marketing.contract import DeliverableContract
from app.marketing.policy import ExecutionPolicy

#: Calls the knowledge compile makes besides reading for evidence: the
#: profile, the voice and the audience passes. One each, always.
_COMPILE_FIXED_CALLS = 3

#: How much material one evidence reading covers. Mirrors
#: `app.knowledge.compiler._EVIDENCE_BATCH_CHARS`; imported rather than
#: repeated would be a circular import, so it is asserted equal in the tests.
_EVIDENCE_BATCH_CHARS = 14_000


@dataclass(frozen=True)
class Forecast:
    """How many model calls one run will make, at best and at worst."""

    low: int
    high: int
    #: The part of the total the knowledge compile accounts for. Called out
    #: separately because it is the one part a second campaign for the same
    #: business does not pay again, and that is the single largest saving
    #: available to a user who does not know it exists.
    compile_low: int = 0
    compile_high: int = 0

    def __add__(self, other: "Forecast") -> "Forecast":
        return Forecast(
            low=self.low + other.low,
            high=self.high + other.high,
            compile_low=self.compile_low + other.compile_low,
            compile_high=self.compile_high + other.compile_high,
        )

    def render(self) -> str:
        if self.low == self.high:
            return f"{self.low} model call(s)"
        return f"{self.low}-{self.high} model calls"


def _readers(policy: ExecutionPolicy) -> int:
    """Cold readers per draft. Three is what `personas_for` builds for a
    panel: the segment, the segment already served by something else, and the
    segment that has been promised this before."""
    return 3 if policy.reader_panel else 1


def _ballot(policy: ExecutionPolicy) -> int:
    """Votes in one duel. `tournament._ballot` rounds up to an even number so
    both label orders divide exactly, and never runs fewer than two."""
    if not policy.tournament:
        return 0
    wanted = max(2, _readers(policy))
    return wanted + wanted % 2


def compile_forecast(policy: ExecutionPolicy, material_chars: int, reused: bool) -> Forecast:
    """What reading this business costs, and nothing if it has been read.

    `material_chars` is how much text the user has attached. A campaign whose
    website has not been crawled yet cannot know - the crawl happens inside
    the run - so a caller with only a URL passes what it has and the estimate
    widens with the crawl budget.
    """
    if reused or material_chars <= 0:
        return Forecast(low=0, high=0)
    readings = max(1, -(-material_chars // _EVIDENCE_BATCH_CHARS))
    calls = _COMPILE_FIXED_CALLS + readings
    return Forecast(low=calls, high=calls, compile_low=calls, compile_high=calls)


def email_forecast(policy: ExecutionPolicy) -> Forecast:
    """One email, from the first candidate to the polished subject line.

    Two things the floor deliberately does not assume, because both were
    measured happening and neither is under the policy's control:

    - **that every candidate gets read.** Two drafts that come back with the
      same subject or the same opening move are one alternative bought twice,
      and `_distinct` drops the repeat before anybody pays to read it.
    - **that the run-off happens.** The two best candidates only go in front
      of a reader together when the free checks could not already separate
      them.

    So the floor is one candidate read and no duel, and the ceiling is every
    candidate read, every duel run and every rewrite bought.
    """
    readers = _readers(policy)
    ballot = _ballot(policy)
    candidates = max(1, min(policy.draft_candidates, 4))

    # Written either way: the candidates are drafted concurrently and the
    # duplicates are found afterwards.
    common = candidates
    # The critic is bought once even on a run with no rewrites at all - see
    # `CraftLoop._critique_for_the_record` - and the subject is polished once,
    # last, on the draft that won.
    if policy.critic_enabled:
        common += 1
    if policy.subject_variants:
        common += 1 + readers

    low = common + readers
    high = common + candidates * readers + (ballot if candidates > 1 else 0)

    # Every rewrite the policy allows: a writer turn, a cold read, a duel
    # against the version it would replace, and a critique to drive the next
    # one.
    high += policy.max_revisions * (1 + readers + ballot + (1 if policy.critic_enabled else 0))
    return Forecast(low=low, high=high)


def rework_forecast(policy: ExecutionPolicy, emails: int) -> Forecast:
    """The whole-sequence read, and the reworks it can order.

    Nothing when there is one email: a sequence of one is not a sequence, and
    the pipeline skips the pass entirely.
    """
    if emails < 2 or not policy.sequence_pass:
        return Forecast(low=0, high=0)
    readers = _readers(policy)
    per_rework = 1 + readers + _ballot(policy)
    reworks = min(policy.max_sequence_reworks, emails)
    return Forecast(low=1, high=1 + reworks * per_rework)


def forecast(
    policy: ExecutionPolicy,
    contract: DeliverableContract,
    material_chars: int = 0,
    knowledge_reused: bool = False,
) -> Forecast:
    """Every model call one run of this campaign can make.

    The strategist's own correction turn is in the ceiling and not the floor:
    it is bought only when the brief comes back with the wrong number of
    emails, which is a failure rather than a step.
    """
    emails = max(1, contract.count)
    total = compile_forecast(policy, material_chars, knowledge_reused)
    per_email = email_forecast(policy)
    total += Forecast(low=per_email.low * emails, high=per_email.high * emails)
    total += rework_forecast(policy, emails)
    # The strategist: one call, plus the correction turn at worst.
    return total + Forecast(low=1, high=2)
