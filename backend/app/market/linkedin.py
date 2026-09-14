"""Public discovery only. Findings remain unverified leads, never writer evidence.

Two phases, in this order and fixed in code: decide who is worth looking for,
then go and look. They are separate calls because they are separate questions -
"who buys this" is answered from the business's own material and its audience
map, while "who exists" is answered from the open web. Running them as one call
lets a search engine's results decide who the buyer is, which is backwards.
"""
from app.ai.base import ResearchTool
from app.ai.model_router import ModelTier
from app.knowledge.artifacts import KnowledgeArtifacts
from app.market.demand import AudienceSegment
from app.runtime.model_session import ModelSession
from app.schemas.linkedin import (
    CriteriaRequest,
    SearchAnswer,
    SearchRequest,
    SearchResult,
    TargetingCriteria,
)

ROLE_ID = "linkedin_research"
TARGETING_ROLE_ID = "linkedin_targeting"

#: How a mapped audience's own signals are introduced to the targeting call.
#: Labelled rather than bare, because most of them are company-level evidence
#: the prospect finder fetches pages to check - and unlabelled they came back
#: as things a profile search was expected to prove.
_QUALIFYING_SIGNALS = (
    "Signals this audience was qualified by (company-level evidence, not "
    "necessarily readable on a profile)"
)


def render_segment(segment: AudienceSegment | None) -> str:
    """A mapped buyer as prompt text. Only the fields that identify somebody
    from the outside - a segment's internal assessment is a decision about
    whether to write to them, not a way to recognise one.

    `where` is deliberately absent. A segment's gathering places are forums,
    directories and registers: real, useful, and describing a different channel
    entirely. Sent here they came back as targeting criteria - "posts on
    indiehackers.com", "activity on GitHub issues" - which sent a LinkedIn
    profile search hunting Show HN threads and returning nobody.

    `signals` arrives labelled rather than bare, because an audience map writes
    them for the prospect finder, which qualifies *companies* against fetched
    evidence. Most of them are not on anybody's profile, and the next prompt
    has to be able to tell which are.
    """
    if segment is None:
        return ""
    fields = (
        ("Audience", segment.name),
        ("Who they are", segment.who),
        ("Organisation", segment.organization),
        ("Who decides", segment.buyer_role),
        ("Who uses it", segment.user_role),
        ("What it costs them today", "; ".join(segment.pains)),
        (_QUALIFYING_SIGNALS, "; ".join(segment.signals)),
        ("How many exist", segment.population),
    )
    return "\n".join(f"{label}: {value}" for label, value in fields if value)


async def propose_criteria(
    session: ModelSession,
    request: CriteriaRequest,
    artifacts: KnowledgeArtifacts,
    segment: AudienceSegment | None,
) -> TargetingCriteria:
    """What a profile would have to show for this business to be worth a
    message. No web access: this is read out of what we already know."""
    criteria = await session.structured(
        role=TARGETING_ROLE_ID, tier=ModelTier.BALANCED, template="linkedin_criteria",
        variables={
            "target": request.target,
            "hint": request.hint,
            "knowledge": artifacts.render_for_writing(),
            "audience": render_segment(segment),
        },
        task="Propose the targeting criteria. Leave a section empty rather than guessing.",
        schema=TargetingCriteria,
    )
    criteria.basis = (
        f"the audience map ({segment.name})" if segment is not None
        else "the compiled knowledge base"
    )
    return criteria


async def search(session: ModelSession, request: SearchRequest) -> SearchResult:
    criteria = request.criteria
    result = await session.structured(
        role=ROLE_ID, tier=ModelTier.BALANCED,
        template="linkedin_search",
        variables={
            "query": request.query,
            "target": request.target,
            "limit": request.limit,
            "criteria": criteria.render() if criteria is not None else "",
        },
        task="Search the public web now. Return only sourced candidates; fewer or none is fine.",
        schema=SearchAnswer, tools=[ResearchTool.WEB_SEARCH],
    )
    prefix = "/in/" if request.target == "people" else "/company/"
    seen: set[str] = set()
    candidates = []
    for candidate in result.candidates:
        if prefix not in candidate.url or candidate.url.casefold() in seen:
            continue
        seen.add(candidate.url.casefold())
        candidates.append(candidate)
    # The criteria are echoed from the request rather than from the answer: a
    # saved job has to say who it was looking for, and a model that rewrote
    # them in its reply would be reporting a search nobody asked for.
    return SearchResult(candidates=candidates[:request.limit], note=result.note, criteria=criteria)
