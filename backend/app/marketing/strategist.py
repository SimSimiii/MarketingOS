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
from app.knowledge.artifacts import Grounding, KnowledgeArtifacts
from app.knowledge.base import build_knowledge_base
from app.knowledge.corpus import SourceCorpus
from app.knowledge.ledger import EvidenceLedger
from app.market.demand import DemandMap
from app.market.material_research import MaterialRecovery
from app.market.positioning import PositioningMap
from app.marketing.briefs import ArgumentOption, CampaignBrief, EmailBrief
from app.marketing.contract import DeliverableContract
from app.marketing.exceptions import StrategyError
from app.marketing.intelligence import CampaignIntelligence
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

#: One second, complete commercial proposition. Two real bets are enough to
#: discover whether the Strategist chose the wrong ground; more buys another
#: full draft and reader panel before either bet is refined.
MAX_ALTERNATIVE_ARGUMENTS = 1


def _render_recovery(
    recovery: MaterialRecovery | None, artifacts: KnowledgeArtifacts
) -> str:
    persisted = [
        entry
        for entry in artifacts.evidence.entries
        if re.fullmatch(r"R\d+", entry.id)
    ]
    if recovery is None or not recovery.recovered:
        if not persisted:
            return ""
        lines = [
            (
                "Earlier automatic recovery passes quotation-verified these official facts. "
                "They are available when relevant; do not force them into an unrelated "
                "campaign:"
            ),
        ]
        lines.extend(
            f"- [{entry.id}] {entry.claim} (official source: {entry.source})"
            for entry in persisted
        )
        return "\n".join(lines)
    lines = [
        "The previous craft pass diagnosed this exact strategy or material gap:",
        recovery.gap,
        "",
        "The system then found and quotation-verified these official facts:",
    ]
    lines.extend(
        f"- [{entry.id}] {entry.claim} (official source: {entry.source})"
        for entry in recovery.evidence
    )
    other = [entry for entry in persisted if entry.id not in {e.id for e in recovery.evidence}]
    if other:
        lines.append("")
        lines.append("Other official facts recovered earlier remain available when useful:")
        lines.extend(
            f"- [{entry.id}] {entry.claim} (official source: {entry.source})"
            for entry in other
        )
    lines.extend(
        [
            "",
            (
                "This is corrective material, not optional background. Rebuild at least one "
                "primary email around a recovered id and assign that id in evidence_ids. If an "
                "official source page lets the reader answer the diagnosed question before "
                "signup, put its exact URL in call_to_action and explain the decision it enables "
                "in the next-step fields. Do not claim that the page proves anything outside "
                "its quoted fact."
            ),
        ]
    )
    return "\n".join(lines)


def _spends_any(brief: CampaignBrief, evidence_ids: set[str]) -> bool:
    return any(evidence_ids.intersection(email.evidence_ids) for email in brief.emails)


def _recovered_next_step(
    *,
    artifacts: KnowledgeArtifacts,
    evidence_ids: list[str],
    next_step_evidence_ids: list[str],
    call_to_action: str,
    next_step_value: str,
) -> tuple[str, str]:
    """Tie an automatically recovered payoff to its exact official page."""
    ordered = list(dict.fromkeys([*next_step_evidence_ids, *evidence_ids]))
    entry = next(
        (
            found
            for evidence_id in ordered
            if evidence_id.startswith("R")
            and (found := artifacts.evidence.get(evidence_id)) is not None
            and found.source.startswith(("https://", "http://"))
        ),
        None,
    )
    if entry is None:
        return call_to_action, next_step_value
    urls = {
        url.rstrip(".,;:)")
        for url in re.findall(r'https?://[^\s<>"\]]+', call_to_action)
    }
    if urls == {entry.source}:
        return call_to_action, next_step_value
    return (
        f"Review the official documentation: {entry.source}",
        f"The official page documents this verified fact: {entry.claim}",
    )


_SOURCE_TOKEN_NOISE = frozenset(
    {
        "api", "auth", "changelog", "docs", "email", "emails", "feature",
        "guide", "guides", "https", "integration", "knowledge", "pricing",
        "reference", "send", "sending", "settings", "smtp", "test", "with",
    }
)


def _unestablished_integration_partners(
    evidence_ids: list[str],
    artifacts: KnowledgeArtifacts,
    supported_audience_context: str,
) -> list[str]:
    """Find partner names that only source material, not the user, establishes."""
    company = artifacts.business.company_name.casefold()
    supported = supported_audience_context.casefold()
    partners: list[str] = []
    for evidence_id in evidence_ids:
        entry = artifacts.evidence.get(evidence_id)
        if entry is None or not evidence_id.startswith("R"):
            continue
        source_tokens = {
            token
            for token in re.findall(r"[a-z0-9]{4,}", entry.source.casefold())
            if token not in _SOURCE_TOKEN_NOISE
        }
        claim = entry.claim.casefold()
        for token in source_tokens:
            if token in company or token in supported or token not in claim:
                continue
            partners.append(token)
    return list(dict.fromkeys(partners))


def _integration_conditions(
    evidence_ids: list[str],
    artifacts: KnowledgeArtifacts,
    supported_audience_context: str,
) -> list[str]:
    """Keep an integration relevant without inventing that the reader uses it."""
    return [
        (
            f"Do not state or imply that every reader uses {partner.title()}. Present this "
            f"integration conditionally (for example, 'If you use {partner.title()}...') "
            "unless the user-supplied campaign context establishes it."
        )
        for partner in _unestablished_integration_partners(
            evidence_ids, artifacts, supported_audience_context
        )
    ]


def _depends_on_unestablished_partner(
    alternative: ArgumentOption,
    evidence_ids: list[str],
    artifacts: KnowledgeArtifacts,
    supported_audience_context: str,
) -> bool:
    partners = _unestablished_integration_partners(
        evidence_ids, artifacts, supported_audience_context
    )
    if not partners:
        return False
    proposition = (
        f"{alternative.single_idea} {alternative.felt_need} "
        f"{alternative.mechanism} {alternative.call_to_action} "
        f"{alternative.next_step_decision} {alternative.next_step_value}"
    ).casefold()
    return any(
        re.search(rf"\b{re.escape(partner)}\b", proposition)
        for partner in partners
    )


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
        intelligence: CampaignIntelligence | None = None,
        recovery: MaterialRecovery | None = None,
    ) -> CampaignBrief:
        prompt_artifacts = artifacts
        prompt_intelligence = intelligence
        researched = intelligence is not None and intelligence.research_loaded
        if intelligence is not None:
            intelligence.admit_automatically_recovered(artifacts.evidence)
            intelligence.validate_against(artifacts.evidence)
            if intelligence.v2_claim_boundary:
                forbidden = set(intelligence.forbidden_evidence_ids)
                prompt_artifacts = artifacts.model_copy(
                    update={
                        "evidence": EvidenceLedger(
                            entries=[
                                item
                                for item in artifacts.evidence.entries
                                if item.id not in forbidden
                            ]
                        )
                    }
                )
            if researched:
                # Discovery imagined a buyer so research could find one. Once
                # research exists, those biographies are not competing sources.
                segment = prompt_artifacts.audience.match(
                    chosen_segment or intelligence.selected_audience, "",
                )
                audience = prompt_artifacts.audience.model_copy(update={
                    "segments": [segment] if segment is not None else [],
                    "objections": [item for item in prompt_artifacts.audience.objections
                                   if item.grounding is Grounding.USER_STATED
                                   or (item.grounding is Grounding.GROUNDED and item.provenance)],
                })
                prompt_artifacts = prompt_artifacts.model_copy(update={"audience": audience})
                prompt_intelligence = intelligence.model_copy(update={
                    "objections": [item for item in intelligence.objections
                                   if item.grounding is Grounding.USER_STATED
                                   or (item.grounding is Grounding.GROUNDED and item.provenance)],
                })
        variables = {
            "request": request.request,
            "campaign_context": request.render_context(),
            "knowledge": prompt_artifacts.render_for_strategy(),
            # The shape of what exists, above the facts themselves. A hundred
            # undifferentiated entries answer "what is true" and hide "what
            # can this campaign argue from at all" - and the second question
            # is the one being asked here. An empty shelf is the most useful
            # line in it: it is why an obvious angle is off the table.
            "knowledge_map": build_knowledge_base(prompt_artifacts).render_map(),
            "proof_posture": assess(prompt_artifacts).render_for_strategy(),
            # What the material cannot contain: which of this company's
            # claims every competitor also makes. Absent, the strategist
            # is told so plainly rather than left to assume the field is
            # empty - see PositioningMap.render_for_strategy.
            "positioning": (
                positioning or PositioningMap()
            ).render_for_strategy(),
            # Unverified discovery remains a fallback, not a second biography
            # beside the verified audience selected for this campaign.
            "demand": (
                "The audience is already selected. Use the verified research below; "
                "discovery hypotheses are superseded, not additional facts about this reader."
                if researched else (demand or DemandMap()).render_for_strategy(chosen_segment)
            ),
            "campaign_intelligence": (
                prompt_intelligence.render_for_strategy() if prompt_intelligence is not None else ""
            ),
            "contract": contract.render(),
            "relevant_material": corpus.render_search(
                f"{request.request} {request.product_description}", _RETRIEVAL_CHUNKS
            ),
            "prior_learnings": prior_learnings or "This is the first campaign for this business.",
            "recovery_material": _render_recovery(recovery, artifacts),
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
        audience_context = f"{request.request}\n{request.render_context()}"
        brief = self._normalize(
            brief, contract, artifacts, intelligence, audience_context
        )

        count_wrong = contract.count_is_explicit and len(brief.emails) != contract.count
        unsupported_steps = [
            email for email in brief.emails
            if email.call_to_action and email.next_step_value
            and not email.next_step_evidence_ids
        ]
        if count_wrong or unsupported_steps:
            # Both are errors in the plan, so combine them into one bounded
            # correction before paying a writer or a cold reader.
            corrections: list[str] = []
            if count_wrong:
                corrections.append(
                    f"Your brief planned {len(brief.emails)} emails; the user requested "
                    f"exactly {contract.count}. Redesign the arc for that count."
                )
            if unsupported_steps:
                positions = ", ".join(str(email.position) for email in unsupported_steps)
                corrections.append(
                    f"Email(s) {positions} promise a concrete next-step payoff but have no "
                    "assigned next_step_evidence_ids. For each, choose verified ledger ids "
                    "that prove what the action or destination actually lets the reader do, "
                    "and include those ids in evidence_ids too. If no such fact exists, "
                    "change the action and its payoff to a supported first decision. Do not "
                    "treat generic account creation as proof that a test works."
                )
            logger.info("strategist: correcting %d plan defect(s)", len(corrections))
            brief = await self._session.structured(
                role=ROLE_ID,
                tier=ModelTier.DEEP,
                template="strategist",
                variables=variables,
                task="Rebuild the brief before drafting. " + " ".join(corrections),
                schema=CampaignBrief,
            )
            brief = self._normalize(
                brief, contract, artifacts, intelligence, audience_context
            )
            if any(
                email.call_to_action and email.next_step_value
                and not email.next_step_evidence_ids
                for email in brief.emails
            ):
                raise StrategyError(
                    "The strategy promises a next-step payoff without any assigned proof.",
                    request=request.request,
                )

        recovered_ids = {entry.id for entry in recovery.evidence} if recovery else set()
        if recovered_ids and not _spends_any(brief, recovered_ids):
            logger.info(
                "strategist: recovered evidence %s was ignored - correcting",
                sorted(recovered_ids),
            )
            brief = await self._session.structured(
                role=ROLE_ID,
                tier=ModelTier.DEEP,
                template="strategist",
                variables=variables,
                task=(
                    "Rebuild the brief around the automatic recovery section. The previous "
                    "brief ignored every newly verified fact. At least one primary email "
                    f"must assign one of {', '.join(sorted(recovered_ids))} in evidence_ids, "
                    "use it to answer the diagnosed gap, and make the supported official "
                    "documentation page the next step when it helps the reader decide before "
                    "signup. Keep the requested email count and all claim boundaries."
                ),
                schema=CampaignBrief,
            )
            brief = self._normalize(
                brief, contract, artifacts, intelligence, audience_context
            )
            if not _spends_any(brief, recovered_ids):
                raise StrategyError(
                    "The recovery strategy ignored every newly verified fact.",
                    request=request.request,
                )

        if not brief.emails:
            raise StrategyError(
                "The strategist produced no email briefs - there is nothing to write.",
                request=request.request,
            )
        if chosen_segment:
            brief.reader_segment = chosen_segment
        # The strategist chooses an argument, not a new biography. Passing its
        # expanded persona on as audience context lets invented tools, delays
        # and team ownership become facts in every subsequent writing call.
        segment = (
            next((item for item in artifacts.audience.segments if item.name == chosen_segment), None)
            if chosen_segment
            else artifacts.audience.match(brief.reader_segment, brief.reader)
        )
        if segment is not None:
            brief.reader = (
                f"Selected audience: {segment.name}.\n"
                f"Situation context ({segment.situation_grounding}; check applicability): "
                f"{segment.situation or 'not established'}"
            )
        else:
            brief.reader = (
                f"Selected audience: {brief.reader_segment or 'not established'}. "
                "No further situation is established beyond the user's request."
            )
        if request.target_market:
            brief.reader += f"\nUser-specified audience: {request.target_market}"
        if request.channel is not None and request.channel.confirmed_context:
            brief.reader += f"\nUser-confirmed recipient context: {request.channel.confirmed_context}"
        brief.contract = contract
        return brief

    # ------------------------------------------------------------- internals

    def _normalize(
        self,
        brief: CampaignBrief,
        contract: DeliverableContract,
        artifacts: KnowledgeArtifacts,
        intelligence: CampaignIntelligence | None = None,
        audience_context: str = "",
    ) -> CampaignBrief:
        """Fix in code everything about a brief that has a correct answer.

        Positions must be 1..n in order, evidence ids must exist, a fact one
        email spends is not there for the next one to spend again, and the
        "already spent" list is derivable from the briefs before it - asking a
        model to keep those consistent is asking it to do bookkeeping instead
        of thinking.
        """
        if intelligence is not None:
            intelligence.validate_against(artifacts.evidence)
            if intelligence.dossier_current and intelligence.orientation:
                brief.orientation = intelligence.orientation

        segment = artifacts.audience.match(brief.reader_segment, brief.reader)
        supported_audience_context = audience_context
        if segment is not None:
            # Store it back exactly as the audience model spells it, so the
            # cold reader is looked up by identity rather than matched again.
            brief.reader_segment = segment.name
            # A researched segment describes a plausible market, not this
            # recipient's installed stack. Only user-supplied campaign context
            # can establish that they already use an integration partner.
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
            forbidden_evidence: list[str] = []
            if intelligence is not None and intelligence.v2_claim_boundary:
                allowed = set(intelligence.allowed_evidence_ids)
                forbidden = set(intelligence.forbidden_evidence_ids)
                removed = [
                    evidence_id
                    for evidence_id in assigned
                    if evidence_id not in allowed or evidence_id in forbidden
                ]
                if removed:
                    logger.info(
                        "strategist: dropped V2-forbidden evidence ids %s", removed
                    )
                assigned = [
                    evidence_id
                    for evidence_id in assigned
                    if evidence_id in allowed and evidence_id not in forbidden
                ]
                forbidden_evidence = sorted(forbidden | set(removed))
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
            next_step_evidence = [
                evidence_id
                for evidence_id in email.next_step_evidence_ids
                if evidence_id in assigned
            ]
            if email.next_step_evidence_ids and not next_step_evidence:
                logger.info(
                    "strategist: email %d named no assigned evidence for its CTA payoff",
                    position,
                )
            call_to_action, next_step_value = _recovered_next_step(
                artifacts=artifacts,
                evidence_ids=assigned,
                next_step_evidence_ids=next_step_evidence,
                call_to_action=email.call_to_action,
                next_step_value=email.next_step_value,
            )
            constraints = _distinct_constraints(
                [
                    *email.must_not_say,
                    *_integration_conditions(
                        assigned, artifacts, supported_audience_context
                    ),
                ]
            )
            felt_need = email.felt_need
            status_quo = email.status_quo
            if intelligence is not None:
                if intelligence.research_loaded:
                    felt_need = intelligence.normalized_felt_need(felt_need)
                    status_quo = intelligence.normalized_status_quo(status_quo)
                caveats = intelligence.constraints_for(assigned, artifacts.evidence)
                if intelligence.v2_claim_boundary:
                    constraints = _distinct_constraints(
                        [*constraints, *intelligence.forbidden_claims]
                    )
                if intelligence.selected_company_name:
                    constraints = _distinct_constraints(
                        [
                            *constraints,
                            (
                                f"Do not state that {intelligence.selected_company_name} has "
                                "an internal problem or workflow unless the direct company "
                                "evidence establishes it; otherwise use conditional or "
                                "audience-level language."
                            ),
                        ]
                    )
                existing_constraints = {
                    " ".join(item.casefold().split()) for item in constraints
                }
                injected = [
                    caveat
                    for caveat in caveats
                    if " ".join(caveat.casefold().split()) not in existing_constraints
                ]
                constraints = _distinct_constraints([*constraints, *caveats])
                for caveat in injected:
                    if caveat not in intelligence.trace.partial_caveats_injected:
                        intelligence.trace.partial_caveats_injected.append(caveat)
                for evidence_id in intelligence.selected_withhold(
                    assigned, artifacts.evidence
                ):
                    if evidence_id not in intelligence.trace.withhold_evidence_selected:
                        intelligence.trace.withhold_evidence_selected.append(evidence_id)
                        intelligence.trace.warn(
                            f"WITHHOLD evidence selected by the Strategist: {evidence_id}."
                        )
            alternative_arguments: list[ArgumentOption] = []
            seen_argument_keys = {_idea_key(email.single_idea)}
            for alternative in email.alternative_arguments:
                idea_key = _idea_key(alternative.single_idea)
                if (
                    not idea_key
                    or any(_too_close(idea_key, earlier) for earlier in seen_argument_keys)
                    or len(alternative_arguments) >= MAX_ALTERNATIVE_ARGUMENTS
                ):
                    continue
                seen_argument_keys.add(idea_key)
                alternative_evidence = [
                    evidence_id
                    for evidence_id in alternative.evidence_ids
                    if evidence_id in known_evidence
                ]
                if intelligence is not None and intelligence.v2_claim_boundary:
                    allowed = set(intelligence.allowed_evidence_ids)
                    forbidden = set(intelligence.forbidden_evidence_ids)
                    alternative_evidence = [
                        evidence_id
                        for evidence_id in alternative_evidence
                        if evidence_id in allowed and evidence_id not in forbidden
                    ]
                alternative_evidence = alternative_evidence[:MAX_EVIDENCE_PER_EMAIL]
                if _depends_on_unestablished_partner(
                    alternative, alternative_evidence, artifacts, supported_audience_context
                ):
                    logger.info(
                        "strategist: alternative %r depends on partner usage absent from "
                        "user-selected audience context - dropped before candidate drafting",
                        alternative.single_idea,
                    )
                    continue
                alternative_next_step_evidence = [
                    evidence_id
                    for evidence_id in alternative.next_step_evidence_ids
                    if evidence_id in alternative_evidence
                ]
                alternative_action, alternative_next_step_value = _recovered_next_step(
                    artifacts=artifacts,
                    evidence_ids=alternative_evidence,
                    next_step_evidence_ids=alternative_next_step_evidence,
                    call_to_action=alternative.call_to_action,
                    next_step_value=alternative.next_step_value,
                )
                alternative_constraints = _distinct_constraints(
                    [
                        *alternative.must_not_say,
                        *_integration_conditions(
                            alternative_evidence,
                            artifacts,
                            supported_audience_context,
                        ),
                    ]
                )
                alternative_felt_need = alternative.felt_need
                alternative_status_quo = alternative.status_quo
                if intelligence is not None:
                    if intelligence.research_loaded:
                        alternative_felt_need = intelligence.normalized_felt_need(
                            alternative_felt_need
                        )
                        alternative_status_quo = intelligence.normalized_status_quo(
                            alternative_status_quo
                        )
                    alternative_constraints = _distinct_constraints(
                        [
                            *alternative_constraints,
                            *intelligence.constraints_for(
                                alternative_evidence, artifacts.evidence
                            ),
                            *(
                                intelligence.forbidden_claims
                                if intelligence.v2_claim_boundary
                                else []
                            ),
                        ]
                    )
                alternative_arguments.append(
                    alternative.model_copy(
                        update={
                            "felt_need": alternative_felt_need,
                            "status_quo": alternative_status_quo,
                            "evidence_ids": alternative_evidence,
                            "next_step_evidence_ids": alternative_next_step_evidence,
                            "call_to_action": alternative_action,
                            "next_step_value": alternative_next_step_value,
                            "must_not_say": alternative_constraints,
                        }
                    )
                )
            email = email.model_copy(
                update={
                    "position": position,
                    "evidence_ids": assigned,
                    "next_step_evidence_ids": next_step_evidence,
                    "call_to_action": call_to_action,
                    "next_step_value": next_step_value,
                    "felt_need": felt_need,
                    "status_quo": status_quo,
                    "must_not_say": constraints,
                    "forbidden_evidence_ids": forbidden_evidence,
                    "forbidden_capability_ids": (
                        list(intelligence.forbidden_capability_ids)
                        if intelligence is not None
                        and intelligence.v2_claim_boundary
                        else []
                    ),
                    "must_not_reuse": list(spent),
                    "alternative_ideas": _distinct_ideas(
                        email.alternative_ideas, email.single_idea
                    )[:MAX_ALTERNATIVE_IDEAS],
                    "alternative_arguments": alternative_arguments,
                }
            )
            if cta_labels and email.call_to_action and email.call_to_action.lower() not in cta_labels:
                # Not fatal: the strategist may legitimately phrase an existing
                # action differently. Worth knowing when a run's CTAs drift.
                logger.info(
                    "strategist: call to action %r is not on the offer sheet", email.call_to_action
                )
            for alternative in alternative_arguments:
                if (
                    cta_labels
                    and alternative.call_to_action
                    and alternative.call_to_action.lower() not in cta_labels
                ):
                    logger.info(
                        "strategist: alternative call to action %r is not on the offer sheet",
                        alternative.call_to_action,
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


def _distinct_constraints(items: list[str]) -> list[str]:
    seen: set[str] = set()
    kept: list[str] = []
    for item in items:
        value = item.strip()
        key = " ".join(value.casefold().split())
        if key and key not in seen:
            kept.append(value)
            seen.add(key)
    return kept


def _idea_key(idea: str) -> frozenset[str]:
    return frozenset(word for word in re.findall(r"[a-z]{4,}", idea.lower()))


def _too_close(left: frozenset[str], right: frozenset[str]) -> bool:
    if not left or not right:
        return False
    return len(left & right) * 2 >= min(len(left), len(right))
