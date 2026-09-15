"""Bounded discovery validation: public pages are data, never product truth.

One search-enabled discovery call is followed by at most one closed-corpus
assessment call for the whole map. Transport retries remain ModelSession's job.
"""

import hashlib
import re
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, ValidationError

from app.ai.base import ResearchTool
from app.ai.model_router import ModelTier
from app.knowledge.artifacts import Grounding
from app.knowledge.corpus import fold
from app.market.audience_research import (
    AudienceResearch,
    FetchedSource,
    FixedURLFetcher,
    LocatedSource,
    SourceTier,
    bounded_sources,
)
from app.market.capabilities import CapabilityState, ProductCapabilityProfile
from app.market.demand import (
    CARTOGRAPHER_ROLE_ID,
    AudienceSegment,
    DemandMap,
    MapAssessment,
    MapEvidence,
    MapOptions,
    _MapAnswer,
    audience_fingerprint,
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
    changed = bool(demand.product_fingerprint and demand.product_fingerprint != product_fingerprint(profile))
    for item in current.segments:
        product_check(item, profile)
        rank_assessment(item)
    if changed:
        current.validation_note = "Product profile changed; compatibility rechecked. " + current.validation_note
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


#: Which map evidence kind each half of a research artifact answers. Research
#: asks its questions in the audience's own terms and the map asks them in
#: commercial ones, but the underlying claim is the same: a verified problem is
#: a need, the tool they use instead is an alternative, and a venue populated
#: with them is access.
_RESEARCH_EVIDENCE_KINDS = {
    "problems": "need",
    "buyer_phrases": "need",
    "incumbent_behaviour": "alternative",
    "where": "access",
}


def evidence_from_research(research: AudienceResearch) -> list[MapEvidence]:
    """Verified research findings, in the shape the map already ranks.

    Research quotations are checked against the fetched page before the row is
    written, so they arrive here at least as well established as anything
    `validate_map` produced - they were simply written into a different table
    and never read back.

    Only grounded findings cross over. An inferred one is the researcher's
    reasoning about the corpus, which is worth reading and is not a source.
    """
    by_id = {source.id: source for source in research.sources}
    found: list[MapEvidence] = []
    seen: set[tuple[str, str, str]] = set()

    def collect(claim: str, kind: str, references: list) -> None:
        for reference in references:
            source = by_id.get(reference.source_id)
            if source is None or not reference.quote.strip() or not claim.strip():
                continue
            if kind == "need" and source.tier is not SourceTier.BUYER_VOICE:
                continue
            key = (source.final_url, fold(reference.quote), kind)
            if key in seen:
                continue
            seen.add(key)
            found.append(
                MapEvidence(
                    claim=claim,
                    quote=reference.quote,
                    url=source.final_url,
                    kind=kind,
                    fetched_at=source.fetched_at,
                )
            )

    for problem in research.problems:
        if problem.grounding is Grounding.GROUNDED:
            collect(problem.statement, _RESEARCH_EVIDENCE_KINDS["problems"], problem.evidence)
    # A buyer phrase carries no grounding of its own because it cannot be
    # inferred: it is the buyer's words or it is not recorded.
    for phrase in research.buyer_phrases:
        collect(phrase.text, _RESEARCH_EVIDENCE_KINDS["buyer_phrases"], [phrase.evidence])
    for behaviour in research.incumbent_behaviour:
        if behaviour.grounding is Grounding.GROUNDED:
            collect(
                behaviour.text,
                _RESEARCH_EVIDENCE_KINDS["incumbent_behaviour"],
                behaviour.evidence,
            )
    for venue in research.where:
        if venue.grounding is Grounding.GROUNDED:
            collect(venue.text, _RESEARCH_EVIDENCE_KINDS["where"], venue.evidence)
    return found


def merge_research_evidence(
    demand: DemandMap,
    researches: dict[str, AudienceResearch],
    profile: ProductCapabilityProfile | None,
) -> DemandMap:
    """Reuse verified findings only while the researched situation still matches."""
    if not researches:
        return demand
    merged = demand.model_copy(deep=True)
    for segment in merged.segments:
        research = researches.get(fold(segment.name))
        if research is None:
            continue
        assessment = segment.assessment
        if research.audience_fingerprint != audience_fingerprint(segment):
            assessment.unknowns.append(
                "Stored research belongs to a different or unverified audience definition; research again."
            )
            assessment.unknowns = list(dict.fromkeys(assessment.unknowns))
            continue
        present = {
            (item.url, fold(item.quote), item.kind) for item in assessment.evidence
        }
        assessment.evidence.extend(
            item
            for item in evidence_from_research(research)
            if (item.url, fold(item.quote), item.kind) not in present
        )
        assessment.reasons = [item for item in assessment.reasons
                              if not item.startswith("Re-ranked on ")]
        if assessment.evidence:
            assessment.reasons = [item for item in assessment.reasons if item != USER_AUDIENCE_REASON]
            assessment.reasons.append(
                f"Re-ranked on matching researched sources ({len(research.sources)} fetched)."
            )
        product_check(segment, profile)
        rank_assessment(segment)
        if assessment.compatibility == "incompatible":
            assessment.priority = "incompatible"
        assessment.reasons = list(dict.fromkeys(assessment.reasons))
        assessment.unknowns = list(dict.fromkeys(assessment.unknowns))
    return merged


class CandidateAssessment(BaseModel):
    candidate_id: int = Field(ge=0)
    assessment: MapAssessment
    duplicate_of: int | None = Field(default=None, ge=0)


class _LocatedMapSources(BaseModel):
    source_urls: list[str] = Field(default_factory=list, max_length=20)


async def recover_sources(
    session: ModelSession, answer: _MapAnswer, candidates: list[AudienceSegment],
    options: MapOptions,
) -> list[str]:
    """Reuse literal URLs, then make at most one fresh search if reporting failed.

    Model calls have no shared browsing memory. The fallback must search, not
    reconstruct paths from a summary. All returned pages still pass the fetch
    and quotation checks below.
    """
    # Parse the text fields directly: JSON escapes must never enter a URL.
    literal = re.findall(r"https?://[^\s<>\"\[\]]+", "\n".join([
        answer.reading, answer.note, *answer.searched,
        *(text for item in candidates for text in [item.basis, *item.where, *item.signals]),
    ]))
    located = bounded_sources([
        LocatedSource(url=url.rstrip(".,;:!?)")) for url in literal
    ])
    if located:
        return [item.url for item in located]
    if not (answer.reading.strip() or answer.searched):
        return []
    try:
        located = await session.structured(
            role=CARTOGRAPHER_ROLE_ID,
            tier=ModelTier.BALANCED,
            template="audience_map_sources",
            variables={
                "searched": "\n".join(f"- {query}" for query in answer.searched)
                or "No queries were reported.",
                "reading": answer.reading or "No reading was reported.",
                "note": answer.note or "No coverage gaps were reported.",
                "scope": options.model_dump_json(),
                "candidates": "\n".join(
                    f"- {item.name}: {item.organization} | {item.workflow} | {item.need}"
                    for item in candidates
                ),
            },
            task="Search now for source pages supporting or challenging these hypotheses; return exact URLs.",
            schema=_LocatedMapSources,
            tools=[ResearchTool.WEB_SEARCH],
        )
    except ModelRuntimeError:
        return []
    return [item.url for item in bounded_sources([
        LocatedSource(url=url) for url in located.source_urls
    ])]


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


#: Said when the candidate named no product requirement at all, or when there
#: is no profile to check one against. Distinct from the message below because
#: they are opposite situations wearing the same word: here nobody has stated
#: what the audience would need, there somebody did and the product has not
#: established it.
NO_REQUIREMENT_MAPPED = (
    "No product requirement is mapped for this audience, so compatibility is unchecked "
    "rather than doubtful."
)


def product_check(
    segment: AudienceSegment, profile: ProductCapabilityProfile | None
) -> None:
    """Deterministic product fit, from the capability profile alone.

    Positive support is settled here rather than left to the validation model,
    which is the only reason `supported` can ever be reached: the discovery
    pass is reading the market, and whether this product does the thing is a
    fact about the product that Python already holds.
    """
    assessment = segment.assessment
    assessment.reasons = [item for item in assessment.reasons
                          if not item.startswith("Required capabilities are unsupported:")]
    assessment.unknowns = [item for item in assessment.unknowns
                          if not item.startswith("Product support needs verification:")
                          and item not in {NO_REQUIREMENT_MAPPED,
                                           "Product knowledge changed; refresh this audience's assessment."}]
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
        return
    if profile is None or not required:
        assessment.compatibility = "unknown"
        assessment.unknowns.append(NO_REQUIREMENT_MAPPED)
        return
    if unknown:
        assessment.compatibility = "unknown"
        assessment.unknowns.append("Product support needs verification: " + ", ".join(unknown))
        return
    assessment.compatibility = "supported"


def rank_assessment(segment: AudienceSegment) -> None:
    """Rank research opportunities; material or unassessed objections need review.

    Only explicit unsupported product requirements exclude a segment. Impact
    labels are judgments, so they route a candidate to review rather than
    turning a contrary source into a deterministic product limitation.
    """
    assessment = segment.assessment
    needs = []
    quotes: set[str] = set()
    for item in assessment.evidence:
        if item.kind == "need" and fold(item.quote) not in quotes:
            quotes.add(fold(item.quote))
            needs.append(item)
    domains = {(urlsplit(item.url).hostname or "").removeprefix("www.") for item in needs} - {""}
    assessment.evidence_strength = (
        "supported" if len(domains) >= 2 else "limited" if needs else "absent"
    )
    reachable = any(item.kind in {"access", "example"} for item in assessment.evidence)
    assessment.findability = "verified" if reachable else "unknown"
    contrary = [item for item in assessment.evidence if item.kind == "counterevidence"]
    assessment.counterevidence = len({item.url for item in contrary})
    review = any(item.impact != "minor" or not item.impact_reason.strip() for item in contrary)
    if assessment.compatibility == "incompatible":
        assessment.priority = "incompatible"
    elif (
        assessment.evidence_strength == "supported"
        and reachable
        and segment.admission().researchable
    ):
        assessment.priority = "review_first" if review else "explore_first"
    else:
        assessment.priority = "hypothesis"
    assessment.unknowns = [item for item in assessment.unknowns if item not in {
        "No verified venue or example establishes findability yet.",
        "Review the counterevidence before prioritising this audience.",
    }]
    if not reachable:
        assessment.unknowns.append("No verified venue or example establishes findability yet.")
    if assessment.counterevidence:
        assessment.unknowns.append("Review the counterevidence before prioritising this audience.")
    assessment.unknowns = list(dict.fromkeys(assessment.unknowns))


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
    urls = [item.url for item in bounded_sources([
        LocatedSource(url=url) for url in answer.source_urls
    ])]
    if candidates and not urls:
        progress("Recovering source links; one bounded web search if no literal URLs were reported")
        urls = await recover_sources(session, answer, candidates, options)
        if not urls:
            note = (
                "No usable source URLs were reported or recovered, "
                "so nothing was verified; candidates remain hypotheses."
            )
    located = [LocatedSource(url=url) for url in urls]
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
