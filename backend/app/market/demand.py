"""Who should be buying this, and where they actually are.

The third question this package exists to answer, and the only one that points
outward. `rivals` asks who else is selling to this buyer; `proof` asks who has
vouched for us. Both take the buyer as given - and the buyer *is* given, by the
knowledge compiler, which read the company's own website and wrote down who
that company says it sells to.

That is the problem. A company's own material can only ever return the audience
it already believes in. It was written by people who have been staring at their
own product for two years, and it names the customer they set out to have. The
segment that would convert best is routinely not in it: the adjacent industry
with the same underlying problem, the person one seat over who feels the pain
but was never marketed to, the reseller who would put it in front of forty
accounts, the buyer who only appears when something specific happens to them.
Nothing in a crawl of the company's homepage can surface those, because the
homepage is the artifact of not having thought of them.

So this reads the *market for the product* rather than the company's account of
it, and it does so in two passes with two very different trust models - the
same split as `rivals`, for the same reason.

**The map is general and it is judgment.** `AudienceCartographer` searches for
where this kind of product gets bought, argued about and complained about, and
returns segments: a description of a buyer, what would make them care, and a
`fit` rate. That rate is an estimate and this module is careful, everywhere,
never to let it read as a measurement. Nobody has sent these emails yet. What
makes the number worth carrying is not its precision, it is that it is written
down next to the reasoning that produced it, so a user who knows their market
can see immediately which segments the machine has misjudged.

**The list is exact and it is verified.** `ProspectFinder` takes one segment and
finds named organisations that match it - then reads each one's own site with
our crawler and keeps only what those pages actually say. Every contact detail
must appear, character for character, on a page this process fetched. That rule
is not bureaucracy. A model asked for a company's email address will produce
`contact@<company>.com` with total fluency and no knowledge whatsoever, and a
list of confidently-formatted invented addresses is worse than an empty list in
every direction that matters: the mail bounces, the domain's sending reputation
takes the damage, some fraction of the guesses land on a real stranger who
never heard of this company, and the user has no way to tell the invented rows
from the real ones. Guessing is therefore not merely discouraged in the prompt,
it is structurally impossible here - a value that is not in the fetched text is
dropped by `_verify_contacts` before anything sees it.

Only what an organisation published about itself is recorded. Business contact
details on a company's own contact page are exactly that; a private person's
details assembled from three sources are not, and this module does not go
looking for them.
"""

import asyncio
import json
import logging
import re
from collections.abc import Iterable
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

from app.ai.base import ResearchTool
from app.ai.model_router import ModelTier
from app.ingestion.documents import RawDocument
from app.ingestion.exceptions import LoaderError
from app.ingestion.loaders.site_crawler import SiteCrawler
from app.knowledge.artifacts import (
    _MIN_SEGMENT_OVERLAP,
    Fact,
    Grounding,
    KnowledgeArtifacts,
    Objection,
    Segment,
    Sophistication,
    _significant_words,
)
from app.knowledge.corpus import fold
from app.market.capabilities import ProductCapabilityProfile
from app.market.positioning import PositioningMap
from app.market.qualification import (
    AudienceDefinition,
    CompanyCapabilityRequirement,
    CompanyQualification,
    CompanySignal,
    QualificationClass,
    SignalGrounding,
    UnmappedCompanyRequirement,
    qualify_company,
)
from app.runtime.model_session import ModelSession

logger = logging.getLogger("marketingos.market")

CARTOGRAPHER_ROLE_ID = "audience_cartographer"
PROSPECTOR_ROLE_ID = "prospect_finder"
READER_ROLE_ID = "prospect_reader"

#: Pages read per prospect. Lower than a competitor's five: we are not reading
#: a positioning statement here, we are answering "is this really the kind of
#: company that segment describes, and how would somebody write to them". That
#: is the home page, the about page and the contact page.
MAX_PAGES_PER_PROSPECT = 4

#: How much of a prospect's site reaches the extraction call.
MAX_PROSPECT_CHARS = 16_000

#: Prospects read at once. Independent crawls of different hosts, so this is
#: wall-clock that costs nothing to save - and low enough to stay a polite
#: number of concurrent strangers' servers.
_READ_CONCURRENCY = 3

#: A `fit` below this is not offered as a segment to write to. Not a truth
#: threshold - a low rate can be perfectly accurate - but a campaign is a
#: choice of one audience, and a list that ranks a 5% segment beside a 40% one
#: invites the user to treat the ranking as noise.
MIN_USEFUL_FIT = 0.10

#: Places that name a channel but not a venue. A qualifier makes them useful:
#: "LinkedIn" fails, while "LinkedIn RevOps Co-op group" passes. This is
#: deliberately a small list, not an ontology of everywhere buyers gather.
_VAGUE_VENUES = frozenset(
    {
        "anywhere",
        "everywhere",
        "internet",
        "linkedin",
        "online",
        "social media",
        "the internet",
        "web",
    }
)
_VENUE_FILLER = frozenset(
    {
        "at",
        "for",
        "in",
        "internet",
        "linkedin",
        "media",
        "of",
        "on",
        "online",
        "social",
        "the",
        "web",
    }
)

#: Signals that can be true of almost anybody and therefore identify nobody.
_VAGUE_SIGNALS = frozenset(
    {
        "active online",
        "has a website",
        "interested in ai",
        "needs help",
        "uses software",
        "uses social media",
        "wants to grow",
    }
)
_OBSERVABLE_SIGNAL_RE = re.compile(
    r"\b(?:certif(?:ied|ication)|complain(?:s|ed|ing)?|directory|exhibitor|"
    r"fund(?:ed|ing)|github|hir(?:e|es|ed|ing)|issue|job post(?:s|ing)?|member|"
    r"pricing page|review|return(?:s)? page|warranty page)\b",
    re.IGNORECASE,
)

#: A situation has work happening in it (the common -ing/-ed forms) or a small
#: structural marker that locates the workflow in time or context. This avoids
#: maintaining an ontology of every job an audience could do.
_SITUATION_RE = re.compile(
    r"\b(?:after|before|first|manual(?:ly)?|across|daily|multiple|recently|"
    r"several|shared|through|weekly|without|[a-z]{4,}(?:ed|ing))\b",
    re.IGNORECASE,
)
_TRIGGER_RE = re.compile(
    r"\b(?:after|before|deadline|first|fund(?:ed|ing)|hir(?:e|es|ed|ing)|"
    r"launch(?:es|ed|ing)?|migrat(?:e|es|ed|ing)|new|recently|renewal|"
    r"replac(?:e|es|ed|ing)|requirement|switch(?:es|ed|ing)?|audit|fine|incident)\b",
    re.IGNORECASE,
)
_GENERIC_AUDIENCES = frozenset(
    {
        "business owner",
        "business owners",
        "companies that want to grow",
        "company that wants to grow",
        "developer",
        "developers",
        "marketer",
        "marketers",
        "people interested in ai",
        "person interested in ai",
    }
)


class Researchability(StrEnum):
    """How worthwhile a segment is to investigate, never how likely it is to buy."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNRESEARCHABLE = "unresearchable"


class AudienceAdmission(BaseModel):
    """A deterministic receipt for whether more research should be spent."""

    researchable: bool
    researchability: Researchability
    reasons: list[str] = Field(default_factory=list)


def _normalised(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def _useful_signal(signal: str) -> bool:
    normalised = _normalised(signal)
    if not normalised or normalised in _VAGUE_SIGNALS:
        return False
    meaningful = _significant_words(signal)
    return len(meaningful) >= 3 or bool(_OBSERVABLE_SIGNAL_RE.search(signal))


def _specific_venue(venue: str) -> bool:
    normalised = _normalised(venue)
    if not normalised or normalised in _VAGUE_VENUES:
        return False
    qualifiers = {word for word in normalised.split() if word not in _VENUE_FILLER}
    return bool(qualifiers)


def _clear_trigger(trigger: str) -> bool:
    normalised = _normalised(trigger)
    return (
        normalised not in {"", "none", "unknown", "not established"}
        and len(_significant_words(trigger)) >= 2
        and bool(_TRIGGER_RE.search(trigger))
    )


def _situation_specificity(segment: "AudienceSegment") -> int:
    description = f"{segment.name} {segment.who}".strip()
    meaningful = _significant_words(description)
    generic = _normalised(segment.name) in _GENERIC_AUDIENCES and not segment.who.strip()
    structural = bool(_SITUATION_RE.search(description)) or _clear_trigger(segment.trigger)
    if generic or len(meaningful) < 4 or not structural:
        return 0
    return 2 if segment.who.strip() and len(meaningful) >= 7 else 1


def _population_is_specific(population: str) -> bool:
    normalised = _normalised(population)
    if normalised in {"", "many", "large", "unknown", "unclear", "not established"}:
        return False
    return bool(re.search(r"\d", population)) or len(_significant_words(population)) >= 2


def _matching_words(text: str) -> set[str]:
    """The existing matcher words, with tiny inflection forgiveness for duplicates."""

    words: set[str] = set()
    for word in _significant_words(text):
        if word.endswith("ies") and len(word) > 5:
            word = f"{word[:-3]}y"
        elif word.endswith("ing") and len(word) > 6:
            word = word[:-3]
        elif word.endswith("s") and not word.endswith("ss") and len(word) > 4:
            word = word[:-1]
        words.add(word)
    return words


def _same_segment(candidate: "AudienceSegment", existing: "AudienceSegment") -> bool:
    wanted = _normalised(candidate.name)
    known = _normalised(existing.name)
    if wanted and known and (wanted == known or wanted in known or known in wanted):
        return True
    candidate_words = _matching_words(f"{candidate.name} {candidate.who}")
    existing_words = _matching_words(f"{existing.name} {existing.who}")
    overlap = len(candidate_words & existing_words)
    smaller = min(len(candidate_words), len(existing_words))
    return overlap >= _MIN_SEGMENT_OVERLAP and smaller > 0 and overlap / smaller >= 0.6


class SegmentKind(StrEnum):
    """How a segment was arrived at. The field that makes the unobvious ones
    findable, because they are the entire reason to run this at all.

    A user who is shown eight segments and recognises all eight has learned
    nothing: those are the eight already on their homepage, and the map cost
    them a search for a restatement. The kinds below are the shapes a
    non-obvious buyer usually takes, named so the cartographer is asked for
    them by name rather than left to be interesting on its own.
    """

    #: Who the company already says it sells to. Kept, because a map that
    #: omits the obvious buyer is not a map - but never the whole answer.
    CORE = "core"
    #: The same problem in a different industry, where nobody is marketing to
    #: them because the vocabulary is different.
    ADJACENT = "adjacent"
    #: Not the buyer - the person one seat over who feels the pain daily and
    #: has to convince the buyer. Different email entirely.
    INFLUENCER = "influencer"
    #: Somebody who would put this in front of their own clients: an agency, a
    #: consultant, a marketplace, an integrator. One conversation, many users.
    CHANNEL = "channel"
    #: Defined by something that just happened to them rather than by what
    #: they are - they raised, they hired, they migrated, they got fined. The
    #: highest-converting kind and the one that never appears on a homepage.
    TRIGGERED = "triggered"
    #: The buyer for a use of the product the company did not intend and may
    #: not know about.
    UNINTENDED = "unintended"


class ContactKind(StrEnum):
    EMAIL = "email"
    PHONE = "phone"
    #: A contact form. Not a mailing target, and worth recording anyway: for a
    #: great many small businesses it is the only channel that exists.
    FORM = "form"
    #: A public profile page - the company's LinkedIn, an X account.
    SOCIAL = "social"


class ProspectStatus(StrEnum):
    NEW = "new"
    KEPT = "kept"
    DISMISSED = "dismissed"


class Contact(BaseModel):
    """One way to reach an organisation, read off a page it published.

    `verified` is the only field that decides whether this is worth anything.
    See the module docstring: an unverified contact detail is a fluent
    invention, and one is indistinguishable from a real one by eye.
    """

    kind: ContactKind = ContactKind.EMAIL
    value: str = ""
    #: Whose it is, in the page's own terms: "general enquiries", "support",
    #: "press", "the address on their contact page". Never a person's name
    #: unless the page itself puts that name next to the address.
    label: str = ""
    #: The page it was read on.
    source: str = ""
    #: Whether `value` was found, character for character, in text this
    #: process fetched. Nothing else may be presented to the user as a contact.
    verified: bool = False

    def render(self) -> str:
        return f"{self.kind}: {self.value}" + (f" ({self.label})" if self.label else "")


class AudienceSegment(BaseModel):
    """One kind of buyer, described well enough to decide whether to write to
    them - and to go and find them by name afterwards."""

    name: str
    kind: SegmentKind = SegmentKind.CORE
    #: One person in a situation, not a category. "A three-person Shopify
    #: store selling refurbished laptops, answering warranty questions by
    #: hand" - not "e-commerce".
    who: str = ""
    #: Why this product matters to them specifically. The sentence that is
    #: different for every segment, and the reason the copy is different too.
    why_them: str = ""
    #: What makes someone like this start looking. Empty is honest and common
    #: for the core segment; for a `triggered` segment it is the whole entry.
    trigger: str = ""
    #: What it costs them today.
    pains: list[str] = Field(default_factory=list)
    #: The reason they would say no.
    objection: str = ""
    #: The one thing to say to them, in one line. The bridge from this map to
    #: a campaign - a segment nobody can write an opening line for is research
    #: rather than an audience.
    angle: str = ""
    #: How much they already know, which decides where an email may open.
    #: Reused from the audience model rather than re-invented, because a
    #: chosen segment becomes one - see `as_segment`.
    sophistication: Sophistication = Sophistication.PROBLEM_AWARE

    #: Roughly what share of the people matching `who` would be interested
    #: enough to reply. **An estimate, never a measurement**: nobody has sent
    #: these emails, and the field is named and rendered so it cannot be read
    #: as a result. What makes it usable is `basis` sitting next to it.
    fit: float = Field(default=0.0, ge=0.0, le=1.0)
    #: Why that number - the observable facts it was reasoned from. A rate
    #: with no basis is a number the user cannot argue with, and a number the
    #: user cannot argue with is one they will either trust too much or
    #: ignore. Both are worse than a rough figure they can correct.
    basis: str = ""
    #: How many of these exist, in whatever units the evidence supports:
    #: "roughly 12,000 UK agencies on the register", "a few hundred". Vague is
    #: fine, invented precision is not.
    population: str = ""

    #: Observable markers that identify a member of this segment from the
    #: outside - what a person would look at to say "yes, that one counts".
    #: This is the field the prospect finder is actually driven by, and the
    #: field that keeps the segment honest: a segment nobody can recognise
    #: from the outside cannot be prospected, and probably cannot be targeted
    #: by any other means either.
    signals: list[str] = Field(default_factory=list)
    #: Where they are findable in bulk: a directory, a marketplace's seller
    #: list, an association's member register, a conference's exhibitor list,
    #: a forum. Named places, not "online".
    where: list[str] = Field(default_factory=list)
    #: Machine-readable qualification requirements. Defaulted so every V1
    #: demand-map payload remains readable, but an empty definition cannot
    #: qualify a named company.
    definition: AudienceDefinition = Field(default_factory=AudienceDefinition)

    @property
    def unobvious(self) -> bool:
        """Whether this is a segment the company's own material would not have
        produced. What the user is really paying for here."""
        return self.kind is not SegmentKind.CORE

    def admission(
        self, existing: Iterable["AudienceSegment"] = ()
    ) -> AudienceAdmission:
        """Whether another research pass can learn something concrete about this buyer.

        This deliberately reads no product, campaign or evidence state. A
        segment is researchable because people matching it can be recognised
        and found, not because MarketingOS thinks they will buy.
        """
        useful_signals = [signal for signal in self.signals if _useful_signal(signal)]
        specific_venues = [venue for venue in self.where if _specific_venue(venue)]
        situation = _situation_specificity(self)
        failures: list[str] = []
        if not useful_signals:
            failures.append("No useful observable signal identifies this audience.")
        if not specific_venues:
            failures.append(
                "No specific venue or source says where this audience can be found."
            )
        if not situation:
            failures.append(
                "Audience describes a broad category rather than an observable "
                "situation or workflow."
            )
        duplicate = next((item for item in existing if _same_segment(self, item)), None)
        if duplicate is not None:
            failures.append(f"Too similar to existing segment: {duplicate.name}.")
        if failures:
            return AudienceAdmission(
                researchable=False,
                researchability=Researchability.UNRESEARCHABLE,
                reasons=failures,
            )

        score = 0
        reasons = [
            (
                f"{len(useful_signals)} useful observable signal"
                f"{'s' if len(useful_signals) != 1 else ''} and "
                f"{len(specific_venues)} specific research venue"
                f"{'s' if len(specific_venues) != 1 else ''}."
            )
        ]
        if len(useful_signals) >= 2:
            score += 1
        else:
            reasons.append("Only one useful observable signal is available.")
        if len(specific_venues) >= 2:
            score += 1
        else:
            reasons.append("Only one specific research venue is available.")
        if situation == 2:
            score += 1
            reasons.append("The audience is anchored in a concrete workflow or situation.")
        if _clear_trigger(self.trigger):
            score += 1
            reasons.append("A clear trigger narrows the evidence to look for.")
        else:
            reasons.append("No clear trigger narrows the research.")
        if _population_is_specific(self.population):
            score += 1
            reasons.append("A population basis is stated.")
        else:
            reasons.append("No population basis is stated.")

        if score >= 4:
            researchability = Researchability.HIGH
        elif score >= 2:
            researchability = Researchability.MEDIUM
        else:
            researchability = Researchability.LOW
        return AudienceAdmission(
            researchable=True,
            researchability=researchability,
            reasons=reasons,
        )

    def render(self) -> str:
        lines = [
            f"- **{self.name}** [{self.kind}] - {round(self.fit * 100)}% likely to bite",
            f"    who: {self.who or 'not described'}",
            f"    why this product matters to them: {self.why_them or 'not established'}",
        ]
        if self.trigger:
            lines.append(f"    what starts them looking: {self.trigger}")
        if self.pains:
            lines.append(f"    what it costs them today: {'; '.join(self.pains)}")
        if self.objection:
            lines.append(f"    why they would say no: {self.objection}")
        if self.angle:
            lines.append(f"    the line to open on: {self.angle}")
        if self.population:
            lines.append(f"    how many: {self.population}")
        if self.basis:
            lines.append(f"    that rate is an estimate, reasoned from: {self.basis}")
        if self.where:
            lines.append(f"    findable at: {'; '.join(self.where[:4])}")
        return "\n".join(lines)

    def as_segment(self) -> Segment:
        """This buyer, in the shape the campaign pipeline already understands.

        The whole point of returning an `AudienceModel.Segment` rather than a
        new kind of thing: a chosen segment then flows through the strategist,
        the brief, the cold reader panel and the critic with nothing else in
        the system needing to know this module exists. See
        `app.market.store.merge_audience`.

        Grounding is INFERRED for everything, and that is not a formality.
        None of this came from the company's material or from the user's
        mouth - it was reasoned from the open web, and a writer that treats it
        as something the company stated will write sentences the company
        cannot stand behind.
        """
        return Segment(
            name=self.name,
            situation=self.who,
            job_to_be_done=self.why_them,
            trigger=self.trigger,
            sophistication=self.sophistication,
            pains=[
                Fact(statement=pain, grounding=Grounding.INFERRED) for pain in self.pains
            ],
        )

    def as_objection(self) -> Objection | None:
        """The reason this buyer says no, for the audience model.

        Returned separately rather than hung off the segment because that is
        where the pipeline looks for it: the strategist assigns one objection
        per email out of `AudienceModel.objections`, and an objection recorded
        anywhere else is one no email will ever be told to answer.
        """
        if not self.objection.strip():
            return None
        return Objection(
            objection=self.objection,
            severity="strong",
            answer="",
            grounding=Grounding.INFERRED,
        )


class DemandMap(BaseModel):
    """Every buyer worth considering for one product, at one moment."""

    segments: list[AudienceSegment] = Field(default_factory=list)
    #: What the cartographer searched. Reported for the same reason the rival
    #: scout reports it: a thin map is either a thin market or a thin search,
    #: and only the queries tell the user which one they are looking at.
    searched: list[str] = Field(default_factory=list)
    #: The cartographer's own account of the market - one paragraph, in the
    #: user's terms, about where the demand actually is.
    reading: str = ""
    note: str = ""
    mapped_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def ranked(self) -> list["AudienceSegment"]:
        return sorted(self.segments, key=lambda segment: segment.fit, reverse=True)

    def admission_for(self, segment: AudienceSegment) -> AudienceAdmission:
        """Admission in map order, so only later duplicates are rejected."""
        index = next(
            (position for position, item in enumerate(self.segments) if item is segment),
            None,
        )
        if index is None:
            index = next(
                (position for position, item in enumerate(self.segments) if item == segment),
                len(self.segments),
            )
        return segment.admission(self.segments[:index])

    @property
    def researchability_ranked(self) -> list["AudienceSegment"]:
        """High, medium, low, then failed; fit only breaks ties for compatibility."""
        order = {
            Researchability.HIGH: 0,
            Researchability.MEDIUM: 1,
            Researchability.LOW: 2,
            Researchability.UNRESEARCHABLE: 3,
        }
        return sorted(
            self.segments,
            key=lambda segment: (
                order[self.admission_for(segment).researchability],
                -segment.fit,
            ),
        )

    def named(self, name: str) -> AudienceSegment | None:
        """The segment a campaign chose, matched forgivingly.

        Same contract and same forgiveness as `AudienceModel.match`: the name
        arrives from a form the user filled in from this list, so it is
        normally exact, and being strict about whitespace or case would land a
        campaign on no segment at all - which silently reverts it to the
        company's own idea of its buyer, the exact thing this module exists to
        get past.
        """
        wanted = " ".join(name.lower().split())
        if not wanted:
            return None
        for segment in self.segments:
            if " ".join(segment.name.lower().split()) == wanted:
                return segment
        return next(
            (
                segment
                for segment in self.segments
                if wanted in " ".join(segment.name.lower().split())
            ),
            None,
        )

    def summary(self) -> str:
        if not self.segments:
            return "No audience has been mapped for this brand yet."
        best = self.ranked[0]
        unobvious = sum(1 for segment in self.segments if segment.unobvious)
        return (
            f"{len(self.segments)} audience(s) mapped, {unobvious} of them nobody would "
            f"have found on your own website. Best fit: {best.name} "
            f"({round(best.fit * 100)}%)."
        )

    def render_for_strategy(self, chosen: str = "") -> str:
        """The map, for the one role that decides who the campaign is written to.

        The chosen segment is marked rather than sent alone, because the
        contrast is the information: a strategist told "write to resellers"
        knows less than one told "write to resellers, who are a 35% fit,
        rather than to the founders on the homepage, who are 12%". The second
        one knows what it is trading away.
        """
        if not self.segments:
            return (
                "Nobody has mapped this product's demand. You are working from the audience "
                "the company describes on its own website, which is the audience it set out "
                "to have rather than the one most likely to answer. Write to it, and do not "
                "assume the field beyond it is empty."
            )
        lines = [
            (
                "Every rate below is an estimate reasoned from public evidence, not a "
                "measured result - no campaign has been sent to any of these people yet. "
                "Treat them as one informed opinion about where the demand is."
            ),
            "",
        ]
        if self.reading:
            lines.extend([self.reading, ""])
        for segment in self.ranked:
            mark = " <- THIS CAMPAIGN" if chosen and segment.name == chosen else ""
            lines.append(segment.render() + mark)
        return "\n".join(lines)


class ProspectLead(BaseModel):
    """A named organisation somebody proposed. Nothing believed yet."""

    name: str
    url: str = ""
    #: The observable thing that put them on the list, which must be one of
    #: the segment's signals. "Their pricing page lists a hardware warranty
    #: tier" is a reason; "a leading player in the space" is the sentence this
    #: field exists to refuse.
    why_them: str = ""
    segment: str = ""

    @field_validator("url")
    @classmethod
    def _normalize(cls, value: str) -> str:
        url = value.strip()
        if url and not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        return url


class Prospect(BaseModel):
    """One organisation that could buy this, read from its own pages."""

    name: str
    url: str = ""
    segment: str = ""
    #: What they do, from their own site.
    what_they_do: str = ""
    why_them: str = ""
    #: The sentence on their page that supports `why_them`, quoted. Checked
    #: against the fetched text exactly as a competitor's claims are: this is
    #: what stops a list of plausible-sounding companies that match nothing.
    verbatim: str = ""
    #: Roughly how well this specific organisation fits, which is not the
    #: segment's rate - the segment says how often this kind of company bites,
    #: this says how sure we are that this company is that kind of company.
    fit: float = Field(default=0.5, ge=0.0, le=1.0)
    contacts: list[Contact] = Field(default_factory=list)
    #: Why this might be wrong. Same job as a proof candidate's caveat: it is
    #: what turns a row into a two-second decision.
    caveat: str = ""
    #: True when their site was actually read. False means everything above is
    #: a lead we could not confirm, and the UI must say so rather than show an
    #: empty card.
    verified: bool = False
    pages_read: int = 0
    #: Contact details the extractor reported that were not on their pages.
    #: Counted rather than silently dropped - a prospect whose contacts were
    #: all invented is a prospect whose *fit* deserves distrust too.
    invented_contacts: int = 0
    note: str = ""
    #: Categorical V2 qualification. None only for a legacy stored prospect
    #: that predates the qualification payload.
    qualification: CompanyQualification | None = None
    found_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def reachable(self) -> bool:
        return any(contact.verified for contact in self.contacts)

    def render(self) -> str:
        contacts = ", ".join(contact.render() for contact in self.contacts) or "no way in found"
        return f"- {self.name} ({self.url}) - {self.why_them or self.what_they_do} | {contacts}"


class _MapAnswer(BaseModel):
    """The cartographer's answer, before anything is trimmed."""

    segments: list[AudienceSegment] = Field(default_factory=list)
    searched: list[str] = Field(default_factory=list)
    reading: str = ""
    note: str = ""


class _LeadList(BaseModel):
    leads: list[ProspectLead] = Field(default_factory=list)
    searched: list[str] = Field(default_factory=list)
    note: str = ""


class _ReadProspect(BaseModel):
    """One prospect's pages, extracted. Nothing verified yet."""

    what_they_do: str = ""
    why_them: str = ""
    verbatim: str = ""
    fit: float = 0.5
    contacts: list[Contact] = Field(default_factory=list)
    caveat: str = ""
    company_signals: list[CompanySignal] = Field(default_factory=list)
    company_requirements: list[CompanyCapabilityRequirement] = Field(default_factory=list)
    unmapped_requirements: list[UnmappedCompanyRequirement] = Field(default_factory=list)


class AudienceCartographer:
    """Reads the market for a product and says who would buy it."""

    def __init__(self, session: ModelSession) -> None:
        self._session = session

    async def map(
        self,
        artifacts: KnowledgeArtifacts,
        *,
        positioning: PositioningMap | None = None,
        limit: int = 7,
    ) -> DemandMap:
        """One pass over the demand side. One search call, and nothing else.

        `positioning` is passed when a scan exists because who to sell to and
        who else is selling are the same question asked twice: a segment every
        competitor already saturates is a worse bet at the same fit rate than
        one none of them address, and the cartographer cannot know that from
        the company's own material.
        """
        answer = await self._session.structured(
            role=CARTOGRAPHER_ROLE_ID,
            tier=ModelTier.DEEP,
            template="audience_map",
            variables={
                "company": artifacts.business.company_name or "this company",
                "what_it_does": artifacts.business.what_it_does,
                "category": artifacts.business.category,
                "business_model": artifacts.business.business_model,
                "offer": artifacts.offer.render(),
                # Who they already think they sell to. Given so it can be
                # *departed from* deliberately rather than accidentally
                # re-derived: without it the map's most likely failure is
                # spending a search to restate the homepage.
                "stated_audience": artifacts.audience.render(),
                "positioning": (
                    positioning.render_for_strategy()
                    if positioning is not None
                    else "Nobody has read this market's competitors yet."
                ),
                "limit": limit,
            },
            task=(
                "Search the web now and work out who would actually buy this. Give every "
                "segment a rate and the reasoning behind it."
            ),
            schema=_MapAnswer,
            tools=[ResearchTool.WEB_SEARCH, ResearchTool.WEB_FETCH],
        )
        kept = [
            segment
            for segment in answer.segments
            if segment.name.strip() and segment.fit >= MIN_USEFUL_FIT
        ]
        if dropped := len(answer.segments) - len(kept):
            logger.info("demand: dropped %d segment(s) below the useful fit floor", dropped)
        return DemandMap(
            segments=kept[:limit],
            searched=answer.searched,
            reading=answer.reading,
            note=answer.note,
        )


class ProspectFinder:
    """Finds named organisations matching one segment, and reads their pages."""

    def __init__(self, session: ModelSession, crawler: SiteCrawler | None = None) -> None:
        self._session = session
        self._crawler = crawler or SiteCrawler(max_pages=MAX_PAGES_PER_PROSPECT)

    async def find(
        self,
        *,
        artifacts: KnowledgeArtifacts,
        segment: AudienceSegment,
        limit: int = 10,
        known: Iterable[str] = (),
        with_contacts: bool = True,
        capability_profile: ProductCapabilityProfile | None = None,
        refresh: Iterable[ProspectLead] = (),
    ) -> list[Prospect]:
        """Named organisations for one segment, each read from its own site.

        `with_contacts` is separate from the search because they are different
        asks with different weight. A user who wants to know whether a segment
        is real wants names; a user who wants to send mail on Monday wants
        addresses, and only the second is worth reading four pages per company
        for.
        """
        refresh_leads: list[ProspectLead] = []
        refreshed: set[str] = set()
        if with_contacts:
            for lead in refresh:
                key = lead.url.strip().casefold() or lead.name.strip().casefold()
                if not key or key in refreshed:
                    continue
                refreshed.add(key)
                lead.segment = segment.name
                refresh_leads.append(lead)
                if len(refresh_leads) >= limit:
                    break
        leads = list(refresh_leads)
        remaining = max(0, limit - len(leads))
        if remaining:
            leads.extend(await self._search(artifacts, segment, remaining, known))
        if not leads:
            return []
        if not with_contacts:
            return [
                Prospect(
                    name=lead.name,
                    url=lead.url,
                    segment=segment.name,
                    why_them=lead.why_them,
                    note="their site was not read - names only",
                    qualification=(
                        CompanyQualification(
                            classification=QualificationClass.UNVERIFIED,
                            audience_structure_fit="unknown",
                            product_capability_fit="unknown",
                            evidence_completeness="missing",
                            reachability="unknown",
                            reason_codes=["site_not_read"],
                        )
                        if capability_profile is not None
                        else None
                    ),
                )
                for lead in leads
            ]

        semaphore = asyncio.Semaphore(_READ_CONCURRENCY)

        async def one(lead: ProspectLead) -> Prospect:
            async with semaphore:
                return await self._read(
                    lead, segment, artifacts, capability_profile=capability_profile
                )

        return list(await asyncio.gather(*(one(lead) for lead in leads)))

    async def _search(
        self,
        artifacts: KnowledgeArtifacts,
        segment: AudienceSegment,
        limit: int,
        known: Iterable[str],
    ) -> list[ProspectLead]:
        already = ", ".join(sorted({name.strip() for name in known if name.strip()}))
        answer = await self._session.structured(
            role=PROSPECTOR_ROLE_ID,
            tier=ModelTier.BALANCED,
            template="prospect_hunt",
            variables={
                "company": artifacts.business.company_name or "this company",
                "what_it_does": artifacts.business.what_it_does,
                "segment": segment.render(),
                "signals": "\n".join(f"- {signal}" for signal in segment.signals)
                or "- none named, which makes this harder: match on the description above",
                "where": "\n".join(f"- {place}" for place in segment.where)
                or "- nowhere named; find where this kind of company is listed",
                "known": already or "nothing yet",
                "limit": limit,
            },
            task=(
                "Search now and name real organisations that match this segment. Every entry "
                "needs a real homepage URL you found and the observable reason it is on the list."
            ),
            schema=_LeadList,
            tools=[ResearchTool.WEB_SEARCH, ResearchTool.WEB_FETCH],
        )
        seen = {name.strip().lower() for name in known}
        leads: list[ProspectLead] = []
        for lead in answer.leads:
            key = lead.name.strip().lower()
            if not key or key in seen or not lead.url:
                continue
            seen.add(key)
            lead.segment = segment.name
            leads.append(lead)
        return leads[:limit]

    async def _read(
        self,
        lead: ProspectLead,
        segment: AudienceSegment,
        artifacts: KnowledgeArtifacts,
        *,
        capability_profile: ProductCapabilityProfile | None = None,
    ) -> Prospect:
        """Read one organisation's pages and record how to reach them.

        No web tool is passed. The crawl is ours, the model sees only text this
        process fetched, and every contact it reports is checked back against
        that text - which is the only arrangement in which "we found their
        email address" is a true sentence.
        """
        try:
            pages = await self._crawler.crawl(lead.url)
        except LoaderError as exc:
            logger.info("demand: could not read %s (%s)", lead.url, exc)
            return Prospect(
                name=lead.name,
                url=lead.url,
                segment=segment.name,
                why_them=lead.why_them,
                note="their site could not be read, so there is no way in and nothing confirmed",
                qualification=(
                    qualify_company(
                        definition=segment.definition,
                        profile=capability_profile,
                        evidence=[],
                        site_verified=False,
                        pages_read=0,
                        reachable=False,
                    )
                    if capability_profile is not None
                    else None
                ),
            )

        material = _material(pages)
        if not material.strip():
            return Prospect(
                name=lead.name,
                url=lead.url,
                segment=segment.name,
                why_them=lead.why_them,
                note="their site returned no readable text",
                qualification=(
                    qualify_company(
                        definition=segment.definition,
                        profile=capability_profile,
                        evidence=[],
                        site_verified=False,
                        pages_read=0,
                        reachable=False,
                    )
                    if capability_profile is not None
                    else None
                ),
            )

        read = await self._session.structured(
            role=READER_ROLE_ID,
            tier=ModelTier.BALANCED,
            template="prospect_read",
            variables={
                "name": lead.name,
                "url": lead.url,
                "seller": artifacts.business.company_name or "our client",
                "what_we_sell": artifacts.business.what_it_does,
                "segment": segment.name,
                "signals": "\n".join(f"- {signal}" for signal in segment.signals)
                or "- none named",
                "qualification_definition": segment.definition.model_dump_json(indent=2),
                "capability_catalog": json.dumps(
                    (
                        capability_profile.extraction_catalog()
                        if capability_profile is not None
                        else []
                    ),
                    ensure_ascii=False,
                    indent=2,
                ),
                "material": material,
            },
            task=(
                "Read the pages above. Say what this organisation does, whether it really "
                "matches the segment, map its directly evidenced requirements to the supplied "
                "product capability catalogue, and quote every contact detail exactly as it appears."
            ),
            schema=_ReadProspect,
        )
        return _verify(
            lead,
            segment,
            read,
            material,
            len(pages),
            capability_profile=capability_profile,
        )


# ------------------------------------------------------------------ internals


def _material(pages: list[RawDocument]) -> str:
    parts: list[str] = []
    budget = MAX_PROSPECT_CHARS
    for page in pages:
        if budget <= 0:
            break
        body = page.content[:budget]
        parts.append(f"### {page.source}\n{body}")
        budget -= len(body)
    return "\n\n".join(parts)


def _verify(
    lead: ProspectLead,
    segment: AudienceSegment,
    read: _ReadProspect,
    material: str,
    pages: int,
    *,
    capability_profile: ProductCapabilityProfile | None = None,
) -> Prospect:
    """Keep only what the fetched pages actually contain."""
    haystack = fold(material)
    quote = fold(read.verbatim)
    supported = len(quote) >= 12 and quote in haystack
    contacts, invented = _verify_contacts(read.contacts, material, lead.url)
    signals, dropped_signals = _verify_company_signals(
        read.company_signals, material, lead.url
    )
    requirements, unmapped_requirements, dropped_requirements = (
        _verify_company_requirements(
            read.company_requirements,
            read.unmapped_requirements,
            material,
            lead.url,
            capability_profile,
        )
    )

    notes: list[str] = []
    if not supported and read.verbatim.strip():
        notes.append("the reason given for this one was not on their pages and was dropped")
    if invented:
        notes.append(
            f"{invented} contact detail(s) the extractor reported were nowhere on their "
            "site and were discarded"
        )
    if dropped_signals:
        notes.append(
            f"{dropped_signals} company qualification signal(s) were not supported by "
            "the fetched pages and were discarded"
        )
    if dropped_requirements:
        notes.append(
            f"{dropped_requirements} company requirement(s) were not bound to the active "
            "capability catalogue and fetched pages and were discarded"
        )
    if not contacts:
        notes.append("no contact detail is published anywhere we could read")

    return Prospect(
        name=lead.name,
        url=lead.url,
        segment=segment.name,
        what_they_do=read.what_they_do,
        why_them=read.why_them or lead.why_them,
        verbatim=read.verbatim if supported else "",
        # An unsupported reason costs the row half its confidence rather than
        # deleting it: the company was still found and read, and "we think so
        # but could not point at the sentence" is a real state a user can
        # judge. Deleting it would quietly turn a weak list into a short one.
        fit=read.fit if supported else min(read.fit, 0.5),
        contacts=contacts,
        caveat=read.caveat,
        verified=True,
        pages_read=pages,
        invented_contacts=invented,
        note="; ".join(notes),
        qualification=(
            qualify_company(
                definition=segment.definition,
                profile=capability_profile,
                evidence=signals,
                requirements=requirements,
                unmapped_requirements=unmapped_requirements,
                site_verified=True,
                pages_read=pages,
                reachable=bool(contacts),
            )
            if capability_profile is not None
            else None
        ),
    )


def _verify_company_requirements(
    reported: list[CompanyCapabilityRequirement],
    reported_unmapped: list[UnmappedCompanyRequirement],
    material: str,
    fallback_source: str,
    profile: ProductCapabilityProfile | None,
) -> tuple[
    list[CompanyCapabilityRequirement],
    list[UnmappedCompanyRequirement],
    int,
]:
    """Bind every extracted requirement to both fetched text and this profile."""
    haystack = fold(material)
    mapped: list[CompanyCapabilityRequirement] = []
    unmapped: list[UnmappedCompanyRequirement] = []
    seen_mapped: set[tuple[str, str]] = set()
    seen_unmapped: set[tuple[str, str]] = set()
    dropped = 0

    def supported(
        evidence_state: SignalGrounding, quote: str, source_url: str
    ) -> bool:
        if evidence_state is SignalGrounding.MISSING:
            return False
        # Capability names can be short published phrases ("voice agent",
        # "HIPAA"). Exact source binding carries the trust boundary here;
        # the longer generic-signal floor would discard valid requirements.
        if len(fold(quote)) < 4 or fold(quote) not in haystack:
            return False
        return not source_url.strip() or fold(source_url) in haystack

    for requirement in reported:
        capability_id = re.sub(
            r"[^a-z0-9]+", "_", requirement.capability_id.casefold()
        ).strip("_")
        quote = requirement.quote.strip()
        source = requirement.source_url.strip() or fallback_source
        if not capability_id or not supported(requirement.evidence_state, quote, source):
            dropped += 1
            continue
        capability = profile.capability(capability_id) if profile is not None else None
        if capability is None:
            key = (capability_id, fold(quote))
            if key not in seen_unmapped:
                unmapped.append(
                    UnmappedCompanyRequirement(
                        raw_requirement=requirement.capability_id,
                        evidence_state=requirement.evidence_state,
                        quote=quote,
                        source_url=source,
                        reasoning=requirement.reasoning,
                    )
                )
                seen_unmapped.add(key)
            continue
        key = (capability.id, fold(quote))
        if key in seen_mapped:
            continue
        mapped.append(
            requirement.model_copy(
                update={
                    "capability_id": capability.id,
                    "quote": quote,
                    "source_url": source,
                }
            )
        )
        seen_mapped.add(key)

    for requirement in reported_unmapped:
        raw_requirement = requirement.raw_requirement.strip()
        quote = requirement.quote.strip()
        source = requirement.source_url.strip() or fallback_source
        key = (raw_requirement.casefold(), fold(quote))
        if (
            not raw_requirement
            or key in seen_unmapped
            or not supported(requirement.evidence_state, quote, source)
        ):
            if raw_requirement and key not in seen_unmapped:
                dropped += 1
            continue
        unmapped.append(
            requirement.model_copy(
                update={"quote": quote, "source_url": source, "mapped_capability_id": None}
            )
        )
        seen_unmapped.add(key)
    return mapped, unmapped, dropped


def _verify_company_signals(
    reported: list[CompanySignal], material: str, fallback_source: str
) -> tuple[list[CompanySignal], int]:
    """Retain only signal bases actually present in fetched company pages."""
    haystack = fold(material)
    kept: list[CompanySignal] = []
    seen: set[tuple[str, str]] = set()
    dropped = 0
    for signal in reported:
        code = re.sub(r"[^a-z0-9]+", "_", signal.code.casefold()).strip("_")
        quote = signal.quote.strip()
        source = signal.source_identifier.strip() or fallback_source
        key = (code, signal.value.casefold().strip())
        if not code or key in seen:
            continue
        if signal.grounding is SignalGrounding.MISSING:
            kept.append(signal.model_copy(update={"code": code, "source_identifier": source}))
            seen.add(key)
            continue
        if len(fold(quote)) < 12 or fold(quote) not in haystack:
            dropped += 1
            continue
        if signal.source_identifier.strip() and fold(signal.source_identifier) not in haystack:
            dropped += 1
            continue
        kept.append(
            signal.model_copy(
                update={"code": code, "quote": quote, "source_identifier": source}
            )
        )
        seen.add(key)
    return kept, dropped


#: Where an address ends. Deliberately generous on the local part, because
#: real published addresses are `first.last+sales@`, and deliberately strict
#: about the dot in the domain.
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_DIGITS_RE = re.compile(r"\D+")

#: The shortest string of digits that can be a phone number anywhere. Below
#: this a "match" is a year, a price or a street number, and a verifier that
#: accepts those is a verifier that accepts anything.
_MIN_PHONE_DIGITS = 7

#: How many trailing digits have to be on the page for a number to count as
#: found. Trailing, because the front of a phone number is exactly the part
#: that legitimately differs between the page and a correct reading of it: a
#: page writes `+44 (0)20 7946 0018` and the right answer in a CSV column is
#: `+442079460018`, with the trunk `(0)` dropped. Comparing the whole digit
#: string rejects that - the page's stream contains `44` `0` `20` and the
#: value's contains `44` `20` - which would throw away correctly-read numbers
#: far more often than it would catch an invented one. Seven trailing digits
#: is enough that a fabricated number does not collide with a real one by
#: accident, and everything in front of them is formatting.
_PHONE_TAIL_DIGITS = 7


def _verify_contacts(
    reported: list[Contact], material: str, fallback_source: str
) -> tuple[list[Contact], int]:
    """Every contact the extractor reported, checked against the fetched text.

    The check is per kind, because "did this appear on the page" means three
    different things:

    - An **email** must be present as a string. Addresses are written the same
      way everywhere, so the folded comparison the rest of the system uses is
      exactly right, and an address that is not in the text was invented.
    - A **phone number** is written a dozen ways for one number - `+44 20 7946
      0018`, `(020) 7946 0018`, `02079460018` - so it is compared on its
      trailing digits. Requiring the exact formatting, or even the whole digit
      string, would reject correctly-read numbers at a rate that makes the
      whole field useless; see `_PHONE_TAIL_DIGITS`.
    - A **form or social URL** must be a page on their own site or a profile
      whose address is in the text. Not a mailing target either way, so the
      test only has to stop us inventing one.

    Verification is not a warning here, it is a filter: unverified values are
    dropped, never returned marked. Marked-but-shown means a list where some
    rows are real and some are fiction, sorted together, and the user
    discovers which is which by sending mail to them.
    """
    haystack = fold(material)
    digits = _DIGITS_RE.sub("", material)
    kept: list[Contact] = []
    seen: set[tuple[str, str]] = set()
    invented = 0

    for contact in reported:
        value = contact.value.strip()
        if not value:
            continue
        key = (str(contact.kind), value.lower())
        if key in seen:
            continue
        if not _is_present(contact.kind, value, haystack, digits):
            invented += 1
            continue
        seen.add(key)
        kept.append(
            contact.model_copy(
                update={
                    "value": value,
                    "source": contact.source or fallback_source,
                    "verified": True,
                }
            )
        )
    return kept, invented


def _is_present(kind: ContactKind, value: str, haystack: str, digits: str) -> bool:
    if kind is ContactKind.PHONE:
        wanted = _DIGITS_RE.sub("", value)
        if len(wanted) < _MIN_PHONE_DIGITS:
            return False
        return wanted[-_PHONE_TAIL_DIGITS:] in digits
    if kind is ContactKind.EMAIL and not _EMAIL_RE.fullmatch(value):
        # A malformed address is not a verification failure, it is a parsing
        # failure, and letting it through on a substring match would put
        # "Email us at" in a mail-merge column.
        return False
    return fold(value) in haystack


def contacts_of(contacts: list[Contact], kind: ContactKind) -> str:
    """Every verified contact of one kind, joined - the shape a CSV column wants.

    Takes the list rather than the prospect because the export reads stored
    rows, whose contacts are rehydrated from JSON by `store.prospect_contacts`
    and never assembled back into a `Prospect`.
    """
    return "; ".join(
        contact.value for contact in contacts if contact.kind is kind and contact.verified
    )
