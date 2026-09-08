"""Bounded discovery validation: public pages are data, never product truth.

One search-enabled discovery call is followed by at most one closed-corpus
assessment call for the whole map. Transport retries remain ModelSession's job.
"""

import hashlib
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, ValidationError

from app.ai.model_router import ModelTier
from app.knowledge.corpus import fold
from app.market.audience_research import FetchedSource, FixedURLFetcher, LocatedSource
from app.market.capabilities import CapabilityState, ProductCapabilityProfile
from app.market.demand import (
    CARTOGRAPHER_ROLE_ID,
    AudienceSegment,
    DemandMap,
    MapAssessment,
    MapOptions,
    _MapAnswer,
)
from app.runtime.exceptions import ModelRuntimeError
from app.runtime.model_session import ModelSession

MAX_MAP_SOURCE_CHARS = 6_000
MAX_MAP_CORPUS_CHARS = 48_000
MAX_RETAINED_AUDIENCES = 30


def product_fingerprint(profile: ProductCapabilityProfile | None) -> str:
    return hashlib.sha256(
        (profile.model_dump_json() if profile else "unknown").encode()
    ).hexdigest()


def current_map(demand: DemandMap, profile: ProductCapabilityProfile | None) -> DemandMap:
    """An edited product profile invalidates old commercial judgments on read."""
    current = demand.model_copy(deep=True)
    current.segments = unique_audiences(current.segments)
    if not demand.product_fingerprint or demand.product_fingerprint == product_fingerprint(profile):
        return current
    for item in current.segments:
        item.assessment.compatibility = "unknown"
        item.assessment.priority = "hypothesis"
        item.assessment.unknowns.append("Product knowledge changed; refresh this audience's assessment.")
        product_check(item, profile)
        if item.assessment.compatibility == "incompatible":
            item.assessment.priority = "incompatible"
    current.validation_note = "Product profile changed since this map. " + current.validation_note
    return current


#: Why a hand-added audience carries no evidence. Stated on the assessment
#: rather than left to be inferred from an empty list, because "nobody checked"
#: and "somebody checked and found nothing" are opposite readings of the same
#: blank space.
USER_AUDIENCE_REASON = (
    "You described this audience; nothing on the open web has been checked "
    "against it yet. Research it to gather verified sources."
)


def assess_user_audience(
    segment: AudienceSegment, profile: ProductCapabilityProfile | None
) -> AudienceSegment:
    """One hand-written audience, read by exactly the checks a mapped one gets.

    Rebuilt from a clean assessment on every read rather than stored with one,
    so it is idempotent and so an edited product profile shows up the moment it
    is saved rather than at the next remap. A user audience never carries
    fetched evidence, which is why `rank_assessment` can only land it on
    `hypothesis`: naming your buyer is a claim about your intent, not a reading
    of the market. The one thing it can land on is `incompatible` - the product
    check is about what the product does, and the user does not get to overrule
    that by typing.
    """
    assessed = segment.model_copy(
        deep=True,
        update={"added_by": "user", "assessment": MapAssessment(), "fit": 0.0},
    )
    assessed.assessment.reasons.append(USER_AUDIENCE_REASON)
    product_check(assessed, profile)
    rank_assessment(assessed)
    if assessed.assessment.compatibility == "incompatible":
        assessed.assessment.priority = "incompatible"
    assessed.assessment.reasons = list(dict.fromkeys(assessed.assessment.reasons))
    assessed.assessment.unknowns = list(dict.fromkeys(assessed.assessment.unknowns))
    return assessed


def merge_user_audiences(
    demand: DemandMap,
    audiences: list[AudienceSegment],
    profile: ProductCapabilityProfile | None,
) -> DemandMap:
    """The compiled map with the user's own audiences in front of it.

    In front, and that is the whole of it: `unique_audiences` and
    `admission_for` both resolve a collision in favour of whichever segment
    came first, so putting the user's ahead of the cartographer's makes a
    discovered near-duplicate the one that gets flagged. On the subject of
    their own buyer the user is the authority - the same rule the rival list
    follows when a scan re-proposes something the user already muted.

    Merged on read rather than written into the map payload because the two
    have different lifetimes: a map is a compiled reading of one moment and a
    refresh replaces it wholesale, while these must survive every remap.
    """
    if not audiences:
        return demand
    assessed = [assess_user_audience(item, profile) for item in audiences]
    mine = {fold(item.name) for item in assessed}
    merged = demand.model_copy(deep=True)
    merged.segments = unique_audiences(
        assessed + [item for item in merged.segments if fold(item.name) not in mine]
    )
    return merged


class CandidateAssessment(BaseModel):
    candidate_id: int = Field(ge=0)
    assessment: MapAssessment
    duplicate_of: int | None = Field(default=None, ge=0)


class AssessedMap(BaseModel):
    candidates: list[CandidateAssessment] = Field(default_factory=list)


def identity(segment: AudienceSegment) -> str:
    """Structured situation first; names remain the stable legacy fallback."""
    parts = [segment.organization, segment.workflow, segment.need]
    return fold(" | ".join(parts)) if all(p.strip() for p in parts) else fold(segment.name)


def unique_audiences(segments: list[AudienceSegment]) -> list[AudienceSegment]:
    """Keep the first result for each name or exact structured situation."""
    names: set[str] = set()
    situations: set[str] = set()
    result: list[AudienceSegment] = []
    for segment in segments:
        name, situation = fold(segment.name), identity(segment)
        if not name or name in names or situation in situations:
            continue
        names.add(name)
        situations.add(situation)
        result.append(segment)
    return result


def product_check(
    segment: AudienceSegment, profile: ProductCapabilityProfile | None
) -> None:
    assessment = segment.assessment
    required = segment.definition.required_product_capabilities
    unsupported = [
        key for key in required
        if profile and profile.state_of(key) is CapabilityState.UNSUPPORTED
    ]
    unknown = [
        key for key in required
        if profile is None or profile.state_of(key) is CapabilityState.UNKNOWN
    ]
    if unsupported:
        assessment.compatibility = "incompatible"
        assessment.reasons.append("Required capabilities are unsupported: " + ", ".join(unsupported))
    elif unknown or not required or profile is None:
        if assessment.compatibility != "incompatible":
            assessment.compatibility = "unknown"
        assessment.unknowns.append(
            "Product support needs verification: " + (", ".join(unknown) or "no verified requirement mapping")
        )


def rank_assessment(segment: AudienceSegment) -> None:
    assessment = segment.assessment
    needs = [item for item in assessment.evidence if item.kind == "need"]
    domains = {(urlsplit(item.url).hostname or "").removeprefix("www.") for item in needs}
    assessment.evidence_strength = (
        "supported" if len(domains) >= 2 else "limited" if needs else "absent"
    )
    reachable = any(item.kind in {"access", "example"} for item in assessment.evidence)
    counterevidence = any(item.kind == "counterevidence" for item in assessment.evidence)
    if assessment.compatibility == "incompatible":
        assessment.priority = "incompatible"
    elif (
        assessment.compatibility == "supported"
        and assessment.evidence_strength == "supported"
        and reachable
        and not counterevidence
        and segment.admission().researchable
    ):
        assessment.priority = "explore_first"
    else:
        assessment.priority = "hypothesis"
    if not reachable:
        assessment.unknowns.append("No verified venue or example establishes findability yet.")
    if counterevidence:
        assessment.unknowns.append("Review the counterevidence before prioritising this audience.")


async def validate_map(
    session: ModelSession,
    answer: _MapAnswer,
    profile: ProductCapabilityProfile | None,
    options: MapOptions,
    previous: DemandMap | None,
    limit: int,
    progress: Callable[[str], None],
    *,
    fetcher: FixedURLFetcher | None = None,
) -> DemandMap:
    candidates: list[AudienceSegment] = []
    profile_fingerprint = product_fingerprint(profile)
    seen: set[str] = set()
    seen_names: set[str] = set()
    same_scope = previous is not None and (
        options.model_dump(exclude={"mode"}) == previous.options.model_dump(exclude={"mode"})
    )
    previous_names = {identity(item): item.name for item in previous.segments} if same_scope else {}
    for item in unique_audiences(answer.segments):
        if not item.name.strip() or identity(item) in seen:
            continue
        seen.add(identity(item))
        # A discovery model cannot certify its own evidence or compatibility.
        name = previous_names.get(identity(item), item.name.strip())
        if fold(name) in seen_names:
            name = f"{name} — {item.workflow or item.need or len(candidates) + 1}"
        seen_names.add(fold(name))
        candidates.append(item.model_copy(deep=True, update={
            "name": name, "assessment": MapAssessment(), "fit": 0.0,
        }))
        if len(candidates) >= limit:
            break

    note = "No sources were verified; candidates remain hypotheses."
    located = [LocatedSource(url=url) for url in answer.source_urls]
    cache: list[dict] = []
    if candidates and located:
        progress("Fetching up to 10 exact URLs; validating against at most 48,000 characters")
        cached: list[FetchedSource] = []
        if previous and options.mode == "explore":
            for payload in previous.source_cache[:10]:
                try:
                    source = FetchedSource.model_validate(payload)
                except ValidationError:
                    continue
                stamp = source.fetched_at.replace(tzinfo=UTC) if source.fetched_at.tzinfo is None else source.fetched_at
                if datetime.now(UTC) - timedelta(days=7) <= stamp <= datetime.now(UTC):
                    cached.append(source)
        located = located[:10]
        cached = [s for s in cached if any(p.url in {s.requested_url, s.final_url} for p in located)]
        cached_urls = {url for s in cached for url in (s.requested_url, s.final_url)}
        fetched = await (fetcher or FixedURLFetcher()).fetch(
            [item for item in located if item.url not in cached_urls]
        )
        sources = {}
        hashes: set[str] = set()
        budget = MAX_MAP_CORPUS_CHARS
        for source in [*cached, *fetched.sources]:
            if budget <= 0:
                break
            content = source.content[:min(MAX_MAP_SOURCE_CHARS, budget)]
            digest = hashlib.sha256(fold(content).encode()).hexdigest()
            if digest in hashes:
                continue
            hashes.add(digest)
            budget -= len(content)
            sources[source.final_url] = source.model_copy(update={"content": content})
        cache = [source.model_dump(mode="json") for source in sources.values()]
        if sources:
            progress(f"Evaluating candidates against {len(sources)} fetched pages (stage 2 of 2)")
            try:
                assessed = await session.structured(
                    role=CARTOGRAPHER_ROLE_ID,
                    tier=ModelTier.DEEP,
                    template="audience_map_validate",
                    variables={
                        "candidates": "\n".join(
                            f"Candidate {i}: {item.model_dump_json()}"
                            for i, item in enumerate(candidates)
                        ),
                        "capabilities": profile.model_dump_json() if profile else "Unknown",
                        "scope": options.model_dump_json(),
                        "corpus": "\n\n".join(
                            f"URL: {url}\n{source.content}" for url, source in sources.items()
                        ),
                    },
                    task="Assess each candidate using only these sources; cite exact URLs and quotations.",
                    schema=AssessedMap,
                    tools=[],
                )
                processed: set[int] = set()
                duplicates: set[int] = set()
                for result in assessed.candidates:
                    index = result.candidate_id
                    if index >= len(candidates) or index in processed:
                        continue
                    processed.add(index)
                    assessment = result.assessment
                    verified = []
                    evidence_keys: set[tuple[str, str, str]] = set()
                    for evidence in assessment.evidence:
                        source = sources.get(evidence.url)
                        key = (evidence.url, fold(evidence.quote), evidence.kind)
                        if key in evidence_keys:
                            continue
                        if (
                            source and len(fold(evidence.quote)) >= 12
                            and fold(evidence.quote) in fold(source.content)
                        ):
                            verified.append(evidence.model_copy(update={"fetched_at": source.fetched_at}))
                            evidence_keys.add(key)
                    dropped = len(assessment.evidence) - len(verified)
                    assessment.evidence = verified
                    if dropped:
                        assessment.unknowns.append(f"{dropped} unsupported or duplicate quotation(s) discarded.")
                    candidates[index].assessment = assessment
                    # Duplicate judgments only flag rows. The user can inspect them;
                    # a model's guess must not silently erase a distinct buyer.
                    if result.duplicate_of is not None and result.duplicate_of < index:
                        duplicates.add(index)
                        assessment.unknowns.append(
                            "Possible overlap with " + candidates[result.duplicate_of].name
                        )
                note = (
                    f"Checked {len(sources)} pages; {len(fetched.failures)} fetch failure(s). "
                    "Quotes are source-verified; interpretations and purchase intent are hypotheses."
                )
                for index, item in enumerate(candidates):
                    if index not in processed:
                        item.assessment.unknowns.append("The validation response omitted this candidate.")
                    product_check(item, profile)
                    rank_assessment(item)
                    if index in duplicates and item.assessment.priority == "explore_first":
                        item.assessment.priority = "hypothesis"
            except ModelRuntimeError:
                note = "Source assessment failed. Discovered candidates were saved as unverified hypotheses."
        else:
            note = "None of the located pages could be read. This does not establish an absence of demand."

    for item in candidates:
        product_check(item, profile)
        if item.assessment.compatibility == "incompatible":
            item.assessment.priority = "incompatible"
        item.assessment.reasons = list(dict.fromkeys(item.assessment.reasons))
        item.assessment.unknowns = list(dict.fromkeys(item.assessment.unknowns))

    # Exploration appends new hypotheses without losing the audience names used
    # by research, prospect decisions and existing campaigns. Scope changes start
    # a separate map so out-of-scope audiences cannot leak into the new results.
    if previous and same_scope and options.mode == "explore":
        retained = [item.model_copy(deep=True) for item in unique_audiences(previous.segments)]
        previous_keys = {identity(item) for item in retained}
        previous_labels = {fold(item.name) for item in retained}
        if previous.product_fingerprint != profile_fingerprint:
            for item in retained:
                item.assessment.compatibility = "unknown"
                item.assessment.priority = "hypothesis"
                item.assessment.unknowns.append("Product knowledge changed; refresh this audience's assessment.")
                product_check(item, profile)
                if item.assessment.compatibility == "incompatible":
                    item.assessment.priority = "incompatible"
        additions = [
            item for item in candidates
            if identity(item) not in previous_keys and fold(item.name) not in previous_labels
        ]
        room = max(0, MAX_RETAINED_AUDIENCES - len(retained))
        candidates = retained + additions[:room]
        if len(additions) > room:
            note += " Map capacity reached (30); refresh to consolidate the audiences."
    return DemandMap(
        segments=unique_audiences(candidates), options=options, validation_note=note,
        searched=answer.searched, reading=answer.reading, note=answer.note,
        source_cache=cache, product_fingerprint=profile_fingerprint,
    )
