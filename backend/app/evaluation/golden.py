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


GOLDEN_CASES: tuple[GoldenCase, ...] = (
    GoldenCase(
        name="rich-sequence",
        request="Write me 3 emails that get developers to try Notewright",
        product_description="Turns merged commits into a release note",
        documents=(("Home", _NOTEWRIGHT_SITE), ("Blog", _NOTEWRIGHT_BLOG)),
        target_market="engineering teams that ship weekly",
        goals="trial signups",
    ),
    GoldenCase(
        name="rich-single",
        request="Write me 1 email that gets developers to try Notewright",
        product_description="Turns merged commits into a release note",
        documents=(("Home", _NOTEWRIGHT_SITE), ("Blog", _NOTEWRIGHT_BLOG)),
        target_market="engineering teams that ship weekly",
        goals="trial signups",
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
    ),
)


def case_named(name: str) -> GoldenCase | None:
    return next((case for case in GOLDEN_CASES if case.name == name), None)
