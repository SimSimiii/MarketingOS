"""Editing one finished email on request, without re-running the campaign.

"Too long", "more direct": the user has the email and wants a difference.
Re-running the campaign to get it would re-plan, re-draft and re-read every
email in the sequence to change one paragraph, so this reuses what the run
already settled - the brief this slot was finally written to, the evidence
it may spend, the emails before it - and buys one writer pass.

Bounded on purpose. One writer pass and its independent source review, and at
most one repair/review pair. No cold read, critic or duel: the user supplies
the preference. The exact proposal receives fresh mechanical checks and AI
source judgment; the original's approval never validates changed words.
A proposal that still fails after its repair is kept and shown, marked
blocked, and cannot be chosen.
"""

from dataclasses import dataclass

from app.knowledge.artifacts import KnowledgeArtifacts
from app.knowledge.ledger import EvidenceIndex
from app.market.positioning import PositioningMap
from app.marketing.briefs import CampaignBrief, EmailBrief
from app.marketing.craft import check_draft
from app.marketing.email_copy import Email
from app.marketing.gates import GateReport
from app.marketing.grounding import ClaimReviewer
from app.marketing.request import CampaignRequest
from app.marketing.writer import EmailWriter

#: Writer passes one proposal may spend: the adjustment, and one repair.
MAX_PASSES = 2
#: Proposals one email may accumulate. A ceiling on a loop a user can drive
#: by hand, so a stuck conversation with one email stops costing quota.
MAX_REVISIONS_PER_EMAIL = 12
MAX_INSTRUCTION_CHARS = 500


def adjustment_review_brief(brief: EmailBrief, instruction: str,
                            earlier_requests: list[str] | None = None) -> EmailBrief:
    """The reviewer must see the user's latest preference, not just the old plan."""
    reviewed = brief.model_copy(deep=True)
    reviewed.steering.directions.extend([
        *("Earlier local adjustment: " + text for text in earlier_requests or []),
        "Current local adjustment: " + instruction,
        ("The current local adjustment supersedes earlier editorial/inclusion preferences. "
         "It cannot establish a new fact, remove source conditions or license forbidden claims."),
    ])
    return reviewed


@dataclass
class Adjustment:
    email: Email
    #: The checks of *this* text. Never the original's.
    gates: GateReport
    passes: int

    @property
    def blocked(self) -> bool:
        return bool(self.gates.blocking)


async def adjust_email(
    *,
    writer: EmailWriter,
    draft: Email,
    brief: EmailBrief,
    campaign: CampaignBrief,
    request: CampaignRequest,
    artifacts: KnowledgeArtifacts,
    evidence: EvidenceIndex,
    previous: list[Email],
    instruction: str,
    earlier_requests: list[str] | None = None,
    merge_fields: list[str] | tuple[str, ...] = (),
    positioning: PositioningMap | None = None,
) -> Adjustment:
    """Make the change, check it as a run would, repair once if it broke."""
    current = draft
    gates: GateReport | None = None
    passes = 0
    reviewer = ClaimReviewer(writer._session)
    review_brief = adjustment_review_brief(brief, instruction, earlier_requests)
    while passes < MAX_PASSES:
        proposal = await writer.adjust(
            draft=current, brief=brief, campaign=campaign, request=request,
            artifacts=artifacts, previous=previous, instruction=instruction,
            earlier_requests=earlier_requests, gates=gates,
        )
        passes += 1
        # The slot does not move because its copy did.
        proposal = proposal.model_copy(update={"position": draft.position})
        gates, _ = check_draft(
            proposal, brief, artifacts=artifacts, evidence=evidence, previous=previous,
            merge_fields=merge_fields, positioning=positioning,
        )
        if not gates.blocking:
            gates = gates.extend(await reviewer.review(
                email=proposal, brief=review_brief, artifacts=artifacts, hints=gates, corpus=writer.corpus,
            ))
        current = proposal
        if not gates.blocking:
            break
    assert gates is not None
    return Adjustment(email=current, gates=gates, passes=passes)
