"""Route a clearly specified single email without a strategic model call.

Action selection is an identity check, never list order or a keyword guess.
Ambiguous jobs retain the planned path and its configured review depth.
"""

from app.knowledge.artifacts import KnowledgeArtifacts
from app.marketing.briefs import CampaignBrief, EmailBrief
from app.marketing.contract import DeliverableContract, DeliverableKind
from app.marketing.intelligence import CampaignIntelligence
from app.marketing.policy import ExecutionPolicy
from app.marketing.request import CampaignRequest

_DIRECT_OBJECTIVES = {"announcement", "activation", "recovery", "nurture"}


def direct_brief(
    request: CampaignRequest,
    artifacts: KnowledgeArtifacts,
    contract: DeliverableContract,
    policy: ExecutionPolicy,
    intelligence: CampaignIntelligence | None = None,
    selected_audience: str = "",
) -> CampaignBrief | None:
    if policy.strategy_mode == "planned" or request.channel is not None:
        return None
    if contract.kind is not DeliverableKind.SINGLE_EMAIL or contract.count != 1:
        return None
    intent = request.effective_intent
    if policy.strategy_mode == "auto" and (
        request.intent is None or intent.objective not in _DIRECT_OBJECTIVES
    ):
        return None
    actions = artifacts.offer.calls_to_action
    if request.cta_url:
        actions = [action for action in actions if action.url == request.cta_url]
    elif intent.desired_action:
        matches = [action for action in actions if intent.desired_action.strip().casefold()
                   in {action.label.strip().casefold(), action.reference_id.casefold()}]
        if not matches:
            return None
        actions = matches
    # Identical actions can occur twice in legacy compilations. Different
    # labels/destinations remain ambiguous even when one happens to be first.
    unique = {(action.reference_id, action.label, action.url): action for action in actions}
    if len(unique) != 1:
        return None
    action = next(iter(unique.values()))
    if not action.url:
        return None
    forbidden = list(intelligence.forbidden_evidence_ids) if intelligence else []
    if intelligence and intelligence.v2_claim_boundary:
        forbidden = sorted(set(forbidden) | (
            artifacts.evidence.ids - set(intelligence.allowed_evidence_ids)
        ))
    if set(action.evidence_ids) & set(forbidden):
        return None
    audience = request.target_market or selected_audience or (intelligence.selected_audience if intelligence else "")
    email = EmailBrief(
        position=1,
        job=request.request,
        offer_id="offering",
        action_id=action.reference_id,
        call_to_action=action.label,
        next_step_url=action.url or "",
        next_step_evidence_ids=list(action.evidence_ids),
        selection_reason="The user specified one email; its action is unambiguous in the offer.",
        must_not_say=list(intelligence.forbidden_claims) if intelligence else [],
        forbidden_evidence_ids=forbidden,
        forbidden_capability_ids=list(intelligence.forbidden_capability_ids) if intelligence else [],
    )
    return CampaignBrief(
        strategy_mode="direct", intent=intent, contract=contract,
        interpretation=request.request, reader=audience, reader_profile_override=audience,
        reader_scope=intelligence.eligible_subsegment if intelligence else "",
        fixed_cta_url=request.cta_url or "", orientation=artifacts.business.what_it_does,
        emails=[email],
    )
