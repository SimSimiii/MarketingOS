"""Deep research about one mapped audience, independent of the product.

The trust boundary is deliberately split in three. A search-enabled model
proposes URLs, Python fetches those exact URLs without crawling, and a second
model extracts findings from only the fetched corpus. Python then verifies
every quotation against the source it names and applies the source-tier
rules before anything can be persisted.
"""

import asyncio
import hashlib
import ipaddress
import logging
import re
import socket
from collections.abc import Awaitable, Callable, Sequence
from datetime import UTC, date, datetime
from enum import IntEnum, StrEnum
from urllib.parse import urldefrag, urljoin, urlsplit, urlunsplit

import httpx
from pydantic import BaseModel, Field, field_validator

from app.ai.base import ResearchTool
from app.ai.model_router import ModelTier
from app.ingestion.loaders.html_extract import extract_content
from app.knowledge.artifacts import Grounding, Sophistication
from app.knowledge.corpus import fold
from app.market.demand import AudienceSegment
from app.market.qualification import AudienceDefinition
from app.runtime.model_session import ModelSession

logger = logging.getLogger("marketingos.market")

ROLE_ID = "audience_researcher"

MAX_ATTEMPTED_URLS = 10
MAX_REDIRECTS = 4
MAX_SOURCE_BYTES = 750_000
MAX_CORPUS_CHARS = 72_000
MAX_SOURCE_CORPUS_CHARS = 20_000
_FETCH_CONCURRENCY = 3
_REQUEST_TIMEOUT = 15.0
_MIN_CONTENT_CHARS = 80
_MIN_QUOTE_CHARS = 8
_USER_AGENT = "MarketingOS/1.0 (fixed-url audience research)"
_HTML_TYPES = ("text/html", "application/xhtml+xml")
_TEXT_TYPES = (*_HTML_TYPES, "text/plain")
_REDIRECTS = frozenset({301, 302, 303, 307, 308})
_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)*")


class SourceTier(IntEnum):
    """How directly a fetched source observes the audience."""

    BUYER_VOICE = 1
    BEHAVIOURAL = 2
    INTERPRETATION = 3


class BuyerPhraseKind(StrEnum):
    NAMES_THE_PROBLEM = "names_the_problem"
    NAMES_A_TOOL = "names_a_tool"
    COMPLAINT = "complaint"
    AVOIDED = "avoided"


class LocatedSource(BaseModel):
    """One URL proposed by the locating call; not evidence yet."""

    url: str
    reason: str = ""
    tier: SourceTier = SourceTier.INTERPRETATION
    venue: str = ""

    @field_validator("url")
    @classmethod
    def _strip_url(cls, value: str) -> str:
        return value.strip()


class _LocatedSources(BaseModel):
    sources: list[LocatedSource] = Field(default_factory=list)


class FetchedSource(BaseModel):
    """One document fetched by this process and available to synthesis."""

    requested_url: str
    final_url: str
    title: str = ""
    tier: SourceTier
    venue: str = ""
    fetched_at: datetime
    published_date: date | None = None
    content_hash: str
    content: str


class FetchFailure(BaseModel):
    url: str
    error: str


class FetchResult(BaseModel):
    sources: list[FetchedSource] = Field(default_factory=list)
    failures: list[FetchFailure] = Field(default_factory=list)


class SourceReference(BaseModel):
    id: str
    requested_url: str
    final_url: str
    title: str = ""
    tier: SourceTier
    venue: str = ""
    fetched_at: datetime
    published_date: date | None = None
    content_hash: str


class EvidenceReference(BaseModel):
    source_id: str
    quote: str


class SourcedObservation(BaseModel):
    text: str
    grounding: Grounding = Grounding.INFERRED
    evidence: list[EvidenceReference] = Field(default_factory=list)
    inference_basis: str = ""


class AudienceProblem(BaseModel):
    id: str = ""
    statement: str
    grounding: Grounding = Grounding.INFERRED
    evidence: list[EvidenceReference] = Field(default_factory=list)
    corroboration: int = 0
    cost: str = ""
    cost_evidence: EvidenceReference | None = None


class BuyerPhrase(BaseModel):
    text: str
    kind: BuyerPhraseKind = BuyerPhraseKind.COMPLAINT
    evidence: EvidenceReference


class _ResearchDraft(BaseModel):
    """The synthesis proposal before deterministic verification."""

    situation: SourcedObservation | None = None
    incumbent_behaviour: list[SourcedObservation] = Field(default_factory=list)
    sophistication: Sophistication | None = None
    sophistication_basis: SourcedObservation | None = None
    problems: list[AudienceProblem] = Field(default_factory=list)
    buyer_phrases: list[BuyerPhrase] = Field(default_factory=list)
    triggers: list[SourcedObservation] = Field(default_factory=list)
    desired_outcomes: list[SourcedObservation] = Field(default_factory=list)
    signals: list[SourcedObservation] = Field(default_factory=list)
    where: list[SourcedObservation] = Field(default_factory=list)


class AudienceResearch(BaseModel):
    audience_name: str
    candidate_kind: str
    definition: AudienceDefinition = Field(default_factory=AudienceDefinition)
    situation: SourcedObservation | None = None
    incumbent_behaviour: list[SourcedObservation] = Field(default_factory=list)
    sophistication: Sophistication | None = None
    sophistication_basis: SourcedObservation | None = None
    problems: list[AudienceProblem] = Field(default_factory=list)
    buyer_phrases: list[BuyerPhrase] = Field(default_factory=list)
    triggers: list[SourcedObservation] = Field(default_factory=list)
    desired_outcomes: list[SourcedObservation] = Field(default_factory=list)
    signals: list[SourcedObservation] = Field(default_factory=list)
    where: list[SourcedObservation] = Field(default_factory=list)
    sources: list[SourceReference] = Field(default_factory=list)
    dropped_claims: int = 0
    researched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class URLSafetyError(ValueError):
    """A URL can reach somewhere this server must not fetch."""


class AudienceResearchError(RuntimeError):
    """A research pass cannot produce an honest persisted result."""


Resolver = Callable[[str], Awaitable[Sequence[str]]]


def _url_shape(url: str) -> tuple[str, str]:
    """Validate the non-network parts of a public HTTP URL."""
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise URLSafetyError(f"Invalid URL: {url}") from exc
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise URLSafetyError("Only absolute HTTP/HTTPS URLs can be fetched")
    if parsed.username or parsed.password:
        raise URLSafetyError("URLs containing credentials are not allowed")
    if port is not None and not 1 <= port <= 65535:
        raise URLSafetyError("URL port is outside the valid range")
    host = parsed.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        raise URLSafetyError(f"Local hostname is not allowed: {host}")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        if not address.is_global:
            raise URLSafetyError(f"Non-public address is not allowed: {host}")
    return urlunsplit((parsed.scheme.lower(), parsed.netloc, parsed.path or "/", parsed.query, "")), host


async def _resolve(host: str) -> Sequence[str]:
    loop = asyncio.get_running_loop()
    rows = await loop.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    return sorted({str(row[4][0]) for row in rows})


async def validate_public_url(url: str, resolver: Resolver | None = None) -> str:
    """Return a normalized URL only when every resolved address is public."""
    normalized, host = _url_shape(url)
    try:
        addresses = await (resolver or _resolve)(host)
    except (OSError, socket.gaierror) as exc:
        raise URLSafetyError(f"Host could not be resolved: {host}") from exc
    if not addresses:
        raise URLSafetyError(f"Host could not be resolved: {host}")
    for raw in addresses:
        try:
            address = ipaddress.ip_address(raw)
        except ValueError as exc:
            raise URLSafetyError(f"Resolver returned an invalid address for {host}") from exc
        if not address.is_global:
            raise URLSafetyError(f"Host resolves to a non-public address: {host}")
    return normalized


def _canonical_url(url: str) -> str:
    without_fragment, _ = urldefrag(url.strip())
    parsed = urlsplit(without_fragment)
    host = (parsed.hostname or "").lower().rstrip(".")
    port = f":{parsed.port}" if parsed.port else ""
    path = parsed.path.rstrip("/") or "/"
    return urlunsplit((parsed.scheme.lower(), f"{host}{port}", path, parsed.query, ""))


def bounded_sources(
    sources: Sequence[LocatedSource], limit: int = MAX_ATTEMPTED_URLS
) -> list[LocatedSource]:
    """Drop malformed/unsafe-shaped duplicates and enforce the attempt cap."""
    kept: list[LocatedSource] = []
    seen: set[str] = set()
    for source in sources:
        try:
            normalized, _ = _url_shape(source.url)
            key = _canonical_url(normalized)
        except URLSafetyError:
            logger.info("audience research: rejected unsafe or invalid URL %r", source.url)
            continue
        if key in seen:
            continue
        seen.add(key)
        kept.append(source.model_copy(update={"url": normalized}))
        if len(kept) >= limit:
            break
    return kept


class FixedURLFetcher:
    """Fetch a bounded set of exact URLs across hosts without following links."""

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        *,
        resolver: Resolver | None = None,
        max_urls: int = MAX_ATTEMPTED_URLS,
    ) -> None:
        self._client = client
        self._resolver = resolver
        self._max_urls = min(max(1, max_urls), MAX_ATTEMPTED_URLS)

    async def fetch(self, candidates: Sequence[LocatedSource]) -> FetchResult:
        sources = bounded_sources(candidates, self._max_urls)
        if not sources:
            return FetchResult()
        if self._client is not None:
            return await self._fetch_with(self._client, sources)
        async with httpx.AsyncClient(
            follow_redirects=False,
            timeout=_REQUEST_TIMEOUT,
            headers={"User-Agent": _USER_AGENT, "Accept": "text/html,text/plain;q=0.9"},
        ) as client:
            return await self._fetch_with(client, sources)

    async def _fetch_with(
        self, client: httpx.AsyncClient, sources: Sequence[LocatedSource]
    ) -> FetchResult:
        gate = asyncio.Semaphore(_FETCH_CONCURRENCY)

        async def one(source: LocatedSource) -> FetchedSource | FetchFailure:
            async with gate:
                try:
                    return await self._one(client, source)
                # A broken encoding, malformed content-length, or parser edge
                # on one stranger's page must not cost the other fetched sources.
                except Exception as exc:  # noqa: BLE001 - deliberately isolated per URL
                    logger.info("audience research: could not fetch %s (%s)", source.url, exc)
                    return FetchFailure(url=source.url, error=str(exc))

        results = await asyncio.gather(*(one(source) for source in sources))
        return FetchResult(
            sources=[item for item in results if isinstance(item, FetchedSource)],
            failures=[item for item in results if isinstance(item, FetchFailure)],
        )

    async def _one(
        self, client: httpx.AsyncClient, source: LocatedSource
    ) -> FetchedSource:
        requested = source.url
        current = requested
        raw = b""
        content_type = ""
        final_url = current
        encoding = "utf-8"
        for redirect in range(MAX_REDIRECTS + 1):
            current = await validate_public_url(current, self._resolver)
            async with client.stream("GET", current, follow_redirects=False) as response:
                if response.status_code in _REDIRECTS:
                    location = response.headers.get("location", "").strip()
                    if not location:
                        raise ValueError("Redirect response had no Location header")
                    if redirect == MAX_REDIRECTS:
                        raise ValueError("Too many redirects")
                    current = urljoin(current, location)
                    continue
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").lower()
                if content_type and not any(kind in content_type for kind in _TEXT_TYPES):
                    raise ValueError(f"Unsupported content type: {content_type}")
                declared = response.headers.get("content-length")
                if declared and int(declared) > MAX_SOURCE_BYTES:
                    raise ValueError("Response is larger than the per-source limit")
                chunks: list[bytes] = []
                size = 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > MAX_SOURCE_BYTES:
                        raise ValueError("Response exceeded the per-source limit")
                    chunks.append(chunk)
                raw = b"".join(chunks)
                final_url = str(response.url)
                encoding = response.encoding or "utf-8"
                break

        text = raw.decode(encoding, errors="replace")
        title = ""
        if any(kind in content_type for kind in _HTML_TYPES) or not content_type:
            title, _, content = extract_content(text)
        else:
            content = text.strip()
        if len(content) < _MIN_CONTENT_CHARS:
            raise ValueError("Page returned no useful readable text")
        fetched_at = datetime.now(UTC)
        return FetchedSource(
            requested_url=requested,
            final_url=final_url,
            title=title,
            tier=source.tier,
            venue=source.venue,
            fetched_at=fetched_at,
            content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
            content=content,
        )


class AudienceResearcher:
    """Locate, fetch, synthesize, and verify one admitted audience."""

    def __init__(
        self, session: ModelSession, fetcher: FixedURLFetcher | None = None
    ) -> None:
        self._session = session
        self._fetcher = fetcher or FixedURLFetcher()

    async def research(
        self,
        segment: AudienceSegment,
        *,
        on_progress: Callable[[str], None] | None = None,
    ) -> AudienceResearch:
        progress = on_progress or (lambda _message: None)
        progress("Locating first-party audience voices and behavioural sources")
        located = await self.locate(segment)
        progress(f"Fetching up to {min(len(located), MAX_ATTEMPTED_URLS)} exact source URLs")
        fetched = await self._fetcher.fetch(located)
        if not fetched.sources:
            detail = f" ({len(fetched.failures)} URL(s) failed)" if fetched.failures else ""
            raise AudienceResearchError(
                "None of the located audience sources returned useful readable text" + detail
            )
        progress(
            f"Synthesising from {len(fetched.sources)} fetched source(s); "
            f"{len(fetched.failures)} fetch(es) failed"
        )
        draft, references = await self.synthesise(segment, fetched.sources)
        verified = verify_research(segment, draft, fetched.sources, references)
        progress(
            f"Verified {len(verified.problems)} problem(s) and "
            f"{len(verified.buyer_phrases)} buyer phrase(s); "
            f"dropped {verified.dropped_claims} unverifiable item(s)"
        )
        return verified

    async def locate(self, segment: AudienceSegment) -> list[LocatedSource]:
        answer = await self._session.structured(
            role=ROLE_ID,
            tier=ModelTier.BALANCED,
            template="audience_research_locator",
            variables={"candidate": _candidate_context(segment), "limit": MAX_ATTEMPTED_URLS},
            task=(
                "Search the web now and return exact public URLs where this audience speaks "
                "or leaves observable behavioural evidence. Locate sources only; do not "
                "summarise snippets as findings."
            ),
            schema=_LocatedSources,
            tools=[ResearchTool.WEB_SEARCH],
        )
        return bounded_sources(answer.sources)

    async def synthesise(
        self, segment: AudienceSegment, fetched: Sequence[FetchedSource]
    ) -> tuple[_ResearchDraft, list[SourceReference]]:
        corpus, references = _corpus(fetched)
        draft = await self._session.structured(
            role=ROLE_ID,
            tier=ModelTier.BALANCED,
            template="audience_research_synthesis",
            variables={"candidate": _candidate_context(segment), "corpus": corpus},
            task=(
                "Using only the fetched corpus above, describe what is true about this "
                "audience independently of any product. Cite a source id and verbatim quote "
                "for every proposed finding."
            ),
            schema=_ResearchDraft,
            # Explicit even though an omitted list also means none: this call must stay a
            # closed world if the role catalogue later gains more capabilities.
            tools=[],
        )
        return draft, references


def _candidate_context(segment: AudienceSegment) -> str:
    """Discovery handles only: deliberately no fit, product bridge, angle, or objection."""
    return (
        f"Name: {segment.name}\n"
        f"Kind: {segment.kind}\n"
        f"Situation hypothesis: {segment.who or 'not stated'}\n"
        f"Possible trigger: {segment.trigger or 'not stated'}\n"
        "Observable signals:\n"
        + ("\n".join(f"- {item}" for item in segment.signals) or "- none")
        + "\nPlaces already named:\n"
        + ("\n".join(f"- {item}" for item in segment.where) or "- none")
    )


def _corpus(
    fetched: Sequence[FetchedSource],
) -> tuple[str, list[SourceReference]]:
    parts: list[str] = []
    references: list[SourceReference] = []
    budget = MAX_CORPUS_CHARS
    total_sources = len(fetched)
    for index, source in enumerate(fetched, start=1):
        source_id = f"S{index}"
        references.append(
            SourceReference(
                id=source_id,
                requested_url=source.requested_url,
                final_url=source.final_url,
                title=source.title,
                tier=source.tier,
                venue=source.venue,
                fetched_at=source.fetched_at,
                published_date=source.published_date,
                content_hash=source.content_hash,
            )
        )
        remaining_sources = total_sources - index + 1
        fair_share = max(1, budget // remaining_sources)
        body = source.content[: min(MAX_SOURCE_CORPUS_CHARS, fair_share)]
        budget -= len(body)
        parts.append(
            f'<source id="{source_id}" tier="{int(source.tier)}" '
            f'url="{source.final_url}">\n{body}\n</source>'
        )
    return "\n\n".join(parts), references


def verify_research(
    segment: AudienceSegment,
    draft: _ResearchDraft,
    fetched: Sequence[FetchedSource],
    references: Sequence[SourceReference] | None = None,
) -> AudienceResearch:
    """Apply quote, provenance, tier, numerical, and corroboration rules."""
    if references is None:
        _, built = _corpus(fetched)
        references = built
    by_id: dict[str, tuple[SourceReference, FetchedSource]] = {}
    aliases: dict[str, str] = {}
    for reference, source in zip(references, fetched, strict=True):
        by_id[reference.id] = (reference, source)
        aliases[_canonical_url(reference.requested_url)] = reference.id
        aliases[_canonical_url(reference.final_url)] = reference.id

    dropped = 0

    def evidence(
        proposed: Sequence[EvidenceReference],
    ) -> tuple[list[EvidenceReference], int]:
        kept: list[EvidenceReference] = []
        invalid = 0
        seen: set[tuple[str, str]] = set()
        for item in proposed:
            wanted = item.source_id.strip()
            if wanted not in by_id:
                try:
                    wanted = aliases.get(_canonical_url(wanted), "")
                except ValueError:
                    wanted = ""
            pair = by_id.get(wanted)
            quote = item.quote.strip()
            if pair is None or len(fold(quote)) < _MIN_QUOTE_CHARS:
                invalid += 1
                continue
            if fold(quote) not in fold(pair[1].content):
                invalid += 1
                continue
            key = (wanted, fold(quote))
            if key in seen:
                continue
            seen.add(key)
            kept.append(EvidenceReference(source_id=wanted, quote=quote))
        return kept, invalid

    def observation(item: SourcedObservation | None) -> SourcedObservation | None:
        nonlocal dropped
        if item is None or not item.text.strip():
            return None
        kept, invalid = evidence(item.evidence)
        dropped += invalid
        if not kept:
            dropped += 1
            return None
        if not _numbers_supported(item.text, kept):
            dropped += 1
            return None
        tiers = {by_id[ref.source_id][0].tier for ref in kept}
        if tiers == {SourceTier.INTERPRETATION}:
            if not item.inference_basis.strip():
                dropped += 1
                return None
            grounding = Grounding.INFERRED
        else:
            grounding = Grounding.GROUNDED
        return item.model_copy(update={"grounding": grounding, "evidence": kept})

    def observations(items: Sequence[SourcedObservation]) -> list[SourcedObservation]:
        return [kept for item in items if (kept := observation(item)) is not None]

    problems: list[AudienceProblem] = []
    for proposed in draft.problems:
        kept, invalid = evidence(proposed.evidence)
        dropped += invalid
        tier_one = [
            item
            for item in kept
            if by_id[item.source_id][0].tier is SourceTier.BUYER_VOICE
        ]
        if not proposed.statement.strip() or not tier_one:
            dropped += 1
            continue
        if not _numbers_supported(proposed.statement, kept):
            dropped += 1
            continue
        cost = proposed.cost.strip()
        cost_evidence = proposed.cost_evidence
        if cost and _NUMBER_RE.search(cost):
            verified_cost, invalid_cost = evidence([cost_evidence] if cost_evidence else [])
            dropped += invalid_cost
            numbers = _NUMBER_RE.findall(cost)
            if (
                not verified_cost
                or any(number not in fold(verified_cost[0].quote) for number in numbers)
            ):
                cost = ""
                cost_evidence = None
                dropped += 1
            else:
                cost_evidence = verified_cost[0]
        domains = {
            _normalized_domain(by_id[item.source_id][0].final_url) for item in tier_one
        }
        problems.append(
            proposed.model_copy(
                update={
                    "id": f"P{len(problems) + 1}",
                    "grounding": Grounding.GROUNDED,
                    "evidence": kept,
                    "corroboration": len(domains),
                    "cost": cost,
                    "cost_evidence": cost_evidence,
                }
            )
        )

    phrases: list[BuyerPhrase] = []
    for proposed in draft.buyer_phrases:
        kept, invalid = evidence([proposed.evidence])
        dropped += invalid
        if not kept:
            dropped += 1
            continue
        reference = by_id[kept[0].source_id][0]
        if (
            reference.tier is not SourceTier.BUYER_VOICE
            or len(fold(proposed.text)) < _MIN_QUOTE_CHARS
            or fold(proposed.text) not in fold(kept[0].quote)
        ):
            dropped += 1
            continue
        phrases.append(proposed.model_copy(update={"evidence": kept[0]}))

    sophistication_basis = observation(draft.sophistication_basis)
    sophistication = draft.sophistication
    if sophistication is not None and sophistication_basis is None:
        sophistication = None
        dropped += 1

    return AudienceResearch(
        audience_name=segment.name,
        candidate_kind=str(segment.kind),
        definition=segment.definition,
        situation=observation(draft.situation),
        incumbent_behaviour=observations(draft.incumbent_behaviour),
        sophistication=sophistication,
        sophistication_basis=sophistication_basis,
        problems=problems,
        buyer_phrases=phrases,
        triggers=observations(draft.triggers),
        desired_outcomes=observations(draft.desired_outcomes),
        signals=observations(draft.signals),
        where=observations(draft.where),
        sources=list(references),
        dropped_claims=dropped,
    )


def _normalized_domain(url: str) -> str:
    host = (urlsplit(url).hostname or "").lower().rstrip(".")
    return host.removeprefix("www.")


def _numbers_supported(text: str, evidence: Sequence[EvidenceReference]) -> bool:
    numbers = _NUMBER_RE.findall(text)
    if not numbers:
        return True
    quoted = " ".join(fold(item.quote) for item in evidence)
    return all(number in quoted for number in numbers)
