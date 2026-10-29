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
import hashlib
import json
import logging
import re
from datetime import UTC, datetime
from urllib.parse import urldefrag, urlsplit, urlunsplit

from pydantic import BaseModel, Field, field_validator

from app.ai.base import ResearchTool
from app.ai.model_router import ModelTier
from app.ingestion.documents import RawDocument
from app.ingestion.exceptions import LoaderError
from app.ingestion.loaders.site_crawler import SiteCrawler
from app.knowledge.artifacts import BusinessProfile, KnowledgeArtifacts
from app.knowledge.corpus import fold
from app.knowledge.decision_context import evidence_record, select_evidence
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
    public_urls: list[str] = Field(default_factory=list, max_length=2)

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
    discovery_reason: str = ""
    rationale_status: str = "unverified"
    rationale_sources: list[str] = Field(default_factory=list)
    our_evidence_ids: list[str] = Field(default_factory=list)
    public_urls: list[str] = Field(default_factory=list)
    source_fingerprint: str = ""
    reused: bool = False
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
    public_pages: dict[str, list[str]] = Field(default_factory=dict)


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
    why: str = ""
    why_sources: list[str] = Field(default_factory=list)
    our_evidence_ids: list[str] = Field(default_factory=list)


class RivalScout:
    """Finds and profiles the competitors a reader is really choosing between."""

    def __init__(self, session: ModelSession, crawler: SiteCrawler | None = None) -> None:
        self._session = session
        self._crawler = crawler or SiteCrawler(max_pages=MAX_PAGES_PER_RIVAL)

    async def discover(
        self, business: BusinessProfile, limit: int = 6, known: list[str] | None = None,
        public_page_requests: dict[str, str] | None = None,
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
                "public_page_requests": json.dumps(public_page_requests or {}, ensure_ascii=False),
                "limit": limit,
            },
            task=(
                "Search the web now and report who this company's buyer is really "
                "deciding between. Every entry needs a real URL you found."
            ),
            schema=_LeadList,
            # Discovery locates URLs; profile() crawls the pages itself and
            # verifies every retained quotation against that fetched text.
            tools=[ResearchTool.WEB_SEARCH],
        )

    async def profile_all(self, leads: list[RivalLead], *, artifacts: KnowledgeArtifacts | None = None,
                          previous: list[RivalProfile] | None = None) -> list[RivalProfile]:
        semaphore = asyncio.Semaphore(_PROFILE_CONCURRENCY)

        async def one(lead: RivalLead) -> RivalProfile:
            async with semaphore:
                old = next((item for item in previous or [] if _source_key(item.url) == _source_key(lead.url)
                            and item.name.casefold() == lead.name.casefold()), None)
                if old and not lead.public_urls:
                    lead = lead.model_copy(update={"public_urls": old.public_urls})
                return await self.profile(lead, artifacts=artifacts, previous=old)

        return list(await asyncio.gather(*(one(lead) for lead in leads)))

    async def profile(self, lead: RivalLead, *, artifacts: KnowledgeArtifacts | None = None,
                      previous: RivalProfile | None = None) -> RivalProfile:
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
        focus = " ".join([
            lead.why,
            artifacts.business.what_it_does if artifacts else "",
            *(entry.claim for entry in artifacts.evidence.entries if artifacts),
        ]) if artifacts else lead.why
        try:
            pages = await self._crawler.crawl(lead.url, focus=focus)
        except LoaderError as exc:
            logger.info("rivals: could not read %s (%s)", lead.url, exc)
            pages = []

        # Read only fallback URLs actually found in discovery, never guessed
        # marketing paths. All crawls retain the public HTTP safety boundary.
        if not _material(pages).strip():
            for url in lead.public_urls[:2]:
                if _source_key(url) == _source_key(lead.url):
                    continue
                try:
                    pages = await self._crawler.crawl(url, focus=focus)
                except LoaderError:
                    continue
                if _material(pages).strip():
                    break

        material = _material(pages)
        if not material.strip():
            return RivalProfile(
                name=lead.name,
                url=lead.url,
                kind=lead.kind,
                discovery_reason=lead.why,
                note="their site could not be read or returned no readable text",
                public_urls=lead.public_urls,
            )

        ours = select_evidence(
            artifacts.evidence, lead.why or artifacts.business.what_it_does,
            preferred_ids=[plan.provenance.evidence_id for plan in artifacts.offer.plans
                           if plan.provenance and plan.provenance.evidence_id],
            cap=12,
        ).ledger if artifacts else None
        our_context = json.dumps([evidence_record(entry) for entry in ours.entries], ensure_ascii=False) if ours else "[]"
        fingerprint = hashlib.sha256(json.dumps({
            "version": 3, "template": self._session.template_fingerprint("rival_profile"),
            "schema": _ExtractedProfile.model_json_schema(),
            "lead": lead.model_dump(exclude={"public_urls"}),
            "ours": our_context, "material": material,
        }, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        if (previous and previous.verified and (previous.claims.claims or previous.proof_shown)
                and previous.source_fingerprint == fingerprint):
            return review_rationale(previous.model_copy(update={
                "checked_at": datetime.now(UTC), "reused": True,
                "discovery_reason": lead.why, "kind": lead.kind,
            }))

        extracted = await self._session.structured(
            role=PROFILER_ROLE_ID,
            tier=ModelTier.BALANCED,
            template="rival_profile",
            variables={"name": lead.name, "url": lead.url, "material": material,
                       "discovery_reason": lead.why, "our_context": our_context},
            task=(
                "Read the pages above and report what this company promises. Quote them "
                "verbatim for every claim."
            ),
            schema=_ExtractedProfile,
        )
        verified = _verify(lead, extracted, pages)
        valid_sources = {_source_key(claim.source) for claim in [*verified.claims.claims, *verified.proof_shown]}
        refs = list(dict.fromkeys(extracted.our_evidence_ids))
        rationale_sources = list(dict.fromkeys(extracted.why_sources))
        own_sources = {_source_key(entry.source) for entry in ours.entries
                       if entry.id in refs and entry.source} if ours else set()
        cited_sources = {_source_key(url) for url in rationale_sources}
        if (extracted.why.strip() and rationale_sources and refs and ours
                and set(refs) <= ours.ids
                and cited_sources & valid_sources
                and cited_sources <= valid_sources | own_sources):
            verified.why = extracted.why.strip()
            verified.rationale_status = "source_linked_hypothesis"
            verified.rationale_sources = rationale_sources
            verified.our_evidence_ids = refs
        else:
            reason = (
                "no comparison was returned" if not extracted.why.strip()
                else "references to both products did not resolve to verified evidence"
            )
            verified.note = " ".join(filter(None, (
                verified.note, f"Comparison hypothesis withheld: {reason}.",
            )))
        verified.source_fingerprint = fingerprint
        return review_rationale(verified)


def review_rationale(profile: RivalProfile) -> RivalProfile:
    """Do not turn selected plan prices into a supposedly sourced range.

    Finding both endpoint amounts somewhere in the capture does not license
    a range covering the whole offer. Keep the capture; withhold the synthesis.
    """
    ranges = re.findall(r"[$€£]\s*\d+(?:[.,]\d+)?\s*[-–—]\s*(?:[$€£]\s*)?\d+(?:[.,]\d+)?",
                        profile.why)
    if not ranges:
        return profile

    def normalized(value: str) -> str:
        return re.sub(r"\s+", "", re.sub(r"[–—]", "-", value))

    quotes = [normalized(claim.verbatim) for claim in profile.claims.claims]
    if all(any(normalized(value) in quote for quote in quotes) for value in ranges):
        return profile
    note = "Comparison hypothesis withheld: the quoted pages do not state the synthesized price range."
    return profile.model_copy(update={
        "why": "", "rationale_status": "unverified", "rationale_sources": [], "our_evidence_ids": [],
        "note": " ".join(dict.fromkeys(filter(None, (profile.note, note)))),
    })


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
    lead: RivalLead, extracted: _ExtractedProfile, pages: list[RawDocument]
) -> RivalProfile:
    """Keep only what the pages actually said.

    Typography-blind, for the reason the whole system is: every published page
    has been through a CMS that made its apostrophes curly, and a model asked
    to quote one back answers in plain ASCII about half the time. Under an
    exact test those are different strings, and a correctly quoted claim would
    be thrown away over one character.
    """
    # Use exactly the same bound as the prompt. A quotation found on some
    # other page is not verification of the citation the extractor supplied.
    sources: dict[str, tuple[str, str]] = {}
    budget = MAX_PROFILE_CHARS
    for page in pages:
        if budget <= 0:
            break
        body = page.content[:budget]
        sources[_source_key(page.source)] = (page.source, fold(body))
        budget -= len(body)
    kept: list[Claim] = []
    dropped = 0
    for claim in [*extracted.claims, *extracted.proof_shown]:
        quote = fold(claim.verbatim)
        cited = sources.get(_source_key(claim.source)) if claim.source else None
        if not claim.source:
            matches = [source for source in sources.values() if quote and quote in source[1]]
            cited = matches[0] if len(matches) == 1 else None
        if len(quote) >= 12 and cited is not None and quote in cited[1]:
            context = claim.context.model_copy(deep=True)
            context.verification = "quote_verified_on_cited_page"
            claim = claim.model_copy(update={"source": cited[0], "context": context})
            kept.append(claim)
        else:
            dropped += 1

    proof_texts = {claim.text for claim in extracted.proof_shown}
    return RivalProfile(
        name=lead.name,
        url=lead.url,
        kind=lead.kind,
        discovery_reason=lead.why,
        public_urls=lead.public_urls,
        one_liner=extracted.one_liner,
        promise=extracted.promise,
        claims=ClaimSet(claims=[c for c in kept if c.text not in proof_texts]),
        proof_shown=[c for c in kept if c.text in proof_texts],
        pricing=extracted.pricing,
        free_entry=extracted.free_entry,
        icp=extracted.icp,
        vocabulary=[word for word in extracted.vocabulary if word.strip()][:30],
        verified=True,
        pages_read=len(pages),
        unverified_claims=dropped,
        note=(
            f"{dropped} claim(s) the extractor reported were not on their pages and were "
            "discarded"
            if dropped
            else ""
        ),
    )


def _source_key(url: str) -> str:
    parsed = urlsplit(urldefrag(url.strip())[0])
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip("/"),
                       parsed.query, ""))
