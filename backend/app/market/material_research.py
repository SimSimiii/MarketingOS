"""Recover campaign-critical facts from official public documentation.

The craft loop can identify a useful failure precisely: the copy cannot answer
the reader because the campaign does not contain a particular fact.  Leaving
that as a report asks the operator to become the missing pipeline step.  This
module closes that loop without weakening the evidence boundary:

1. a search-enabled market role locates official product or platform pages;
2. Python fetches only those exact public URLs;
3. a closed-world synthesis call proposes claims from the fetched text; and
4. Python rejects every quotation it cannot find in the fetched page.

Only the verified result can enter the campaign ledger and source corpus.
Third-party testimonials still use the approval flow in ``app.market.proof``;
this path is deliberately limited to product capabilities, integrations,
setup instructions, limits and commercial facts stated in official docs.
"""

import logging
import re
from collections.abc import Sequence
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, field_validator

from app.ai.base import ResearchTool
from app.ai.model_router import ModelTier
from app.knowledge.artifacts import KnowledgeArtifacts
from app.knowledge.corpus import Document, SourceCorpus, fold
from app.knowledge.ledger import Evidence, EvidenceKind, EvidenceStrength
from app.market.audience_research import (
    FetchedSource,
    FixedURLFetcher,
    LocatedSource,
    SourceTier,
)
from app.runtime.model_session import ModelSession

logger = logging.getLogger("marketingos.market")

ROLE_ID = "material_researcher"
MAX_MATERIAL_URLS = 6
MAX_SYNTHESIS_CHARS = 60_000
MAX_SOURCE_CHARS = 18_000
_MIN_QUOTE_CHARS = 12

# These can contain useful commentary, but they cannot be the official source
# for a product capability or integration.  Rejecting them in code keeps a
# search result or model mistake from silently changing the trust policy.
_NON_OFFICIAL_HOSTS = frozenset(
    {
        "capterra.com",
        "facebook.com",
        "g2.com",
        "linkedin.com",
        "medium.com",
        "reddit.com",
        "twitter.com",
        "x.com",
        "youtube.com",
    }
)


class OfficialSource(BaseModel):
    """An exact page proposed by the locating turn; not evidence yet."""

    url: str
    official_for: str
    reason: str = ""

    @field_validator("url", "official_for", "reason")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()


class _LocatedOfficialSources(BaseModel):
    sources: list[OfficialSource] = Field(default_factory=list)


class MaterialClaim(BaseModel):
    """A claim proposed from fetched text, before quote verification."""

    source_id: str
    kind: EvidenceKind = EvidenceKind.INTEGRATION
    claim: str
    verbatim: str

    @field_validator("source_id", "claim", "verbatim")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()


class _MaterialDraft(BaseModel):
    claims: list[MaterialClaim] = Field(default_factory=list)
    note: str = ""


class MaterialRecovery(BaseModel):
    """Verified sources and evidence that can safely extend one campaign."""

    gap: str
    sources: list[FetchedSource] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    dropped_claims: int = 0
    note: str = ""

    @property
    def recovered(self) -> bool:
        return bool(self.evidence)


_GAP_STOPWORDS = frozenset(
    {
        "about", "account", "after", "before", "click", "current", "does",
        "evidence", "from", "information", "into", "lacks", "needed", "page",
        "reader", "setup", "specific", "supplied", "terms", "that", "their",
        "this", "what", "when", "where", "which", "with", "without",
    }
)


def existing_recovery(
    *, gap: str, artifacts: KnowledgeArtifacts, limit: int = 3
) -> MaterialRecovery | None:
    """Reuse strong official facts recovered by an earlier campaign first."""
    probe = {
        word
        for word in re.findall(r"[a-z0-9]{4,}", fold(gap))
        if word not in _GAP_STOPWORDS
    }
    if not probe:
        return None
    ranked: list[tuple[int, Evidence, set[str]]] = []
    for entry in artifacts.evidence.entries:
        if (
            not re.fullmatch(r"R\d+", entry.id)
            or entry.strength is not EvidenceStrength.STRONG
            or not entry.source.startswith(("https://", "http://"))
        ):
            continue
        words = set(
            re.findall(
                r"[a-z0-9]{4,}",
                fold(f"{entry.claim} {entry.verbatim} {entry.source}"),
            )
        )
        matched = probe & words
        if len(matched) >= min(2, len(probe)):
            ranked.append((len(matched), entry, matched))
    if not ranked:
        return None
    ranked.sort(key=lambda item: (-item[0], item[1].id))
    selected = ranked[:limit]
    covered = set().union(*(matched for _, _, matched in selected))
    if len(covered) / len(probe) < 0.5:
        return None
    return MaterialRecovery(
        gap=gap,
        evidence=[entry for _, entry, _ in selected],
        note="Reused verified official material already present in the knowledge ledger.",
    )


def cited_recovery(*, gap: str, artifacts: KnowledgeArtifacts) -> MaterialRecovery | None:
    """Use exact verified facts cited by a critic to rebuild a weak argument."""
    cited = list(dict.fromkeys(re.findall(r"\bR\d+\b", gap)))[:3]
    evidence = [
        entry
        for evidence_id in cited
        if (entry := artifacts.evidence.get(evidence_id)) is not None
        and entry.strength is EvidenceStrength.STRONG
        and entry.source.startswith(("https://", "http://"))
    ]
    if not evidence:
        return None
    return MaterialRecovery(
        gap=gap,
        evidence=evidence,
        note="Replanned from the critic's exact citation to existing verified material.",
    )


class MaterialResearcher:
    """Locate, fetch, extract and verify official material for one exact gap."""

    def __init__(
        self, session: ModelSession, fetcher: FixedURLFetcher | None = None
    ) -> None:
        self._session = session
        self._fetcher = fetcher or FixedURLFetcher(max_urls=MAX_MATERIAL_URLS)

    async def recover(
        self,
        *,
        gap: str,
        artifacts: KnowledgeArtifacts,
        reader: str,
        request: str,
    ) -> MaterialRecovery:
        located = await self.locate(
            gap=gap,
            artifacts=artifacts,
            reader=reader,
            request=request,
        )
        if not located:
            return MaterialRecovery(gap=gap, note="No official source URL was located.")

        fetched = await self._fetcher.fetch(
            [
                LocatedSource(
                    url=source.url,
                    reason=source.reason,
                    tier=SourceTier.INTERPRETATION,
                    venue=source.official_for,
                )
                for source in located
            ]
        )
        official = [source for source in fetched.sources if _official_host(source.final_url)]
        if not official:
            return MaterialRecovery(
                gap=gap,
                note=(
                    "Located pages could not be fetched as readable official sources"
                    + (f"; {len(fetched.failures)} fetch(es) failed" if fetched.failures else "")
                    + "."
                ),
            )

        draft = await self.synthesise(gap=gap, sources=official)
        return verify_material(
            gap=gap,
            draft=draft,
            fetched=official,
            existing_ids=artifacts.evidence.ids,
        )

    async def locate(
        self,
        *,
        gap: str,
        artifacts: KnowledgeArtifacts,
        reader: str,
        request: str,
    ) -> list[OfficialSource]:
        result = await self._session.structured(
            role=ROLE_ID,
            tier=ModelTier.BALANCED,
            template="material_research_locator",
            variables={
                "company": artifacts.business.company_name or "this company",
                "what_it_does": artifacts.business.what_it_does,
                "category": artifacts.business.category,
                "reader": reader or "the selected reader",
                "campaign_request": request,
                "gap": gap,
                "limit": MAX_MATERIAL_URLS,
            },
            task=(
                "Search now. Return only exact official product, integration or platform "
                "documentation URLs that could establish the missing fact. Do not return "
                "search-result URLs, community posts, social posts, reviews or commentary."
            ),
            schema=_LocatedOfficialSources,
            tools=[ResearchTool.WEB_SEARCH],
        )
        kept: list[OfficialSource] = []
        seen: set[str] = set()
        for source in result.sources:
            if not source.url or not source.official_for or not _official_host(source.url):
                continue
            key = source.url.rstrip("/").lower()
            if key in seen:
                continue
            seen.add(key)
            kept.append(source)
            if len(kept) >= MAX_MATERIAL_URLS:
                break
        return kept

    async def synthesise(
        self, *, gap: str, sources: Sequence[FetchedSource]
    ) -> _MaterialDraft:
        corpus = _render_corpus(sources)
        return await self._session.structured(
            role=ROLE_ID,
            tier=ModelTier.BALANCED,
            template="material_research_synthesis",
            variables={"gap": gap, "corpus": corpus},
            task=(
                "Using only the fetched corpus, extract the smallest set of directly useful "
                "facts that closes the stated gap. Every fact must cite one source id and "
                "copy a verbatim passage from that source."
            ),
            schema=_MaterialDraft,
            tools=[],
        )


def verify_material(
    *,
    gap: str,
    draft: _MaterialDraft,
    fetched: Sequence[FetchedSource],
    existing_ids: set[str] | None = None,
) -> MaterialRecovery:
    """Reject unsupported claims and turn verified quotations into evidence."""

    by_id = {f"S{index}": source for index, source in enumerate(fetched, start=1)}
    used = set(existing_ids or set())
    evidence: list[Evidence] = []
    dropped = 0
    seen: set[tuple[str, str]] = set()

    for proposed in draft.claims:
        source = by_id.get(proposed.source_id)
        quote = proposed.verbatim.strip()
        claim = proposed.claim.strip()
        if (
            source is None
            or not claim
            or len(fold(quote)) < _MIN_QUOTE_CHARS
            or fold(quote) not in fold(source.content)
            or not _official_host(source.final_url)
        ):
            dropped += 1
            continue
        identity = (source.final_url.rstrip("/").lower(), fold(quote))
        if identity in seen:
            continue
        seen.add(identity)
        evidence_id = next_recovery_id(used)
        used.add(evidence_id)
        evidence.append(
            Evidence(
                id=evidence_id,
                kind=proposed.kind,
                claim=claim,
                verbatim=quote,
                source=source.final_url,
                document_id=f"auto:{source.content_hash[:20]}",
                strength=EvidenceStrength.STRONG,
            )
        )

    used_sources = {entry.source.rstrip("/").lower() for entry in evidence}
    return MaterialRecovery(
        gap=gap,
        sources=[
            source
            for source in fetched
            if source.final_url.rstrip("/").lower() in used_sources
        ],
        evidence=evidence,
        dropped_claims=dropped,
        note=draft.note,
    )


def apply_recovery(
    artifacts: KnowledgeArtifacts,
    corpus: SourceCorpus,
    recovery: MaterialRecovery,
) -> tuple[KnowledgeArtifacts, SourceCorpus]:
    """Extend the run's closed world with verified evidence and source text."""

    if not recovery.recovered:
        return artifacts, corpus
    enriched = artifacts.model_copy(deep=True)
    existing = {(entry.source.rstrip("/").lower(), fold(entry.verbatim)) for entry in enriched.evidence.entries}
    for entry in recovery.evidence:
        key = (entry.source.rstrip("/").lower(), fold(entry.verbatim))
        if key not in existing:
            enriched.evidence.entries.append(entry)
            existing.add(key)

    documents = list(corpus.documents)
    contents = {fold(document.content) for document in documents}
    for source in recovery.sources:
        if fold(source.content) in contents:
            continue
        document_id = f"auto:{source.content_hash[:20]}"
        documents.append(
            Document(
                id=document_id,
                title=source.title or source.final_url,
                content=source.content,
                source=source.final_url,
                source_type="website",
            )
        )
        enriched.source_document_ids.append(document_id)
        contents.add(fold(source.content))
    enriched.notes.append(
        f"Automatically recovered {len(recovery.evidence)} verified fact(s) for: {recovery.gap}"
    )
    return enriched, SourceCorpus.from_documents(documents)


def next_recovery_id(existing: set[str]) -> str:
    """Stable id namespace separate from compiler and approved-proof ids."""

    index = 1
    while f"R{index}" in existing:
        index += 1
    return f"R{index}"


def _render_corpus(sources: Sequence[FetchedSource]) -> str:
    parts: list[str] = []
    budget = MAX_SYNTHESIS_CHARS
    for index, source in enumerate(sources, start=1):
        if budget <= 0:
            break
        body = source.content[: min(MAX_SOURCE_CHARS, budget)]
        budget -= len(body)
        parts.append(
            f'<source id="S{index}" official_for="{source.venue}" '
            f'url="{source.final_url}">\n{body}\n</source>'
        )
    return "\n\n".join(parts)


def _official_host(url: str) -> bool:
    try:
        host = (urlsplit(url).hostname or "").lower().rstrip(".")
    except ValueError:
        return False
    if not host:
        return False
    return not any(host == blocked or host.endswith(f".{blocked}") for blocked in _NON_OFFICIAL_HOSTS)
