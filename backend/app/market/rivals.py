"""Who else the reader is deciding between, and what each of them promises.

Split deliberately into two steps with two different trust models, because
they are two different jobs and only one of them needs the open web.

**Discovery needs search and cannot be verified.** There is no way to learn
that Portkey exists from Portkey's competitors' pages, so this step reads the
web, and what comes back is a *lead*: a name and a URL, proposed. Nothing is
believed yet.

**Profiling needs no search at all.** Once a lead names a URL, the honest way
to find out what that company promises is to read its pages - with the same
crawler that reads the user's own site - and extract claims from text we
fetched ourselves. Then every claim's quotation is checked against the page it
came from, in code, exactly as the evidence gate checks a draft against the
ledger.

That split is what makes a competitor profile worth putting in front of a
strategist. A model asked "what does Portkey claim?" answers from training
data of unknown age; a model handed Portkey's pricing page, whose answers are
then quote-checked against it, is doing extraction, which is the thing it is
reliably good at. It also means a rival that has changed its positioning since
the model was trained is read correctly, and a rival that has quietly gone out
of business fails to crawl instead of being profiled from memory.

A lead whose site cannot be read is kept and marked unverified rather than
dropped: "we found this competitor and could not read their site" is a true
and useful thing to tell a user, and silently losing it is not.
"""

import asyncio
import logging
from datetime import UTC, datetime

from pydantic import BaseModel, Field, field_validator

from app.ai.base import ResearchTool
from app.ai.model_router import ModelTier
from app.ingestion.documents import RawDocument
from app.ingestion.exceptions import LoaderError
from app.ingestion.loaders.site_crawler import SiteCrawler
from app.knowledge.artifacts import BusinessProfile
from app.knowledge.corpus import fold
from app.market.claims import Claim, ClaimSet
from app.runtime.model_session import ModelSession

logger = logging.getLogger("marketingos.market")

SCOUT_ROLE_ID = "rival_scout"
PROFILER_ROLE_ID = "rival_profiler"

#: Pages read per competitor. Far below the user's own site budget: we are not
#: compiling a business here, we are reading a positioning statement, and it is
#: on the home page, the pricing page and one product page. A twelve-page crawl
#: of a competitor buys a careers page.
MAX_PAGES_PER_RIVAL = 5

#: How many characters of a competitor's site reach the extraction call. Their
#: home and pricing pages, not their documentation.
MAX_PROFILE_CHARS = 24_000

#: How many competitors are profiled at once. They are independent crawls of
#: different hosts, so this is wall-clock that costs nothing to save.
_PROFILE_CONCURRENCY = 3


class RivalLead(BaseModel):
    """A competitor somebody proposed. Not yet believed."""

    name: str
    url: str = ""
    #: Why this one is in the list - in the user's terms, not the market's.
    #: "Where a team that outgrows spreadsheets usually looks first" is a
    #: reason; "a leading player in the space" is not.
    why: str = ""
    #: How the reader would meet them: a direct alternative, the incumbent
    #: everyone already has, or the thing they would do instead of buying
    #: anything.
    kind: str = "alternative"

    @field_validator("url")
    @classmethod
    def _normalize(cls, value: str) -> str:
        url = value.strip()
        if url and not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        return url


class RivalProfile(BaseModel):
    """One competitor, read from their own pages."""

    name: str
    url: str = ""
    kind: str = "alternative"
    why: str = ""
    #: How they describe themselves, in their words.
    one_liner: str = ""
    #: The single bet their home page makes.
    promise: str = ""
    claims: ClaimSet = Field(default_factory=ClaimSet)
    #: Named customers, quotes and outcomes *they* display. Kept apart from
    #: `claims` because this is the one thing a competitor has that a company
    #: cannot answer by writing better copy.
    proof_shown: list[Claim] = Field(default_factory=list)
    pricing: str = ""
    free_entry: str = ""
    #: Who they say it is for.
    icp: str = ""
    #: The words they use. Feeds the sameness check.
    vocabulary: list[str] = Field(default_factory=list)
    #: True when their site was actually read. False means this is a lead we
    #: could not verify, and everything above it is empty by construction.
    verified: bool = False
    pages_read: int = 0
    #: Claims the model produced that were not really on the page. Recorded
    #: rather than silently dropped: a profile that lost half its claims to
    #: this is a profile a user should distrust, and the count is the only way
    #: they would know.
    unverified_claims: int = 0
    note: str = ""
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def render(self) -> str:
        if not self.verified:
            return f"- **{self.name}** ({self.url or 'no url'}) - {self.note or 'not read'}"
        lines = [
            f"- **{self.name}** ({self.url})",
            f"    what they promise: {self.promise or self.one_liner or 'unclear'}",
        ]
        if self.pricing:
            lines.append(f"    pricing: {self.pricing}")
        if self.free_entry:
            lines.append(f"    way in: {self.free_entry}")
        if self.proof_shown:
            lines.append(
                "    proof they show: "
                + "; ".join(item.text for item in self.proof_shown[:3])
            )
        if self.claims.claims:
            lines.append(
                "    what they claim: "
                + "; ".join(claim.render() for claim in self.claims.claims[:6])
            )
        return "\n".join(lines)


class _LeadList(BaseModel):
    """What the scout returns. A wrapper because the structured-output path
    needs an object at the top level, not an array."""

    leads: list[RivalLead] = Field(default_factory=list)
    #: What the scout searched for. Shown to the user so a thin result is
    #: explainable - "we looked for these three things and this is all there
    #: was" is a finding; an empty list on its own is a bug report.
    searched: list[str] = Field(default_factory=list)


class _ExtractedProfile(BaseModel):
    """The extraction call's answer, before anything is verified."""

    one_liner: str = ""
    promise: str = ""
    claims: list[Claim] = Field(default_factory=list)
    proof_shown: list[Claim] = Field(default_factory=list)
    pricing: str = ""
    free_entry: str = ""
    icp: str = ""
    vocabulary: list[str] = Field(default_factory=list)


class RivalScout:
    """Finds and profiles the competitors a reader is really choosing between."""

    def __init__(self, session: ModelSession, crawler: SiteCrawler | None = None) -> None:
        self._session = session
        self._crawler = crawler or SiteCrawler(max_pages=MAX_PAGES_PER_RIVAL)

    async def discover(
        self, business: BusinessProfile, limit: int = 6, known: list[str] | None = None
    ) -> _LeadList:
        """Who else sells to this buyer. The one step that reads the open web.

        `known` is what the user already told us, and it is passed in so the
        scout spends its searches on the names nobody has thought of rather
        than re-finding the two obvious ones.
        """
        already = ", ".join(known or []) or "nothing yet"
        return await self._session.structured(
            role=SCOUT_ROLE_ID,
            tier=ModelTier.BALANCED,
            template="rival_scan",
            variables={
                "company": business.company_name or "this company",
                "what_it_does": business.what_it_does,
                "category": business.category,
                "vocabulary": ", ".join(business.vocabulary[:20]),
                "known": already,
                "limit": limit,
            },
            task=(
                "Search the web now and report who this company's buyer is really "
                "deciding between. Every entry needs a real URL you found."
            ),
            schema=_LeadList,
            tools=[ResearchTool.WEB_SEARCH, ResearchTool.WEB_FETCH],
        )

    async def profile_all(self, leads: list[RivalLead]) -> list[RivalProfile]:
        semaphore = asyncio.Semaphore(_PROFILE_CONCURRENCY)

        async def one(lead: RivalLead) -> RivalProfile:
            async with semaphore:
                return await self.profile(lead)

        return list(await asyncio.gather(*(one(lead) for lead in leads)))

    async def profile(self, lead: RivalLead) -> RivalProfile:
        """Read one competitor's pages and record what they promise.

        No web tool is used here at all - the crawl is our own, and the model
        only ever sees text this process fetched. See the module docstring.
        """
        if not lead.url:
            return RivalProfile(
                name=lead.name,
                kind=lead.kind,
                why=lead.why,
                note="no website was found for this one, so nothing could be read",
            )
        try:
            pages = await self._crawler.crawl(lead.url)
        except LoaderError as exc:
            logger.info("rivals: could not read %s (%s)", lead.url, exc)
            return RivalProfile(
                name=lead.name,
                url=lead.url,
                kind=lead.kind,
                why=lead.why,
                note="their site could not be read, so nothing here is from them",
            )

        material = _material(pages)
        if not material.strip():
            return RivalProfile(
                name=lead.name,
                url=lead.url,
                kind=lead.kind,
                why=lead.why,
                note="their site returned no readable text",
            )

        extracted = await self._session.structured(
            role=PROFILER_ROLE_ID,
            tier=ModelTier.BALANCED,
            template="rival_profile",
            variables={"name": lead.name, "url": lead.url, "material": material},
            task=(
                "Read the pages above and report what this company promises. Quote them "
                "verbatim for every claim."
            ),
            schema=_ExtractedProfile,
        )
        return _verify(lead, extracted, material, len(pages))


def _material(pages: list[RawDocument]) -> str:
    """The competitor's own pages, in one block, bounded.

    Highest-value pages first is already the crawler's contract, so a bound
    that bites cuts the careers page and keeps the pricing page.
    """
    parts: list[str] = []
    budget = MAX_PROFILE_CHARS
    for page in pages:
        if budget <= 0:
            break
        body = page.content[:budget]
        parts.append(f"### {page.source}\n{body}")
        budget -= len(body)
    return "\n\n".join(parts)


def _verify(
    lead: RivalLead, extracted: _ExtractedProfile, material: str, pages: int
) -> RivalProfile:
    """Keep only what the pages actually said.

    Typography-blind, for the reason the whole system is: every published page
    has been through a CMS that made its apostrophes curly, and a model asked
    to quote one back answers in plain ASCII about half the time. Under an
    exact test those are different strings, and a correctly quoted claim would
    be thrown away over one character.
    """
    haystack = fold(material)
    kept: list[Claim] = []
    dropped = 0
    for claim in [*extracted.claims, *extracted.proof_shown]:
        quote = fold(claim.verbatim)
        if len(quote) >= 12 and quote in haystack:
            kept.append(claim)
        else:
            dropped += 1

    proof_texts = {claim.text for claim in extracted.proof_shown}
    return RivalProfile(
        name=lead.name,
        url=lead.url,
        kind=lead.kind,
        why=lead.why,
        one_liner=extracted.one_liner,
        promise=extracted.promise,
        claims=ClaimSet(claims=[c for c in kept if c.text not in proof_texts]),
        proof_shown=[c for c in kept if c.text in proof_texts],
        pricing=extracted.pricing,
        free_entry=extracted.free_entry,
        icp=extracted.icp,
        vocabulary=[word for word in extracted.vocabulary if word.strip()][:30],
        verified=True,
        pages_read=pages,
        unverified_claims=dropped,
        note=(
            f"{dropped} claim(s) the extractor reported were not on their pages and were "
            "discarded"
            if dropped
            else ""
        ),
    )
