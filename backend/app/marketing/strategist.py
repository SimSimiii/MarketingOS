"""The Strategist: one act of synthesis, on the strongest model available.

This replaces four agents - research, audience, competitor, strategy - and the
replacement is a merge, not a rename. Those four ran in sequence on the cheap
tier, each seeing a fragment of what the others had produced, each emitting a
list of strings. Strategy is the synthesis of audience, market, competition
and product; splitting one act of judgment across four shallow passes produced
four shallow artifacts and called it a pipeline.

By the time this runs, the facts are already gathered and cited. There is
nothing left to research. What is left is the hardest decision in the campaign
- what to say, to whom, in what order - and it gets one deliberation with
everything in front of it.
"""

import logging
import re

from app.ai.model_router import ModelTier
from app.knowledge.artifacts import KnowledgeArtifacts
from app.knowledge.base import build_knowledge_base
from app.knowledge.corpus import SourceCorpus
from app.market.demand import DemandMap
from app.market.positioning import PositioningMap
from app.marketing.briefs import CampaignBrief, EmailBrief
from app.marketing.contract import DeliverableContract
from app.marketing.exceptions import StrategyError
from app.marketing.preflight import assess
from app.marketing.request import CampaignRequest
from app.runtime.model_session import ModelSession

logger = logging.getLogger("marketingos.marketing")

ROLE_ID = "strategist"

#: Retrieval budget for the one question the artifacts cannot anticipate: what
#: this particular request is about. A launch campaign and an onboarding
#: campaign need different corners of the same corpus.
_RETRIEVAL_CHUNKS = 6

#: Facts one email may be assigned. The brief is read by the writer as "this is
#: what this email is built on", and the critic asks afterwards whether the
#: assigned evidence was spent - so a brief that assigns six facts is a brief
#: that asks for six facts on the page, and gets a product page. Three is where
#: a second fact still supports the one idea and a fourth starts arguing its
#: own. Trimmed here rather than requested in the prompt because it is a
#: number, and a number has a correct answer.
MAX_EVIDENCE_PER_EMAIL = 3

#: Other claims one email slot may carry into the bake-off. Three, because the
#: bake-off drafts at most four candidates and the first of them argues the
#: idea the strategist actually chose. Trimmed here rather than asked for in
#: the prompt, for the same reason the evidence list is: it is a number.
MAX_ALTERNATIVE_IDEAS = 3


class Strategist:
    def __init__(self, session: ModelSession) -> None:
        self._session = session

    async def build(
        self,
        *,
        request: CampaignRequest,
        artifacts: KnowledgeArtifacts,
        corpus: SourceCorpus,
        contract: DeliverableContract,
        prior_learnings: str = "",
        positioning: PositioningMap | None = None,
        demand: DemandMap | None = None,
        chosen_segment: str = "",
    ) -> CampaignBrief:
        variables = {
            "request": request.request,
            "campaign_context": request.render_context(),
            "knowledge": artifacts.render_for_strategy(),
            # The shape of what exists, above the facts themselves. A hundred
            # undifferentiated entries answer "what is true" and hide "what
            # can this campaign argue from at all" - and the second question
            # is the one being asked here. An empty shelf is the most useful
            # line in it: it is why an obvious angle is off the table.
            "knowledge_map": build_knowledge_base(artifacts).render_map(),
            "proof_posture": assess(artifacts).render_for_strategy(),
            # What the material cannot contain: which of this company's
            # claims every competitor also makes. Absent, the strategist
            # is told so plainly rather than left to assume the field is
            # empty - see PositioningMap.render_for_strategy.
            "positioning": (
                positioning or PositioningMap()
            ).render_for_strategy(),
            # Who the market says would buy this, and which of them this
            # campaign was pointed at. The chosen segment is already the
            # primary one in `knowledge` above - this is the field of buyers
            # it was chosen *out of*, which is what turns a target into a
            # decision the strategist can reason about instead of an
            # instruction it can only obey.
            "demand": (demand or DemandMap()).render_for_strategy(chosen_segment),
            "contract": contract.render(),
            "relevant_material": corpus.render_search(
                f"{request.request} {request.product_description}", _RETRIEVAL_CHUNKS
            ),
            "prior_learnings": prior_learnings or "This is the first campaign for this business.",
        }
        brief = await self._session.structured(
            role=ROLE_ID,
            tier=ModelTier.DEEP,
            template="strategist",
            variables=variables,
            task=(
                "Decide what this campaign says, to whom, and in what order. Write the brief "
                "for every email before any of them is written."
            ),
            schema=CampaignBrief,
        )
        brief = self._normalize(brief, contract, artifacts)

        if contract.count_is_explicit and len(brief.emails) != contract.count:
            # One correction turn: the count is arithmetic, and a brief that
            # got it wrong is wrong about the only part of the request that
            # was never open to interpretation.
            logger.info(
                "strategist: planned %d emails against a contract of %d - correcting",
                len(brief.emails),
                contract.count,
            )
            brief = await self._session.structured(
                role=ROLE_ID,
                tier=ModelTier.DEEP,
                template="strategist",
                variables=variables,
                task=(
                    f"Your brief planned {len(brief.emails)} emails. The user asked for exactly "
                    f"{contract.count}. Rebuild the sequence with exactly {contract.count} "
                    "emails - not by padding or truncating what you had, but by redesigning the "
                    "arc so that many emails each carry a distinct idea worth sending."
                ),
                schema=CampaignBrief,
            )
            brief = self._normalize(brief, contract, artifacts)

        if not brief.emails:
            raise StrategyError(
                "The strategist produced no email briefs - there is nothing to write.",
                request=request.request,
            )
        brief.contract = contract
        return brief

    # ------------------------------------------------------------- internals

    def _normalize(
        self,
        brief: CampaignBrief,
        contract: DeliverableContract,
        artifacts: KnowledgeArtifacts,
    ) -> CampaignBrief:
        """Fix in code everything about a brief that has a correct answer.

        Positions must be 1..n in order, evidence ids must exist, a fact one
        email spends is not there for the next one to spend again, and the
        "already spent" list is derivable from the briefs before it - asking a
        model to keep those consistent is asking it to do bookkeeping instead
        of thinking.
        """
        segment = artifacts.audience.match(brief.reader_segment, brief.reader)
        if segment is not None:
            # Store it back exactly as the audience model spells it, so the
            # cold reader is looked up by identity rather than matched again.
            brief.reader_segment = segment.name
        elif artifacts.audience.segments:
            logger.info(
                "strategist: reader segment %r matches no segment in the audience model",
                brief.reader_segment,
            )
            brief.reader_segment = ""

        emails = brief.emails[: contract.count] if contract.count_is_explicit else brief.emails
        known_evidence = artifacts.evidence.ids
        cta_labels = {cta.label.lower() for cta in artifacts.offer.calls_to_action}

        normalized: list[EmailBrief] = []
        spent: list[str] = []
        spent_evidence: set[str] = set()
        for position, email in enumerate(emails, start=1):
            unknown = [id_ for id_ in email.evidence_ids if id_ not in known_evidence]
            if unknown:
                logger.info("strategist: dropped unknown evidence ids %s", unknown)
            assigned = [id_ for id_ in email.evidence_ids if id_ in known_evidence]
            # Evidence is finite, and prompts/strategist.md asks for it to be
            # spent that way - "an id that is the backbone of one email should
            # not be the backbone of another". Nothing checked, and the failure
            # it leaves is invisible to every gate in the loop: five emails
            # arguing from one testimonial repeat no phrase, so `overlap_gate`
            # passes each of them, and the sequence still reads as one email
            # sent five times. Which fact belongs to which slot is bookkeeping
            # over a set, so it is settled here rather than asked for.
            fresh = [id_ for id_ in assigned if id_ not in spent_evidence]
            if fresh and fresh != assigned:
                logger.info(
                    "strategist: email %d re-assigned %s, already spent earlier - dropped",
                    position,
                    [id_ for id_ in assigned if id_ in spent_evidence],
                )
                assigned = fresh
            elif assigned and not fresh:
                # Every fact it asked for is gone. A business with two proofs
                # and a five-email sequence is the ordinary case, not an error,
                # and an email with nothing assigned is written from mechanism
                # with no proof to spend - which is strictly worse than one
                # arguing from a fact the reader has seen before.
                logger.info(
                    "strategist: email %d has only facts earlier emails spent - kept, because "
                    "nothing assigned is worse than something repeated",
                    position,
                )
            if len(assigned) > MAX_EVIDENCE_PER_EMAIL:
                # Kept in the strategist's own order: it ranked them, and the
                # first ones are the proof it built the idea on.
                logger.info(
                    "strategist: email %d was assigned %d facts - keeping the first %d",
                    position,
                    len(assigned),
                    MAX_EVIDENCE_PER_EMAIL,
                )
                assigned = assigned[:MAX_EVIDENCE_PER_EMAIL]
            email = email.model_copy(
                update={
                    "position": position,
                    "evidence_ids": assigned,
                    "must_not_reuse": list(spent),
                    "alternative_ideas": _distinct_ideas(
                        email.alternative_ideas, email.single_idea
                    )[:MAX_ALTERNATIVE_IDEAS],
                }
            )
            if cta_labels and email.call_to_action and email.call_to_action.lower() not in cta_labels:
                # Not fatal: the strategist may legitimately phrase an existing
                # action differently. Worth knowing when a run's CTAs drift.
                logger.info(
                    "strategist: call to action %r is not on the offer sheet", email.call_to_action
                )
            normalized.append(email)
            if email.single_idea:
                spent.append(email.single_idea)
            spent_evidence.update(assigned)

        brief.emails = normalized
        return brief


def _distinct_ideas(alternatives: list[str], chosen: str) -> list[str]:
    """The alternatives that are actually alternatives.

    An alternative that restates `single_idea` costs a whole draft and a cold
    read to discover that it was the same bet, which is the one thing a
    bake-off must never spend money on. Compared on significant words rather
    than exactly, because "your script costs more than you think" and "the
    in-house script costs more than you think" are one idea.
    """
    seen = [_idea_key(chosen)] if chosen else []
    kept: list[str] = []
    for idea in alternatives:
        key = _idea_key(idea)
        if not key or any(_too_close(key, earlier) for earlier in seen):
            continue
        seen.append(key)
        kept.append(idea.strip())
    return kept


def _idea_key(idea: str) -> frozenset[str]:
    return frozenset(word for word in re.findall(r"[a-z]{4,}", idea.lower()))


def _too_close(left: frozenset[str], right: frozenset[str]) -> bool:
    if not left or not right:
        return False
    return len(left & right) * 2 >= min(len(left), len(right))
