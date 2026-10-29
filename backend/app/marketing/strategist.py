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
from app.knowledge.decision_context import select_evidence
from app.knowledge.ledger import EvidenceKind
from app.market.demand import DemandMap
from app.market.material_research import MaterialRecovery
from app.market.positioning import PositioningMap
from app.marketing.briefs import ArgumentOption, CampaignBrief, EmailBrief
from app.marketing.contract import DeliverableContract
from app.marketing.exceptions import StrategyError
from app.marketing.intelligence import CampaignIntelligence
from app.marketing.intent import CampaignIntent
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
    if recovery is not None and not recovery.recovered:
        lines = [
            "The previous draft exposed this exact decision gap:",
            recovery.gap,
            "",
            "Official-source research could not verify the missing fact:",
            recovery.note or "No verified official fact closed the gap.",
            "",
            (
                "Rebuild the campaign around a smaller decision supported by existing "
                "evidence. Do not repeat the unavailable payoff, imply that the missing "
                "fact is known, or make the reader's next step depend on it. Choose a "
                "documented action and state its exact limitation."
            ),
        ]
        if persisted:
            lines.append("Earlier verified official facts remain available when relevant:")
            lines.extend(
                f"- [{entry.id}] {entry.claim} (official source: {entry.source})"
                for entry in persisted
            )
        return "\n".join(lines)
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
                "signup, it is an available action, not a mandatory one. Recovery changes the "
                "available evidence, not the campaign's objective. Recovered facts may instead "
                "make an existing licensed signup or product action worthwhile. Choose a guide "
                "only when its documented contents add useful evaluation beyond the email's "
                "own explanation; use its exact URL and name that additional decision. Do not "
                "require a documentation click just because it is the source of a fact. Do not "
                "claim that a page proves anything outside its quoted fact."
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
    fixed_cta_url: str = "",
    action_id: str = "",
) -> tuple[str, str]:
    """Tie an automatically recovered payoff to its exact official page."""
    if fixed_cta_url:
        return call_to_action, next_step_value
    urls = {
        url.rstrip(".,;:)")
        for url in re.findall(r'https?://[^\s<>"\]]+', call_to_action)
    }
    known_destinations = {action.url for action in artifacts.offer.calls_to_action if action.url}
    if len(urls) == 1 and urls.issubset(known_destinations):
        return call_to_action, next_step_value
    if any(action_id == action.reference_id or call_to_action.casefold() == action.label.casefold()
           for action in artifacts.offer.calls_to_action):
        return call_to_action, next_step_value
    ordered = list(dict.fromkeys([*next_step_evidence_ids, *evidence_ids]))
    entries = [
        found
        for evidence_id in ordered
        if evidence_id.startswith("R")
        and (found := artifacts.evidence.get(evidence_id)) is not None
        and found.source.startswith(("https://", "http://"))
    ]
    if not entries:
        return call_to_action, next_step_value
    supported_sources = {
        entry.source for entry in entries
        if not next_step_evidence_ids or entry.id in next_step_evidence_ids
    }
    if len(urls) == 1 and urls.issubset(supported_sources):
        return call_to_action, next_step_value
    entry = entries[0]
    return (
        f"Review the official documentation: {entry.source}",
        f"The official page documents this verified fact: {entry.claim}",
    )


_SOURCE_TOKEN_NOISE = frozenset(
    {
        "api", "auth", "changelog", "console", "dashboard", "docs", "email", "emails", "feature",
        "guide", "guides", "https", "integration", "knowledge", "pricing",
        "introduction", "logs", "overview",
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


def _connection_route_constraints(evidence_ids: list[str], artifacts: KnowledgeArtifacts) -> list[str]:
    """A platform name or a webhook capability does not specify its setup path."""
    entries = [artifacts.evidence.get(item) for item in evidence_ids]
    if not any(
        item is not None and (
            item.kind is EvidenceKind.INTEGRATION
            or re.search(r"\b(?:webhooks?|endpoints?|native connector)\b", item.verbatim, re.IGNORECASE)
        )
        for item in entries
    ):
        return []
    return [
        ("Keep the connection route attached to its cited source. A native or prebuilt "
        "integration and a custom HTTP/webhook endpoint are separate setup paths unless "
        "the source explicitly equates them. A platform name alone establishes neither "
        "manual endpoint configuration nor a no-setup connector. Keep unknown setup "
        "requirements unknown; do not mix the steps or benefits of those paths.")
    ]


def _repair_argument_dependencies(
    original: EmailBrief | ArgumentOption,
    normalized: EmailBrief | ArgumentOption,
    artifacts: KnowledgeArtifacts,
    intelligence: CampaignIntelligence | None,
    *,
    fixed_cta_url: str,
) -> tuple[EmailBrief | ArgumentOption, bool]:
    """A rejected premise cannot keep its old benefit and CTA payoff alive.

    This narrows a proposed plan, not the finished email's factual gates. No
    new call is bought: a writer can explain the assigned function with its
    limits, or the existing critic can report a remaining argument gap.
    """
    if intelligence is None or not intelligence.research_loaded:
        return normalized, False
    if not normalized.status_quo.strip():
        normalized = normalized.model_copy(update={"why_it_fails": ""})
    missing_bridge = bool((original.felt_need.strip() or original.problem_ids) and not normalized.felt_need.strip())
    if not missing_bridge:
        return normalized, False

    entries = [item for id_ in normalized.evidence_ids
               if (item := artifacts.evidence.get(id_)) is not None]
    function = next((item for item in entries
                     if item.kind in {EvidenceKind.FEATURE, EvidenceKind.INTEGRATION}), None)
    anchor = function or next((item for item in entries if item.kind is EvidenceKind.PRICE), None)
    # Preserve the requested action. A failed premise requires another
    # strategic decision, not an automatic tutorial CTA.
    claim = anchor.claim if anchor else (
        artifacts.business.company_name
        if intelligence.v2_claim_boundary else
        f"{artifacts.business.company_name}: {artifacts.business.what_it_does}".strip(": ")
    )
    limitation = (
        "The assigned evidence does not establish that this function resolves the proposed "
        "buyer problem. Inspecting its source or starting an account does not demonstrate "
        "that outcome, a completed integration, or a result for this recipient."
    )
    updates = {
        "single_idea": claim,
        "felt_need": "", "status_quo": "", "why_it_fails": "",
        "mechanism": function.claim if function else "",
        "belief_shift": "", "objection": "",
        "subject_strategy": "Respect the campaign objective and name only a supported proposition; do not imply novelty without user-provided or dated support.",
        "next_step_decision": "",
        "next_step_value": "",
        "next_step_evidence_ids": [],
        "next_step_limit": limitation,
        "argument_issue": "The proposed buyer problem is not linked to the assigned evidence. Select another complete argument while preserving campaign intent and action constraints.",
        "must_not_say": _distinct_constraints([*normalized.must_not_say, limitation]),
    }
    if isinstance(normalized, EmailBrief):
        updates["job"] = original.job
    intelligence.trace.warn(
        "Reframed an unlinked buyer-problem argument as the documented function or offer "
        f"({', '.join(normalized.evidence_ids) or 'no assigned evidence'}); its old benefit, "
        "alternative failure story and evaluation payoff were not retained."
    )
    return normalized.model_copy(update=updates), True


def _resolve_proposition_action(
    argument: EmailBrief | ArgumentOption, artifacts: KnowledgeArtifacts,
    fixed_cta_url: str,
) -> EmailBrief | ArgumentOption:
    # Historical briefs put the chosen link in the CTA field. Preserve that
    # explicit choice, subject to exactly the same licensing below.
    if not argument.next_step_url:
        urls = {url.rstrip(".,;:)") for url in re.findall(r'https?://[^\s<>"\]]+', argument.call_to_action)}
        if len(urls) == 1:
            argument = argument.model_copy(update={"next_step_url": urls.pop()})
    actions = {item.reference_id: item for item in artifacts.offer.calls_to_action}
    updates: dict = {"offer_id": argument.offer_id or "offering"}
    known_offers = {"offering", *(plan.reference_id for plan in artifacts.offer.plans)}
    if argument.offer_id and argument.offer_id not in known_offers:
        updates["argument_issue"] = "The proposition references an unknown offer id. Select offering or an exact plan id from the offer sheet."
    action = actions.get(argument.action_id) if argument.action_id else None
    if argument.action_id and action is None:
        updates["argument_issue"] = "The proposition references an unknown offer action. Choose an action from the supplied catalogue."
    if action is None and not argument.action_id:
        matches = [item for item in actions.values()
                   if item.label.casefold() == argument.call_to_action.casefold()
                   or (item.url and item.url == argument.next_step_url)]
        if len(matches) == 1:
            action = matches[0]
            updates["action_id"] = action.reference_id
    if action is not None and not argument.call_to_action:
        updates["call_to_action"] = action.label

    destination = fixed_cta_url or (action.url if action else "") or argument.next_step_url
    if not destination and action is None and argument.next_step_evidence_ids:
        sources = {entry.source for entry in artifacts.evidence.entries
                   if entry.id in argument.next_step_evidence_ids
                   and entry.id in argument.evidence_ids
                   and entry.source.startswith(("https://", "http://"))}
        if len(sources) == 1:
            destination = sources.pop()
    if destination and not fixed_cta_url and not (action and action.url):
        licensed = {entry.source for entry in artifacts.evidence.entries
                    if entry.id in argument.evidence_ids}
        licensed.update(item.url for item in actions.values() if item.url)
        if destination not in licensed:
            destination = ""
            updates["argument_issue"] = "The selected destination is not licensed by an assigned source or an offer action."
    updates["next_step_url"] = destination or ""
    if argument.destination_kind == "web" and not destination:
        updates["argument_issue"] = (
            "The web CTA has no verified destination. Choose one exact assigned evidence source "
            "or an offer action with a URL; a brand homepage fallback does not establish the promised page."
        )
    return argument.model_copy(update=updates)


class Strategist:
    def __init__(self, session: ModelSession) -> None:
        self._session = session
        self.audit: list[dict] = []

    def _normalize_traced(self, brief: CampaignBrief, *args, **kwargs) -> CampaignBrief:
        raw = brief.model_dump(mode="json")
        result = self._normalize(brief, *args, **kwargs)
        effective = result.model_dump(mode="json")
        self.audit.append({"raw_plan": raw, "effective_plan": effective,
                           "changed_fields": [key for key in raw if raw[key] != effective.get(key)]})
        return result

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
                prompt_artifacts = artifacts.for_claim_boundary(
                    set(intelligence.allowed_evidence_ids)
                    - set(intelligence.forbidden_evidence_ids)
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
        preferred = [item.evidence_id for item in intelligence.ranked_evidence
                     if str(item.band) in {"LEAD", "SUPPORT", "lead", "support"}] if intelligence else []
        selection = select_evidence(
            prompt_artifacts.evidence,
            f"{request.request} {request.render_context()} {chosen_segment} "
            + (prompt_intelligence.render_for_strategy() if prompt_intelligence else ""),
            preferred_ids=preferred,
            excluded_ids=frozenset(intelligence.forbidden_evidence_ids) if intelligence else frozenset(),
        )
        prompt_artifacts = prompt_artifacts.model_copy(update={"evidence": selection.ledger})
        variables = {
            "request": request.request,
            "campaign_context": request.render_context(),
            "knowledge": selection.render_manifest() + "\n" + prompt_artifacts.render_for_strategy(),
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
            ).render_for_strategy(audience=(
                request.target_market or chosen_segment
                or (intelligence.selected_audience if intelligence is not None else "")
            ) + (
                f"; qualified scope: {intelligence.eligible_subsegment}"
                if intelligence is not None and intelligence.eligible_subsegment else ""
            )),
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
        brief = self._normalize_traced(
            brief, contract, artifacts, intelligence, audience_context,
            fixed_cta_url=request.cta_url or "",
            intent=request.effective_intent,
        )

        count_wrong = contract.count_is_explicit and len(brief.emails) != contract.count
        unsupported_steps = [
            email for email in brief.emails
            if email.call_to_action and email.next_step_value
            and not email.next_step_evidence_ids
        ]
        invalid_arguments = [email for email in brief.emails if email.argument_issue]
        recovered_ids = {entry.id for entry in recovery.evidence} if recovery else set()
        missing_recovery = bool(recovered_ids and not _spends_any(brief, recovered_ids))
        if count_wrong or unsupported_steps or invalid_arguments or missing_recovery:
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
            if invalid_arguments:
                corrections.append(
                    "Rebuild the invalid proposition(s), preserving the campaign objective, selected audience and fixed CTA: "
                    + "; ".join(f"email {email.position}: {email.argument_issue}" for email in invalid_arguments)
                    + ". Prefer a supported complete alternative; do not automatically replace the user's campaign by a documentation tutorial. Use problem_ids for researched premises."
                )
            if missing_recovery:
                corrections.append(
                    "Use at least one newly verified recovery fact to answer the diagnosed gap: "
                    + ", ".join(sorted(recovered_ids))
                    + ". Preserve the campaign objective and choose an action whose payoff the supplied material supports."
                )
            logger.info("strategist: correcting %d plan defect(s)", len(corrections))
            brief = await self._session.structured(
                role=ROLE_ID,
                tier=ModelTier.DEEP,
                template="strategist",
                variables=variables,
                task=(
                    "Repair this prior brief before drafting. Keep its supported argument "
                    "and change only what the listed defects require. Prior normalized brief: "
                    + brief.model_dump_json()
                    + " Defects: "
                    + " ".join(corrections)
                ),
                schema=CampaignBrief,
            )
            brief = self._normalize_traced(
                brief, contract, artifacts, intelligence, audience_context,
                fixed_cta_url=request.cta_url or "",
                intent=request.effective_intent,
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

        if recovered_ids and not _spends_any(brief, recovered_ids):
            raise StrategyError(
                "The recovery strategy ignored every newly verified fact after its one combined correction.",
                request=request.request,
            )

        if not brief.emails:
            raise StrategyError(
                "The strategist produced no email briefs - there is nothing to write.",
                request=request.request,
            )
        if chosen_segment:
            brief.reader_segment = chosen_segment
        brief.reader_scope = (
            intelligence.eligible_subsegment
            if intelligence is not None and intelligence.dossier_current
            and intelligence.trace.qualified_subsegment and not request.target_market else ""
        )
        brief.reader_profile_override = (
            (request.target_market or "").strip() if not chosen_segment else ""
        )
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
                "Research context describes some members of this market, not this "
                "recipient's installed tools or experiences. Follow the campaign request "
                "when it scopes the job.\n"
                f"Observed situation ({segment.situation_grounding}; check applicability): "
                f"{segment.situation or 'not established'}"
            )
        else:
            brief.reader = (
                f"Selected audience: {brief.reader_segment or 'not established'}. "
                "No further situation is established beyond the user's request."
            )
        if request.target_market:
            brief.reader += f"\nUser-specified audience: {request.target_market}"
        if brief.reader_scope:
            brief.reader += f"\nQualified campaign scope within that audience: {brief.reader_scope}."
        if brief.reader_profile_override:
            brief.reader = (
                f"Selected audience (user-stated constraints): {brief.reader_profile_override}.\n"
                "No further recipient situation is established. Compiled market context "
                "is research to check for applicability, not a replacement biography."
            )
        if request.channel is not None and request.channel.confirmed_context:
            brief.reader += f"\nUser-confirmed recipient context: {request.channel.confirmed_context}"
        brief.contract = contract
        if self.audit:
            self.audit[-1]["effective_plan"] = brief.model_dump(mode="json")
        return brief

    # ------------------------------------------------------------- internals

    def _normalize(
        self,
        brief: CampaignBrief,
        contract: DeliverableContract,
        artifacts: KnowledgeArtifacts,
        intelligence: CampaignIntelligence | None = None,
        audience_context: str = "",
        *,
        fixed_cta_url: str = "",
        intent: CampaignIntent | None = None,
    ) -> CampaignBrief:
        """Fix in code everything about a brief that has a correct answer.

        Positions must be 1..n in order, evidence ids must exist, a fact one
        email spends is not there for the next one to spend again, and the
        "already spent" list is derivable from the briefs before it - asking a
        model to keep those consistent is asking it to do bookkeeping instead
        of thinking.
        """
        brief.fixed_cta_url = fixed_cta_url
        brief.intent = intent
        brief.pipeline_version = 2
        brief.strategy_mode = "planned"
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
        reframed_positions: list[int] = []
        spent: list[str] = []
        spent_evidence: set[str] = set()
        for position, email in enumerate(emails, start=1):
            # The payoff proof is part of this argument. Models sometimes name
            # it in the dedicated field but forget to repeat it in the broad
            # evidence list; preserve that valid ID before enforcing the cap.
            requested_ids = list(dict.fromkeys([
                *email.next_step_evidence_ids, *email.evidence_ids,
            ]))
            unknown = [id_ for id_ in requested_ids if id_ not in known_evidence]
            if unknown:
                logger.info("strategist: dropped unknown evidence ids %s", unknown)
            assigned = [id_ for id_ in requested_ids if id_ in known_evidence]
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
                # Carry the complete campaign boundary into craft retrieval,
                # not only the disallowed ids the strategist happened to pick.
                # Otherwise a later reader question can rediscover an unranked
                # customer result that the contract never licensed.
                forbidden_evidence = sorted(forbidden | (known_evidence - allowed))
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
                fixed_cta_url=fixed_cta_url,
                action_id=email.action_id,
            )
            constraints = _distinct_constraints(
                [
                    *email.must_not_say,
                    *_integration_conditions(
                        assigned, artifacts, supported_audience_context
                    ),
                    *_connection_route_constraints(assigned, artifacts),
                ]
            )
            felt_need = email.felt_need
            status_quo = email.status_quo
            if intelligence is not None:
                if intelligence.research_loaded:
                    felt_need = intelligence.normalized_felt_need(felt_need, assigned, email.problem_ids)
                    status_quo = intelligence.normalized_status_quo(status_quo)
                    if email.felt_need.strip() and not felt_need:
                        constraints = _distinct_constraints([*constraints,
                            "No verified link connects this argument to the proposed buyer problem. Explain only the documented function; do not invent a pain, a switching story or a promised outcome."])
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
                    fixed_cta_url=fixed_cta_url,
                    action_id=alternative.action_id,
                )
                alternative_constraints = _distinct_constraints(
                    [
                        *alternative.must_not_say,
                        *_integration_conditions(
                            alternative_evidence,
                            artifacts,
                            supported_audience_context,
                        ),
                        *_connection_route_constraints(alternative_evidence, artifacts),
                    ]
                )
                alternative_felt_need = alternative.felt_need
                alternative_status_quo = alternative.status_quo
                if intelligence is not None:
                    if intelligence.research_loaded:
                        alternative_felt_need = intelligence.normalized_felt_need(
                            alternative_felt_need, alternative_evidence, alternative.problem_ids
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
                repaired_alternative, _ = _repair_argument_dependencies(
                    alternative,
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
                    ), artifacts, intelligence, fixed_cta_url=fixed_cta_url,
                )
                alternative_arguments.append(_resolve_proposition_action(repaired_alternative, artifacts, fixed_cta_url))
            email = email.model_copy(
                update={
                    "position": position,
                    "target_audience": intelligence.selected_audience if intelligence is not None else "",
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
            email, reframed = _repair_argument_dependencies(
                brief.emails[position - 1], email, artifacts, intelligence,
                fixed_cta_url=fixed_cta_url,
            )
            email = _resolve_proposition_action(email, artifacts, fixed_cta_url)
            if reframed:
                reframed_positions.append(position)
                email.alternative_ideas = []
                valid_alternative = next((item for item in email.alternative_arguments
                                          if not item.argument_issue), None)
                if valid_alternative is not None:
                    email = email.with_argument(valid_alternative)
                    email.alternative_arguments = [item for item in email.alternative_arguments
                                                   if item is not valid_alternative]
                    reframed_positions.remove(position)
                    if intelligence is not None:
                        intelligence.trace.warn("Selected a complete supported alternative instead of changing the campaign into a first-feature documentation pitch.")
            distinct_arguments: list[ArgumentOption] = []
            argument_keys = [_idea_key(email.single_idea)]
            for alternative in email.alternative_arguments:
                key = _idea_key(alternative.single_idea)
                if key and not any(_too_close(key, prior) for prior in argument_keys):
                    distinct_arguments.append(alternative)
                    argument_keys.append(key)
            if len(distinct_arguments) != len(email.alternative_arguments) and intelligence is not None:
                intelligence.trace.warn("Removed duplicate arguments after repairing their unsupported premise; no redundant draft is needed.")
            email.alternative_arguments = distinct_arguments
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
        if reframed_positions:
            brief.promise = " ".join(_distinct_constraints([item.single_idea for item in normalized]))
            brief.arc = " ".join(item.job for item in normalized if item.job)
            brief.sequence_rationale = (
                "The product/problem link was not established for email(s) "
                + ", ".join(map(str, reframed_positions))
                + ". A new proposition is needed to meet the original campaign objective; "
                "the unsupported problem and dependent outcome were removed without changing the requested action."
            )
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
