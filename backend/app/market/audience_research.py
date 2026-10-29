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
from app.core.public_http import PublicTransport
from app.ingestion.loaders.html_extract import extract_content
from app.ingestion.loaders.public_content import is_access_wall
from app.knowledge.artifacts import Grounding, Sophistication
from app.knowledge.corpus import fold
from app.market.demand import AudienceSegment, audience_fingerprint
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
    publication_date_basis: str = "unknown"
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
    publication_date_basis: str = "unknown"
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
    source_count: int = 0
    review_notes: list[str] = Field(default_factory=list)


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
    audience_fingerprint: str = ""
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
    interpretation_warnings: list[str] = Field(default_factory=list)
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
            transport=PublicTransport(), trust_env=False,
            follow_redirects=False,
            timeout=_REQUEST_TIMEOUT,
            headers={"User-Agent": _USER_AGENT, "Accept": "text/html,text/plain;q=0.9",
                     "Accept-Encoding": "identity"},
        ) as client:
            return await self._fetch_with(client, sources)

    async def _fetch_with(
        self, client: httpx.AsyncClient, sources: Sequence[LocatedSource]
    ) -> FetchResult:
        gate = asyncio.Semaphore(_FETCH_CONCURRENCY)

        async def one(source: LocatedSource) -> FetchedSource | FetchFailure:
            async with gate:
                try:
                    async with asyncio.timeout(30):
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
                if response.headers.get("content-encoding", "identity").lower() != "identity":
                    raise ValueError("Compressed responses are not supported")
                content_type = response.headers.get("content-type", "").lower()
                if content_type and not any(kind in content_type for kind in _TEXT_TYPES):
                    raise ValueError(f"Unsupported content type: {content_type}")
                declared = response.headers.get("content-length")
                if declared and int(declared) > MAX_SOURCE_BYTES:
                    raise ValueError("Response is larger than the per-source limit")
                chunks: list[bytes] = []
                size = 0
                async for chunk in response.aiter_bytes(chunk_size=65536):
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
        if is_access_wall(title, content):
            raise ValueError("Page requires access verification; no audience text was read")
        if len(content) < _MIN_CONTENT_CHARS:
            raise ValueError("Page returned no useful readable text")
        fetched_at = datetime.now(UTC)
        from app.market.source_dates import publication_date

        published_date, date_basis = publication_date(text, final_url, fetched_at.date())
        return FetchedSource(
            requested_url=requested,
            final_url=final_url,
            title=title,
            tier=source.tier,
            venue=source.venue,
            fetched_at=fetched_at,
            published_date=published_date,
            publication_date_basis=date_basis,
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
        _report_fetch_failures(fetched.failures, progress)
        if not fetched.sources and fetched.failures:
            # One fresh search may find a public alternative to an unreadable
            # forum or access wall. Never retry its subdomains or solve its
            # challenge, and never loop on empty source discovery.
            unavailable = {_source_host(item.url) for item in fetched.failures} - {""}
            progress("No readable sources; searching once for public alternatives on other hosts")
            alternatives = await self.locate(segment, unavailable_hosts=unavailable)
            recovered = await self._fetcher.fetch(alternatives)
            _report_fetch_failures(recovered.failures, progress)
            fetched = FetchResult(sources=recovered.sources, failures=[*fetched.failures, *recovered.failures])
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
        if not any((verified.situation, verified.incumbent_behaviour, verified.sophistication_basis,
                    verified.problems, verified.buyer_phrases, verified.triggers,
                    verified.desired_outcomes, verified.signals, verified.where)):
            raise AudienceResearchError("The readable sources produced no verified audience observations; no research was saved")
        if fetched.failures:
            verified.interpretation_warnings.append(
                f"Source coverage is partial: {len(fetched.sources)} readable page(s), "
                f"{len(fetched.failures)} unavailable URL(s). Findings cover only the pages read."
            )
        progress(
            f"Verified {len(verified.problems)} problem(s) and "
            f"{len(verified.buyer_phrases)} buyer phrase(s); "
            f"dropped {verified.dropped_claims} unverifiable item(s)"
        )
        return verified

    async def locate(
        self, segment: AudienceSegment, *, unavailable_hosts: set[str] | None = None,
    ) -> list[LocatedSource]:
        answer = await self._session.structured(
            role=ROLE_ID,
            tier=ModelTier.BALANCED,
            template="audience_research_locator",
            variables={"candidate": _candidate_context(segment), "limit": MAX_ATTEMPTED_URLS},
            task=(
                "Search the web now and return exact public URLs where this audience speaks "
                "or leaves observable behavioural evidence. Locate sources only; do not "
                "summarise snippets as findings."
                + (" Previously attempted hosts returned no readable text: "
                   + ", ".join(sorted(unavailable_hosts))
                   + ". Find other public source hosts. Do not use these hosts or their subdomains, "
                   "authenticate, or try to bypass an access restriction."
                   if unavailable_hosts else "")
            ),
            schema=_LocatedSources,
            tools=[ResearchTool.WEB_SEARCH],
        )
        located = bounded_sources(answer.sources)
        classified = {_canonical_url(item.url): item for item in located}
        # Reuse discovery leads, never its assertions. Every page is fetched
        # afresh and an unclassified lead remains interpretation-tier evidence.
        seeds = [classified.get(_canonical_url(item.url), item)
                 for item in _map_source_leads(segment)]
        return bounded_sources([
            item for item in [*seeds, *located]
            if not any(_source_host(item.url) == host or _source_host(item.url).endswith("." + host)
                       for host in unavailable_hosts or set())
        ])

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


def _report_fetch_failures(failures: Sequence[FetchFailure], progress: Callable[[str], None]) -> None:
    def public_path(value: str) -> str:
        try:
            parsed = urlsplit(value.rstrip(".,;)'\""))
            return urlunsplit((parsed.scheme, parsed.hostname or "invalid-host", parsed.path, "", ""))
        except ValueError:
            return "invalid-public-url"
    for failure in failures[:MAX_ATTEMPTED_URLS]:
        error = re.sub(r"https?://[^\s<>]+", lambda match: public_path(match[0]), failure.error)
        progress(f"Unreadable source: {public_path(failure.url)} — {error[:200]}")


def _source_host(url: str) -> str:
    try:
        return (urlsplit(url).hostname or "").lower().removeprefix("www.")
    except ValueError:
        return ""


def _candidate_context(segment: AudienceSegment) -> str:
    """Discovery handles only: deliberately no fit, product bridge, angle, or objection."""
    return (
        f"Name: {segment.name}\n"
        f"Kind: {segment.kind}\n"
        f"Organization hypothesis: {segment.organization or 'not stated'}\n"
        f"Situation hypothesis: {segment.workflow or segment.who or 'not stated'}\n"
        f"Need hypothesis to test, not assume: {segment.need or 'not stated'}\n"
        f"Possible trigger: {segment.trigger or 'not stated'}\n"
        "Observable signals:\n"
        + ("\n".join(f"- {item}" for item in segment.signals) or "- none")
        + "\nPlaces already named:\n"
        + ("\n".join(f"- {item}" for item in segment.where) or "- none")
        + "\nPreviously located source leads (recheck relevance and voice tier):\n"
        + ("\n".join(f"- {item.url}" for item in _map_source_leads(segment)) or "- none")
    )


def _map_source_leads(segment: AudienceSegment) -> list[LocatedSource]:
    return bounded_sources([
        LocatedSource(url=item.url, reason="Previously located map lead; re-fetch and reclassify.")
        for item in segment.assessment.evidence
        if item.kind in {"need", "counterevidence"}
    ], limit=2)


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
                publication_date_basis=source.publication_date_basis,
                content_hash=source.content_hash,
            )
        )
        remaining_sources = total_sources - index + 1
        fair_share = max(1, budget // remaining_sources)
        body = source.content[: min(MAX_SOURCE_CORPUS_CHARS, fair_share)]
        budget -= len(body)
        parts.append(
            f'<source id="{source_id}" tier="{int(source.tier)}" '
            f'url="{source.final_url}" published_date="{source.published_date or "unknown"}" '
            f'date_basis="{source.publication_date_basis}">\n{body}\n</source>'
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
        if tiers == {SourceTier.INTERPRETATION} or item.inference_basis.strip():
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

    return review_research_interpretations(AudienceResearch(
        audience_name=segment.name,
        audience_fingerprint=audience_fingerprint(segment),
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
    ))


def review_research_interpretations(research: AudienceResearch) -> AudienceResearch:
    """Downgrade clear directional reversals without claiming entailment.

    Quotation presence was verified elsewhere. This bounded, free check keeps
    the quotation inspectable while preventing an opposite interpretation
    from being presented as grounded. It also works on stored research, with
    no refetch or model call and without modifying historical payloads.
    """
    reviewed = research.model_copy(deep=True)
    reversal_prefixes = (
        "Review required: this problem may reverse the cited source's meaning.",
        "Review required: this interpretation may reverse the cited source's meaning.",
    )
    warnings = [warning for warning in reviewed.interpretation_warnings
                if not warning.startswith(reversal_prefixes)]
    from app.market.source_dates import date_from_url

    for source in reviewed.sources:
        if source.published_date is None:
            source.published_date = date_from_url(source.final_url, reviewed.researched_at.date())
            if source.published_date:
                source.publication_date_basis = "dated_url"
    sources = {source.id: source for source in reviewed.sources}

    def temporal(refs: list[EvidenceReference]) -> list[str]:
        used = [sources[ref.source_id] for ref in refs if ref.source_id in sources]
        dates = sorted({source.published_date for source in used if source.published_date})
        notes: list[str] = []
        retrospective_years = {}
        for source in used:
            match = re.search(r"\b(20\d{2})\s+(?:in\s+review|retro(?:spective)?|recap)\b",
                              source.title, re.IGNORECASE)
            if match and reviewed.researched_at.year - int(match.group(1)) > 2:
                retrospective_years[source.id] = match.group(1)
        if used and all((source.published_date and
                         (reviewed.researched_at.date() - source.published_date).days > 730)
                        or source.id in retrospective_years for source in used):
            labels = [str(value) for value in dates]
            labels += ["retrospective content " + year for year in sorted(set(retrospective_years.values()))]
            notes.append("Historical sources (" + ", ".join(labels)
                         + "); present applicability is not corroborated.")
        if used and len(dates) == 0:
            notes.append("Publication date unknown; retrieval today does not establish current applicability.")
        return notes

    def observation(item: SourcedObservation | None) -> None:
        if item is None:
            return
        item.inference_basis = item.inference_basis.replace(reversal_prefixes[1], "").strip("; ")
        notes = temporal(item.evidence)
        if notes:
            for note in notes:
                if note not in item.inference_basis:
                    item.inference_basis = "; ".join(filter(None, [item.inference_basis, note]))
            if any(note.startswith("Historical") for note in notes):
                item.grounding = Grounding.INFERRED
            warnings.extend(f"{note} {item.text}" for note in notes)
        if not interpretation_reversal(item.text, item.evidence):
            return
        note = "Review required: this interpretation may reverse the cited source's meaning."
        item.grounding = Grounding.INFERRED
        if note not in item.inference_basis:
            item.inference_basis = "; ".join(filter(None, (item.inference_basis, note)))
        warnings.append(f"{note} {item.text}")

    for item in (reviewed.situation, reviewed.sophistication_basis):
        observation(item)
    for items in (reviewed.incumbent_behaviour, reviewed.triggers, reviewed.desired_outcomes,
                  reviewed.signals, reviewed.where):
        for item in items:
            observation(item)
    for problem in reviewed.problems:
        used = {ref.source_id for ref in problem.evidence if ref.source_id in sources}
        # Copies of the same fetched text on different hosts are one source.
        unique = {sources[key].content_hash or sources[key].final_url for key in used}
        problem.source_count = len(unique)
        domains = {_normalized_domain(sources[key].final_url) for key in used}
        problem.corroboration = min(problem.corroboration, len(domains), len(unique))
        notes = temporal(problem.evidence)
        if any(note.startswith("Historical") for note in notes):
            problem.grounding = Grounding.INFERRED
        if problem.source_count == 1:
            notes.append("Single-source problem; independent corroboration is not established.")
        # These fields are computed review metadata, not model attestations.
        problem.review_notes = list(dict.fromkeys(notes))
        warnings.extend(f"{problem.id}: {note}" for note in notes)
        if interpretation_reversal(problem.statement, problem.evidence):
            problem.grounding = Grounding.INFERRED
            problem.corroboration = 0
            warnings.append(
                "Review required: this problem may reverse the cited source's meaning. "
                + problem.statement
            )
    problem_sources = {sources[ref.source_id].content_hash or sources[ref.source_id].final_url
                       for problem in reviewed.problems for ref in problem.evidence
                       if ref.source_id in sources}
    if len(reviewed.problems) > 1 and len(problem_sources) == 1:
        warnings.append(f"All {len(reviewed.problems)} problems rely on one source; problem count is not corroboration.")
    reviewed.interpretation_warnings = list(dict.fromkeys(warnings))
    return reviewed


_INTERPRETATION_DIRECTIONS = (
    (r"\b(?:easier|easy|simpler|simplif\w*|straightforward|moins complexe|plus simple)\b",
     r"\b(?:complicat\w*|harder|difficult\w*|more complex|complexif\w*|plus complexe|plus difficile)\b"),
    (r"\b(?:increas\w*|higher|rises?|rising|augment\w*)\b",
     r"\b(?:decreas\w*|reduc\w*|lower|falls?|falling|diminu\w*)\b"),
)
_INTERPRETATION_STOPWORDS = frozenset({
    "the", "this", "that", "with", "from", "their", "they", "our", "your", "and", "for",
    "make", "makes", "making", "are", "was", "were", "have", "has", "can", "will", "been",
    "its", "plus", "moins", "les", "des", "une", "dans", "avec", "est", "sont", "pour",
})


def interpretation_reversal(text: str, evidence: Sequence[EvidenceReference]) -> bool:
    """Only opposing direction with shared topical anchors triggers review.

    A mixed interpretation needs support for each direction it adds. Negated
    directions remain uncertain. This is not general semantic validation and
    never certifies a statement as entailed.
    """
    # A consequence can describe a different object (a complex incumbent
    # pushing buyers toward simpler alternatives). Do not attribute the
    # consequence's direction to the incumbent's topical anchors.
    clauses = re.split(r",\s+(?=(?:pushing|prompting|driving|leading)\b)", text, flags=re.IGNORECASE)
    if len(clauses) > 1:
        return any(interpretation_reversal(clause, evidence) for clause in clauses)
    proposed = fold(text)
    for positive, negative in _INTERPRETATION_DIRECTIONS:
        pattern = f"(?:{positive})|(?:{negative})"

        def directions(value: str, combined: str = pattern, positive_pattern: str = positive) -> set[int]:
            signs: set[int] = set()
            for match in re.finditer(combined, value):
                if re.search(r"\b(?:not|no|never|ne|pas|sans)\b", value[max(0, match.start() - 22):match.start()]):
                    continue
                signs.add(1 if re.fullmatch(positive_pattern, match.group(0)) else -1)
            return signs

        proposed_directions = directions(proposed)
        if not proposed_directions:
            continue
        meaningful = _interpretation_topics(re.sub(pattern, " ", proposed))
        quotes = [fold(item.quote) for item in evidence]
        supported_directions: set[int] = set()
        for quote in quotes:
            anchors = _interpretation_topics(re.sub(pattern, " ", quote))
            if len(meaningful & anchors) >= 2:
                supported_directions.update(directions(quote))
        if any(-direction in supported_directions and direction not in supported_directions
               for direction in proposed_directions):
            return True
    return False


def _interpretation_topics(text: str) -> set[str]:
    # Minimal inflection folding lets "handling" and "handle", or
    # "modules" and "module", anchor the same topic without an NLP layer.
    words = set(re.findall(r"[^\W\d_]{3,}", text)) - _INTERPRETATION_STOPWORDS
    return {re.sub(r"(?:ing|ed|s)$", "", word).rstrip("e") for word in words}


def _normalized_domain(url: str) -> str:
    host = (urlsplit(url).hostname or "").lower().rstrip(".")
    return host.removeprefix("www.")


def _numbers_supported(text: str, evidence: Sequence[EvidenceReference]) -> bool:
    numbers = _NUMBER_RE.findall(text)
    if not numbers:
        return True
    quoted = " ".join(fold(item.quote) for item in evidence)
    return all(number in quoted for number in numbers)
