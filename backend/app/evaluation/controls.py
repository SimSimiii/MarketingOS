"""Extra control emails, written for the bench and honest about it.

The judge bench used to run on the golden set's controls alone, and the golden
set has two of them. Two is not a sample. With one item you cannot separate
"this judge is blind to a missing proof paragraph" from "that particular email
does not miss its proof paragraph much" - the judge and the email are the same
variable, and every rate the bench prints is a statement about both at once.
The first round said `strip_the_proof` came back 2-2, and nothing in the file
can say which of those two sentences it meant.

More items is the only fix. That runs straight into the warning `golden.py`
already carries: a bench whose "good" email was written for the bench proves
the author's taste. So this file is deliberately *not* an extension of the
golden set, and the distinction is load-bearing in two directions.

**Why these are admissible here.** A judge bench pair is not a quality
comparison. It is an email against a damaged copy of *itself*, and the label
comes from the damage, not from how good the original was. The original only
has to be coherent, sendable, and to contain the things the mutations need to
remove - a figure worth checking, a paragraph carrying proof, an ask at the
end, an opening about the reader. Whether a freelancer would have written it
better does not enter into it, because the freelancer's version is not the
other side of the pair.

**Why they are still marked.** A control written in the register a model finds
natural may be easier to defend than one a person wrote, and a bench that
drifted that way would report a reliability the instrument does not have on
real copy. So `anchor` distinguishes the two human controls from these, and
the report gives the anchors their own line. If the two rates diverge, the
controls in this file are the suspect, not the judge.

**What these must never be used for.** `head_to_head.py` measures the system
against an email a person wrote, and that is the one measurement in the
package with an outside referent. Grading the system against copy generated
the same way it was would be measuring nothing at all, at length. These carry
`anchor=False` and `head_to_head` reads the golden set, never this file.

The set spans registers rather than markets: the judge is a general instrument
and the question is whether its reliability survives leaving the cold-B2B-SaaS
voice every other fixture here is written in.
"""

from dataclasses import dataclass

from app.marketing.email_copy import Email, EmailCopyError, parse_email


@dataclass(frozen=True)
class BenchSource:
    """One original the bench mutates, and who reads it."""

    name: str
    email: Email
    persona: str
    #: True for a control a person wrote - today, the golden set's two. The
    #: report keeps their rate separate, because they are the only items whose
    #: provenance is independent of the thing being measured.
    anchor: bool = False


@dataclass(frozen=True)
class ControlDraft:
    """A control before it has been parsed, held as the text a writer emits."""

    name: str
    persona: str
    text: str
    #: What this one is in the set for. Not decoration: a set that drifts back
    #: toward one register stops testing what it was widened to test, and the
    #: only way to notice is to have written down what each item covers.
    register: str


_RENEWAL = """ROLE: reactivation
SUBJECT: Your plot is still there
PREVIEW: nothing was deleted, and nothing needs redoing
GREETING: Hi Sam,
CTA: Pick your seeds for spring
SIGNOFF: - Nadia at Allotment
PS: Your notes and photos are exactly where you left them.
BODY:
Your Allotment plan went quiet in October, which is when most of them do.

Nothing was deleted. The beds you mapped, the notes about what the slugs got
to, the photographs from July - all still where you left them.

Sowing reminders start again in three weeks. They are the part people tell us
afterwards that they missed.

"I forgot how much I relied on it until the first February with no
reminders," Beth wrote to us last spring.

Open your plot and pick this year's beds before sowing starts. Seeds that go
in the post this week arrive in time; the ones you think about in March do
not.
"""

_COMPLIANCE = """ROLE: hook
SUBJECT: The audit question nobody can answer on the day
PREVIEW: it is always the same one, and it is always the access log
GREETING: Hi there,
CTA: See what an evidence pack contains
SIGNOFF: - Rowan, Fieldmark
PS: Happy to look at your current pack and tell you what is missing.
BODY:
Your auditor will ask who had access to production last March. Most finance
teams spend two days reconstructing an answer from screenshots and Slack.

The reconstruction is the problem, not the answer. Nobody is hiding anything;
the record simply was never kept in a form an auditor accepts, so it gets
assembled under time pressure by whoever is free.

Fieldmark keeps that record as it happens, in the format the auditor asks
for. When the question comes, the answer is already written.

"Our last review took a morning instead of a fortnight," said Ines Okafor,
who runs finance operations at Verel.

If you have an audit this year, it is worth seeing what the pack looks like
before somebody on your team starts screenshotting.
"""

_WORKSHOP = """ROLE: invitation
SUBJECT: Two hours on the thing your dough keeps doing
PREVIEW: Thursday evening, eight benches, flour included
GREETING: Hi there,
CTA: Take one of the eight benches
SIGNOFF: - Tomas, Mill Lane Bakery
PS: Bring a container - you go home with the dough you made.
BODY:
If your loaves come out dense and you have stopped knowing which change to
try next, this evening is for that.

Thursday, six to eight, at the bench in the back of the shop. Eight places,
because past that I cannot get round everybody while the dough is still
working.

We do one bulk ferment together and I stop you at the points where it usually
goes wrong. You will feel the difference in the dough rather than read about
it afterwards.

"I had been baking bricks for a year and it turned out to be one thing,"
Marek told me after the last one.

Take a bench and bring your hands. Flour is on me.
"""

_SHELTER = """ROLE: appeal
SUBJECT: The kennel at the end is empty tonight
PREVIEW: it has not been empty since March, and we would like to keep it that way
GREETING: Hi there,
CTA: Cover a week of kennel costs
SIGNOFF: - Priya, Longmoor Rescue
PS: We publish what every pound goes to, monthly, without being asked.
BODY:
The last kennel at the end of our corridor is empty tonight. Bramble went
home on Saturday, after seven months with us.

It is the first time since March that we have had a space, and the reason it
matters is that an empty kennel is the only thing standing between the next
call and a no.

Keeping one kennel running costs forty pounds a week. That is food, heat,
and the vet check every dog gets in the first day.

"They rang me back within the hour and took him the same afternoon," said
Derek Ainsley, who found a collie on the bypass in January.

Cover a week and the space stays open for whoever the next call is about.
"""

_INFRA = """ROLE: hook
SUBJECT: Your p99 is a queue you cannot see
PREVIEW: the wait happens before your handler is ever called
GREETING: Hi there,
CTA: Run the trace on one service
SIGNOFF: - the Tailwater team
PS: Read-only agent, no redeploy, uninstall is one command.
BODY:
Your traces start when the handler runs. The slow requests are already late
by then.

What is missing is the time between the connection arriving and your code
being handed it. On a saturated pool that is most of the wait, and it does
not appear anywhere in the span you are looking at.

Tailwater instruments the accept path, so the queue shows up as its own
segment. Teams usually find it in about ten minutes and it is usually one
pool setting.

"We had been profiling the wrong half of the request for six weeks," said
Marta Klein, who runs platform at Corrin.

Point it at one service and look at where the time actually goes.
"""

_TRADE = """ROLE: hook
SUBJECT: Quoting is costing you the jobs you want
PREVIEW: the ones you lose go to whoever answered first
GREETING: Hi there,
CTA: Send one quote from the van
SIGNOFF: - Dan at Quotebook
PS: Works on the phone you already have, no new hardware.
BODY:
You price a job on Tuesday and send the quote on Sunday night, because that
is when you are finally sitting down.

By Sunday the customer has had two quotes. The job did not go to the
better trade, it went to whoever answered while they still cared about it.

Quotebook lets you build the quote standing in the kitchen you just measured,
off your phone, and send it before you get back in the van. Prices come from
your own rates, so nothing needs typing twice.

"I stopped losing work to lads who are no better than me, they were just
quicker," Ryan Doyle told us in March.

Do the next one from the van and see whether it lands differently.
"""


CONTROL_DRAFTS: tuple[ControlDraft, ...] = (
    ControlDraft(
        name="renewal-warm",
        persona="a lapsed hobbyist who used the product last season and stopped",
        text=_RENEWAL,
        # The ask used to be "coming back costs nothing and takes one click",
        # and the first real bench round caught it: `bury_the_ask` came back
        # 0-4 *for* the mutant on this item alone, because an ask that costs
        # nothing costs nothing to move, and ending on the testimonial instead
        # was simply the better close. The pair was not labelled by
        # construction, so the miss was the fixture's and the matrix said so -
        # `bury_the_ask` was caught on all five other items.
        register="consumer, warm, no price, the ask is dated and costs something to move",
    ),
    ControlDraft(
        name="compliance-cold",
        persona="a finance operations lead at a company facing its first audit",
        text=_COMPLIANCE,
        register="B2B services, cold, long cycle, the cost is a deadline",
    ),
    ControlDraft(
        name="workshop-local",
        persona="a home baker whose loaves keep coming out dense",
        text=_WORKSHOP,
        register="local, in person, scarcity is real rather than manufactured",
    ),
    ControlDraft(
        name="shelter-appeal",
        persona="somebody who has donated to an animal charity before",
        text=_SHELTER,
        register="nonprofit, no product, the ask is money and the proof is a story",
    ),
    ControlDraft(
        name="infra-terse",
        persona="a platform engineer chasing tail latency",
        text=_INFRA,
        register="technical, terse, sceptical reader, mechanism carries the claim",
    ),
    ControlDraft(
        name="trade-plain",
        persona="a self-employed tradesperson quoting jobs in the evenings",
        text=_TRADE,
        register="plain-spoken, non-office reader, no jargon at all",
    ),
)


def bench_only_sources() -> list[BenchSource]:
    """The controls in this file, parsed.

    A draft that stops being sendable is skipped rather than raised, for the
    same reason the golden controls are: the bench shrinking is recoverable,
    and a bench that cannot start tells you nothing about the judge. The
    accompanying test fails loudly on exactly this, so a skip here is never
    how anybody finds out.
    """
    sources: list[BenchSource] = []
    for draft in CONTROL_DRAFTS:
        try:
            email = parse_email(draft.text, position=1)
        except EmailCopyError:
            continue
        sources.append(
            BenchSource(name=draft.name, email=email, persona=draft.persona, anchor=False)
        )
    return sources
