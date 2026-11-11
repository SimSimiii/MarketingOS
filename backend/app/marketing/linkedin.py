"""Short outreach with mechanical channel limits and independent AI source review."""
import re

from app.ai.model_router import ModelTier
from app.knowledge.artifacts import KnowledgeArtifacts
from app.knowledge.ledger import Evidence, EvidenceKind
from app.marketing.briefs import CampaignBrief, EmailBrief
from app.marketing.email_copy import Email
from app.marketing.gates import GateReport
from app.marketing.grounding import ClaimReviewer
from app.runtime.exceptions import OutputValidationError
from app.runtime.model_session import ModelSession
from app.schemas.linkedin import MessageDraft, MessageRequest

ROLE_ID = "linkedin_writer"

#: Our editorial ceiling per format, and the band to actually aim for. Both
#: are in the prompt because a ceiling on its own is read as a target: at 1200
#: characters the writer produced 592 - four sentences of product mechanism -
#: and was within its limit the whole way.
_LIMITS = {"connection": 200, "message": 700}
_TARGETS = {
    "connection": "120 to 200 characters, two or three lines",
    "message": "300 to 500 characters, four or five short lines",
}

def render_brief(brief: EmailBrief | None, campaign: CampaignBrief | None = None) -> str:
    """The Strategist's plan for this message, as instructions.

    Only the parts of an email brief a message of a few hundred characters can
    honour: a subject strategy, an arc position and a sequence rule are answers
    to questions LinkedIn does not ask.

    `orientation` comes off the campaign rather than the email because it is
    the one sentence that is the same in every piece of copy this campaign
    produces - what the business is, to this reader, in words they could repeat
    to somebody else. It is exactly what move two of the message asks for, and
    without it the writer reaches for the business profile's own description,
    which is written for the company and not for the person reading.
    """
    if brief is None and campaign is None:
        return ""
    fields: tuple[tuple[str, str], ...] = ()
    if campaign is not None:
        fields += (("What this is, to this reader", campaign.orientation),)
    if brief is not None:
        fields += (
            ("The one idea this message makes", brief.single_idea),
            ("What the reader is living with", brief.felt_need),
            ("What they do about it today", brief.status_quo),
            ("Why that keeps failing them", brief.why_it_fails),
            ("The objection to answer", brief.objection),
            ("What to ask for", brief.call_to_action),
            ("Evidence it may spend", ", ".join(brief.evidence_ids)),
            ("Never say", "; ".join(brief.must_not_say)),
        )
    return "\n".join(f"{label}: {value}" for label, value in fields if value)


async def write_message(
    session: ModelSession,
    request: MessageRequest,
    artifacts: KnowledgeArtifacts,
    brief: EmailBrief | None = None,
    campaign: CampaignBrief | None = None,
) -> dict:
    limit = _LIMITS[request.kind]
    # Search descriptions and the user's objective are not evidence.
    reviewed_artifacts = artifacts.model_copy(deep=True)
    if request.confirmed_context.strip():
        reviewed_artifacts.evidence.entries.append(Evidence(
            id="recipient-context", kind=EvidenceKind.FEATURE,
            claim="User-confirmed recipient context", verbatim=request.confirmed_context,
            user_attested=True,
        ))
    reviewer = ClaimReviewer(session)
    # The person this business sells to. The brief names one when a campaign
    # planned this message; a standalone draft has no brief, and the primary
    # segment is a better answer than the nothing that was passed before.
    segment = (
        artifacts.audience.match(campaign.reader_segment, campaign.reader)
        if campaign is not None
        else artifacts.audience.primary()
    )
    variables = {
        **request.model_dump(),
        "limit": limit,
        "target": _TARGETS[request.kind],
        "brief": render_brief(brief, campaign),
        "knowledge": artifacts.render_for_writing(),
        "company": artifacts.business.company_name or "this business",
        "reader": segment.render_for_writing() if segment is not None else "",
        "voice": artifacts.voice.render(),
    }
    task = "Write one message, ready to copy. Return its body only in the requested schema."
    attempts = 2
    for attempt in range(attempts):
        draft = await session.structured(
            role=ROLE_ID, tier=ModelTier.BALANCED, template="linkedin_message",
            variables=variables, task=task, schema=MessageDraft,
        )
        body = draft.body.strip()
        # Blocking: the draft cannot ship as it stands. Advisory: it can, and
        # a rewrite is very likely to be better - so it buys the second turn
        # the forecast already allows and never costs the user a failed run.
        blocking: list[str] = []
        if re.search(r"\{\{|\*\|", body):
            blocking.append("No merge fields: address the named recipient directly.")
        if not body or len(body) > limit:
            blocking.append(
                f"Write between 1 and {limit} characters, including spaces. "
                f"Aim for {_TARGETS[request.kind]}."
            )
        advisory: list[str] = []

        source_review = GateReport()
        if not blocking:
            source_review = await reviewer.review(
                email=Email(position=1, subject="", preview_text="", greeting="", body=body,
                            call_to_action="", sign_off=""),
                brief=brief or EmailBrief(position=1, single_idea=request.objective),
                artifacts=reviewed_artifacts, hints=GateReport(),
            )
            blocking.extend(issue.detail for issue in source_review.blocking)
            advisory.extend(issue.detail for issue in source_review.advisory)

        if not blocking and (not advisory or attempt == attempts - 1):
            return {"body": body, "characters": len(body), "limit": limit,
                    "kind": request.kind, "recipient_name": request.recipient_name,
                    "recipient_url": request.recipient_url,
                    "note": "Draft for review. No message has been sent.",
                    "semantic_review": source_review.semantic_review}
        if attempt == attempts - 1:
            raise OutputValidationError(
                "Message failed checks: " + "; ".join(blocking), role=ROLE_ID
            )
        task = ("Rewrite this draft: " + body + "\nFix all these checks:\n"
                + "\n".join(blocking + advisory))
    raise AssertionError("unreachable")  # pragma: no cover
