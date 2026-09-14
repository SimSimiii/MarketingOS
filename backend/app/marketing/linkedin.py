"""A short outreach draft, with no web access and deterministic fact checks.

The channel has no cold reader - see `EmailCampaignPipeline._phase_message` for
why a panel that grades inbox copy would be grading the wrong artefact - so the
first draft is very nearly the shipped draft. That puts the whole quality
burden on two things that cost nothing: what the writer is shown, and what is
checked mechanically afterwards.

Both were thin, and the messages showed it. A writer handed the business, the
offer and the whole evidence ledger, and nothing at all about the person
reading, writes the only thing that material supports: a description of the
product. The checks then licensed every number in it and passed, because
"could this have been sent to anybody" is not a question about numbers.
"""
import re

from app.ai.model_router import ModelTier
from app.knowledge.artifacts import KnowledgeArtifacts
from app.knowledge.ledger import EvidenceIndex
from app.marketing.briefs import CampaignBrief, EmailBrief
from app.marketing.gates import evidence_gate, placeholder_gate, stock_phrase_gate
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

#: Phrasings that say "this was generated" more loudly than anything the
#: message argues. Checked here rather than left to the prompt's own list
#: because a model asked to avoid its own tics is the reader least likely to
#: notice them - the same reasoning as `stock_phrase_gate`, which this extends
#: rather than replaces.
#:
#: The disclaimers are the worst of them. A sentence insisting the message is
#: not a pitch is only ever written on a pitch, and the reader has seen it
#: before on a pitch.
_TELLS = (
    "no pitch", "not a pitch", "not selling", "nothing to sell",
    "genuinely asking", "genuinely curious", "genuinely interested",
    "just curious", "curious where you", "curious how you", "curious whether you",
    "quick question", "i'll keep this short", "keep this brief", "i'll be brief",
    "came across your profile", "came across your post", "stumbled across your",
    "i noticed you", "noticed that you", "saw that you",
    "reaching out", "reach out to you",
    "keep thinking about", "i've been wondering", "i have been wondering",
    "does this resonate", "if this resonates", "worth a conversation",
    "pick your brain", "hop on a call", "jump on a call", "grab 15",
    "love what you", "impressive work", "impressed by your",
    "no strings", "no obligation", "no agenda",
)

#: Words a message and a confirmed-context note would share by coincidence,
#: so their overlap proves nothing. Deliberately short: the check below is
#: advisory, and a noise list long enough to be safe as a blocker would be a
#: second vocabulary to maintain.
_CONTEXT_NOISE = frozenset({
    "about", "after", "also", "been", "being", "build", "builds", "building", "built",
    "company", "could", "does", "doing", "from", "have", "having", "into", "just",
    "like", "make", "makes", "making", "more", "most", "much", "need", "needs",
    "only", "other", "over", "people", "product", "role", "same", "some", "such",
    "team", "teams", "than", "that", "their", "them", "then", "there", "these",
    "they", "thing", "things", "this", "those", "time", "using", "very", "want",
    "wants", "what", "when", "where", "which", "while", "will", "with", "work",
    "working", "works", "would", "year", "years", "your",
})


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


def _words(text: str) -> set[str]:
    return {
        word
        for word in re.findall(r"[a-z][a-z0-9'’-]{3,}", text.lower())
        if word not in _CONTEXT_NOISE
    }


def _specificity_issues(body: str, request: MessageRequest) -> list[str]:
    """Did this message use the one thing that makes it a message?

    When the user has checked facts about this person, those facts are the
    entire difference between writing to somebody and broadcasting at them.
    A draft that ignores them has produced copy that could be pasted into any
    other conversation, which is the failure this channel actually has.

    Advisory rather than blocking, and the reason is the language field: the
    context is pasted off a LinkedIn profile, usually in English, while the
    message may be written in French or in anything else the user asked for.
    A translated message engages with its context perfectly and shares not one
    token with it. So this buys a rewrite - which is nearly always the right
    correction - and never fails a run on its own.
    """
    if not request.confirmed_context.strip():
        return []
    if _words(request.confirmed_context) & _words(body):
        return []
    return [
        (
            "This message uses nothing the user confirmed about "
            f"{request.recipient_name} - it would read the same sent to anybody. "
            "Open on the one thing from their confirmed context that made this "
            "person worth writing to, in your own words."
        )
    ]


async def write_message(
    session: ModelSession,
    request: MessageRequest,
    artifacts: KnowledgeArtifacts,
    brief: EmailBrief | None = None,
    campaign: CampaignBrief | None = None,
) -> dict:
    limit = _LIMITS[request.kind]
    # Search descriptions and the user's objective are not evidence.
    index = EvidenceIndex(artifacts.evidence, source_text=request.confirmed_context)
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
        blocking = [item.detail for item in evidence_gate(body, index).blocking]
        blocking += [item.detail for item in placeholder_gate(body).blocking]
        if re.search(r"\{\{|\*\|", body):
            blocking.append("No merge fields: address the named recipient directly.")
        if not body or len(body) > limit:
            blocking.append(
                f"Write between 1 and {limit} characters, including spaces. "
                f"Aim for {_TARGETS[request.kind]}."
            )
        advisory = [item.detail for item in stock_phrase_gate(body, _TELLS).blocking]
        advisory += _specificity_issues(body, request)

        if not blocking and (not advisory or attempt == attempts - 1):
            return {"body": body, "characters": len(body), "limit": limit,
                    "kind": request.kind, "recipient_name": request.recipient_name,
                    "recipient_url": request.recipient_url,
                    "note": "Draft for review. No message has been sent."}
        if attempt == attempts - 1:
            raise OutputValidationError(
                "Message failed checks: " + "; ".join(blocking), role=ROLE_ID
            )
        task = ("Rewrite this draft: " + body + "\nFix all these checks:\n"
                + "\n".join(blocking + advisory))
    raise AssertionError("unreachable")  # pragma: no cover
