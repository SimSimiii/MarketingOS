"""The frozen set of businesses and requests the benchmark runs against.

Small on purpose. Every case here is billed on every benchmark round, so the
set has to earn its size: these are chosen to span the axes that actually
change the system's behaviour, not to cover a market.

- how much proof exists (a site with numbers and customers, vs. one paragraph)
- whether there is copy to learn a voice from
- one email vs. a sequence, since sequencing is a different failure mode
- selling to a stranger vs. writing to someone who already signed up

They are held as inline text rather than as URLs so a benchmark run is
reproducible: a live site would change under the comparison, and a fixture
whose input drifts measures nothing.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class GoldenCase:
    name: str
    request: str
    product_description: str
    #: (title, content) - what the knowledge compiler reads.
    documents: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    target_market: str = ""
    goals: str = ""
    #: An email a person wrote for this brief, from the same material, in the
    #: labelled-field format the writer emits.
    #:
    #: The reason this exists: every other number in the benchmark compares the
    #: system to an earlier version of itself, which can only ever say whether
    #: a change helped - never whether the output is any good. "Average pull
    #: went from 5.1 to 5.4" is compatible with both versions being worse than
    #: anything a person would send. A control is the only measurement in the
    #: file with an outside referent, and beating it is the actual goal, so it
    #: is the number to look at first.
    #:
    #: Held inline for the same reason the documents are: a control that drifts
    #: makes every comparison against it meaningless.
    control_email: str = ""


_NOTEWRIGHT_SITE = """# Notewright

Notewright turns the commits you already merged into a release note.

Point it at a branch and it drafts the note in about nine seconds, in the tone
of the notes you have already published. It reads your last twenty entries
first, so it writes like you and not like a changelog generator.

## Pricing

Team is $29 per month per workspace. Every account starts with 1,500 free
credits and no card.

## What teams say

"We stopped arguing about who writes the notes. It just does it, and we edit."
- Priya, engineering lead at Halcyon

"Setup took four minutes. I expected an afternoon." - Dan, staff engineer

## Numbers

Teams using Notewright publish release notes 6 days sooner on average than
they did before. 94% of drafts are sent with fewer than three edits.
"""

_NOTEWRIGHT_BLOG = """# Why we built this on a Friday

We shipped it on a Tuesday and told nobody. That is the joke, and it is also
the problem: the work is done days before anyone hears about it, because the
person who has to describe it is the person who just spent a week building it.

We are not going to tell you release notes are exciting. They are not. They
are the last thing between you and the weekend, and they get written like it.
"""

#: A business with almost nothing to say about itself - the case that decides
#: whether the system stays honest or starts inventing specifics. Everything
#: downstream should visibly narrow rather than fill the gap.
_THIN_SITE = """# Ledgerloop

Ledgerloop helps small teams keep their books tidy. Get started today.
"""

_ONBOARDING_SITE = """# Portway

Portway moves a team's files off shared drives and into one searchable place.

Connect a drive and Portway indexes it in the background. Most teams connect
their first source in under ten minutes; search works as soon as the first
folder finishes.

Free for 14 days, then $12 per person per month. No card to start.

"I connected Dropbox on a Monday and my team stopped asking me where things
were by Wednesday." - Marta, operations lead
"""


#: Written by hand, from the material above and nothing else, to be the thing
#: the system has to beat. Deliberately not a straw man and not a showpiece:
#: this is what a competent freelance copywriter sends on a Tuesday - one idea,
#: one proof, a small ask, no throat-clearing. A control that is easy to beat
#: measures nothing, and a control nobody could beat measures nothing either.
_NOTEWRIGHT_CONTROL = """ROLE: hook
SUBJECT: Nine seconds versus Friday afternoon
PREVIEW: the part of shipping that never gets scheduled
GREETING: Hi there,
CTA: Point it at your last branch
SIGNOFF: - the Notewright team
PS: 1,500 free credits to start, and no card.
BODY:
You shipped on Tuesday. You are writing about it on Friday.

That gap is not a discipline problem. The person who has to describe the work
is the person who just spent a week doing it, and by Friday they would rather
do almost anything else.

Notewright reads the commits you already merged and drafts the note in about
nine seconds. It reads your last twenty entries first, so it writes the way
you do rather than the way a changelog generator does.

Priya, an engineering lead at Halcyon, put it like this: "We stopped arguing
about who writes the notes. It just does it, and we edit."

Point it at the branch you merged this week and read what comes back.
"""

_PORTWAY_CONTROL = """ROLE: activation
SUBJECT: Your first folder is the whole setup
PREVIEW: ten minutes, and then search starts working
GREETING: Hi there,
CTA: Connect one drive
SIGNOFF: - the Portway team
PS: Nothing to configure after the first connection.
BODY:
Portway is sitting in your account with nothing to search.

That is the one step, and it is smaller than it looks: connect a single drive
and indexing runs in the background. Most teams are done in under ten minutes.

Search starts working as soon as the first folder finishes, so you are not
waiting on all of it.

Marta, an operations lead, said her team stopped asking her where things were
by the Wednesday after she connected Dropbox on the Monday.

You do not have to move anything or tidy anything first. Point it at the
messiest drive you have; that is the one the search is for.

Connect one drive and let it index while you do something else.
"""

GOLDEN_CASES: tuple[GoldenCase, ...] = (
    GoldenCase(
        name="rich-sequence",
        request="Write me 3 emails that get developers to try Notewright",
        product_description="Turns merged commits into a release note",
        documents=(("Home", _NOTEWRIGHT_SITE), ("Blog", _NOTEWRIGHT_BLOG)),
        target_market="engineering teams that ship weekly",
        goals="trial signups",
        control_email=_NOTEWRIGHT_CONTROL,
    ),
    GoldenCase(
        name="rich-single",
        request="Write me 1 email that gets developers to try Notewright",
        product_description="Turns merged commits into a release note",
        documents=(("Home", _NOTEWRIGHT_SITE), ("Blog", _NOTEWRIGHT_BLOG)),
        target_market="engineering teams that ship weekly",
        goals="trial signups",
        control_email=_NOTEWRIGHT_CONTROL,
    ),
    GoldenCase(
        name="thin-evidence",
        request="Write me 2 emails that get small businesses to sign up",
        product_description="Bookkeeping for small teams",
        documents=(("Home", _THIN_SITE),),
        target_market="small business owners",
        goals="signups",
    ),
    GoldenCase(
        name="onboarding",
        request=(
            "Write me 3 onboarding emails for people who started a Portway trial "
            "but have not connected a data source yet"
        ),
        product_description="Search across a team's files, wherever they live",
        documents=(("Home", _ONBOARDING_SITE),),
        target_market="operations leads at small companies",
        goals="get the first source connected",
        control_email=_PORTWAY_CONTROL,
    ),
)


def case_named(name: str) -> GoldenCase | None:
    return next((case for case in GOLDEN_CASES if case.name == name), None)
