"""The Email Writer: one email per invocation, from one brief.

One email per model call, not one call for a whole sequence. An email is the
unit of attention, and three of them sharing a single response is how all
three end up saying the same thing in the same shape - the old system learned
this the hard way and the lesson survives the redesign.

The writer never emits JSON. Copy is whitespace, and whitespace does not
survive being a string value inside an object alongside two other emails. It
writes an email the way an email is written, inside the labelled-field
envelope parsed by email_copy.

What it may claim is bounded by the evidence it is handed, and that bound is
checked after the fact by the evidence gate rather than trusted here.
"""

import logging

from app.ai.model_router import ModelTier
from app.knowledge.artifacts import KnowledgeArtifacts
from app.marketing.briefs import CampaignBrief, EmailBrief
from app.marketing.email_copy import Email, EmailCopyError, parse_email, render_email
from app.marketing.exceptions import CraftError
from app.marketing.gates import GateReport
from app.marketing.observer import RunObserver
from app.marketing.reader import PanelRead
from app.marketing.request import CampaignRequest
from app.runtime.model_session import ModelSession

logger = logging.getLogger("marketingos.marketing")

ROLE_ID = "email_writer"

#: A draft that breaks the field protocol gets its own errors back, twice.
#: Past that the email fails and the phase above decides what to do, which is
#: cheaper than looping on a model that has stopped following the format.
_REPAIR_ATTEMPTS = 3


class EmailWriter:
    def __init__(self, session: ModelSession, observer: RunObserver | None = None) -> None:
        self._session = session
        self._observer = observer or RunObserver()

    async def draft(
        self,
        *,
        brief: EmailBrief,
        campaign: CampaignBrief,
        request: CampaignRequest,
        artifacts: KnowledgeArtifacts,
        previous: list[Email],
        opening_move: str = "",
        idea_override: str = "",
        history: str = "",
    ) -> Email:
        """One draft of one email.

        `opening_move` constrains only where the draft starts. It is set when
        several openings are being written for the same brief and compared:
        left free, a model asked for the same email twice writes the same
        email twice, and there is nothing for a cold reader to choose between.

        `idea_override` replaces the claim the email argues with one of the
        alternatives the strategist named. It is the stronger of the two knobs
        and the one that makes a bake-off a bake-off: two drafts that open
        differently on the same claim are one bet phrased twice, and a cold
        reader choosing between them is choosing a first sentence. The brief is
        rewritten rather than annotated, because a writer shown both the idea
        it owns and the idea it is standing in for writes something that hedges
        between them.
        """
        if idea_override:
            brief = brief.model_copy(update={"single_idea": idea_override})
        sections = [f"Write email {brief.position} now."]
        if opening_move:
            sections.append(_opening_constraint(opening_move))
        if history:
            sections.append(history)
        sections.append(_already_sent(previous))
        return await self._write(
            brief=brief,
            campaign=campaign,
            request=request,
            artifacts=artifacts,
            task="\n\n".join(sections),
        )

    async def revise(
        self,
        *,
        draft: Email,
        brief: EmailBrief,
        campaign: CampaignBrief,
        request: CampaignRequest,
        artifacts: KnowledgeArtifacts,
        previous: list[Email],
        gates: GateReport,
        read: PanelRead,
        critique_notes: str = "",
        history: str = "",
    ) -> Email:
        """Rewrite against what actually happened to the draft.

        Four different kinds of feedback arrive here and they are kept
        separate on purpose: the automatic checks are facts (this claim is
        unsupported, this paragraph is 71 words), the reader is behavior (they
        stopped here, they could not say what it sells), the critic is
        judgment, and `history` is what has already been measured and failed.
        Collapsing them into one "feedback" blob is how a rewrite ends up
        politely addressing none of them.
        """
        sections = [
            (
                "This draft was read by someone in your audience who knew nothing about the "
                "product, and checked automatically. Here is what came back."
            ),
            f"--- what you sent ---\n{render_email(draft)}\n--- end ---",
            f"What happened to the reader:\n{read.render()}",
        ]
        if history:
            sections.append(history)
        # Blocking and advisory issues arrive in separate sections, and the
        # difference is the architecture's own rule handed to the writer.
        # A blocking issue is arithmetic - an unsupported figure, a paragraph
        # over the width - and it has to be gone. An advisory is a judgment
        # call the copy may legitimately answer another way: an email arguing
        # from mechanism has spent no evidence on purpose. Both used to arrive
        # under "checks that failed ... every one of them has to be gone in
        # the rewrite", which is how a writer ends up bolting a fact onto an
        # email that was right without it.
        if gates.blocking:
            sections.append(
                "Automatic checks that failed - these are facts, not opinions, and every one "
                f"of them has to be gone in the rewrite:\n{gates.render_blocking()}"
            )
        if gates.advisory:
            sections.append(
                "Worth weighing, not orders - decide, and if you disagree, leave it:\n"
                + "\n".join(f"- {issue.render()}" for issue in gates.advisory)
            )
        if critique_notes:
            sections.append(f"What the conversion critic wants changed:\n{critique_notes}")
        sections.append(
            "Rewrite it. Not a polish - fix what actually happened. If they could not say what "
            "it sells, the promise is not on the page. If they stopped at a line, that line "
            "goes. If their doubt went unanswered, answer it before the ask. Keep what worked, "
            f"keep the same idea ({brief.single_idea or 'as briefed'}), and stay off the ground "
            "already covered.\n\n" + _already_sent(previous)
        )
        return await self._write(
            brief=brief,
            campaign=campaign,
            request=request,
            artifacts=artifacts,
            task="\n\n".join(sections),
        )

    # ------------------------------------------------------------- internals

    async def _write(
        self,
        *,
        brief: EmailBrief,
        campaign: CampaignBrief,
        request: CampaignRequest,
        artifacts: KnowledgeArtifacts,
        task: str,
    ) -> Email:
        # The facts this email plausibly needs, not everything true about the
        # business. See EvidenceLedger.slice_for: the full ledger in a writing
        # prompt is both the largest cost in a run and the standing temptation
        # that the brief's `must_not_say` exists to resist.
        slice_ = artifacts.evidence.slice_for(brief.evidence_ids, brief.objection)
        segment = artifacts.audience.match(campaign.reader_segment, campaign.reader)
        system_prompt = self._session.render(
            "writer",
            {
                "request": request.request,
                "reader": campaign.reader or "one person who has never heard of this company",
                "segment": (
                    segment.render_for_writing()
                    if segment is not None
                    else "Nothing was established about this person beyond the line above. "
                    "Write to the situation the brief describes and claim nothing about them."
                ),
                "objection_detail": artifacts.objection_detail(brief.objection),
                "promise": campaign.promise,
                "arc": campaign.render_arc(),
                "brief": brief.render(),
                "evidence": _evidence_for(brief, artifacts),
                "knowledge": artifacts.render_for_writing(slice_),
                "voice": artifacts.voice.render(),
                "voice_notes": campaign.voice_notes or "nothing beyond the brand voice above",
                "sender": _sender(request, artifacts),
            },
        )

        message = task
        last_error: EmailCopyError | None = None
        response = ""
        for repair in range(_REPAIR_ATTEMPTS):
            response = await self._session.text(
                role=ROLE_ID,
                tier=ModelTier.DEEP,
                system_prompt=system_prompt,
                task=message,
            )
            try:
                return parse_email(response, brief.position)
            except EmailCopyError as exc:
                last_error = exc
                # Said out loud, because a repair is a whole extra deep-tier
                # call and the reasons were invisible: they went back to the
                # model and nowhere else, so nobody could tell whether the
                # writer was fighting one rule or twenty. In a measured run,
                # 5 of 12 writer calls were repairs and there was no record of
                # what any of them was for.
                logger.info(
                    "writer: email %d draft rejected on repair %d - %s",
                    brief.position,
                    repair + 1,
                    exc,
                )
                self._observer.on_repair(brief.position, repair + 1, str(exc))
                message = (
                    f"That draft cannot be sent as it stands: {exc}\n\n"
                    "Send the whole email again, corrected, in the labelled-field format - "
                    "every label on its own line, BODY last, nothing before or after it."
                )

        raise CraftError(
            f"Could not produce a sendable email {brief.position}: {last_error}",
            position=brief.position,
            raw_response=response[:2000],
        )


def _sender(request: CampaignRequest, artifacts: KnowledgeArtifacts) -> str:
    """Who signs it, phrased as an instruction rather than as a field.

    Without a name the only honest sign-off is the company, and the prompt has
    to say so - a writer left to guess invents "Sarah from the growth team",
    which is a real person's name on a stranger's email and the one kind of
    placeholder no gate can catch.
    """
    company = artifacts.business.company_name or "the product"
    if request.sender:
        return (
            f"This email is from {request.sender}. Sign it as that person - their name, and "
            f"{company} beside it. You may write in the first person singular, because there "
            "is somebody to be."
        )
    return (
        f"Nobody has told us who this is from, so sign it as {company} and a role that exists "
        "in the material above. Never invent a person's name: a made-up sender is the one "
        "thing on the page a reader can catch you out on for certain."
    )


def _evidence_for(brief: EmailBrief, artifacts: KnowledgeArtifacts) -> str:
    """The facts this email was assigned, pulled out of the ledger in full.

    Assigned evidence is repeated here even though the whole ledger is also in
    the prompt: the difference between "these are the facts you may use" and
    "this is the fact this email is built on" is the difference between an
    email that mentions a proof point and one that argues from it.
    """
    entries = [entry for id_ in brief.evidence_ids if (entry := artifacts.evidence.get(id_))]
    if not entries:
        return (
            "No specific evidence was assigned to this email. Use the ledger below, and if it "
            "has nothing that fits, make no factual claim at all rather than a vague one."
        )
    return "\n".join(
        f"- [{entry.id}] {entry.claim}\n      the source says: \"{entry.verbatim}\""
        for entry in entries
    )


def _opening_constraint(opening_move: str) -> str:
    """Where this particular draft has to start, when that is being varied.

    Deliberately the only thing pinned down. Constrain the argument as well as
    the opening and the candidates stop being alternatives and become the same
    email with three different first paragraphs, which is the failure this is
    supposed to prevent.
    """
    if not opening_move:
        return ""
    return (
        "One constraint on this draft beyond the brief - where it starts:\n\n"
        f"{opening_move}\n\n"
        "The subject line has to follow from that opening rather than from some other one you "
        "might have written. Everything after the first two sentences is your call."
    )


def _already_sent(previous: list[Email]) -> str:
    """The emails the reader has already had, verbatim.

    A digest would let the writer repeat a line it cannot see - which is
    exactly the failure the overlap gate would then catch, one expensive model
    call later.
    """
    if not previous:
        return "Nothing has been sent yet - this is the first email they get from you."
    sent = "\n\n".join(
        f"--- email {email.position} ---\n{render_email(email)}"
        for email in sorted(previous, key=lambda item: item.position)
    )
    return (
        "Already written and sent, in full. Do not reuse an angle, a proof, an opening move or "
        "a phrase from any of them - and never refer back to them, the reader may have missed "
        f"every one:\n\n{sent}"
    )
