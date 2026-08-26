"""The Knowledge Compiler: raw material in, cited artifacts out.

Compilation happens once per business and is read by every campaign after it,
which is what makes it worth spending real model time on. It is also the only
role in the system allowed to reach outside the prompt for information.

Two rules make its output trustworthy downstream. First, every factual entry
must quote the text that supports it. Second - and this is the part a prompt
alone cannot deliver - code checks those quotes actually appear in the source
before the entry is kept. A compiler that hallucinates a testimonial would
otherwise poison every campaign written afterwards, and it would do it
invisibly, because nothing further down ever sees the original page.
"""

import asyncio
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel, Field

from app.ai.model_router import ModelTier
from app.knowledge.artifacts import (
    AudienceModel,
    BusinessProfile,
    Gap,
    GapReport,
    KnowledgeArtifacts,
    OfferSheet,
    VoiceProfile,
)
from app.knowledge.corpus import Document, SourceCorpus, collapse, fold
from app.knowledge.ledger import (
    Evidence,
    EvidenceKind,
    EvidenceLedger,
    EvidenceStrength,
)
from app.knowledge.taxonomy import FactCategory, classify
from app.runtime.exceptions import ModelRuntimeError
from app.runtime.model_session import ModelSession

logger = logging.getLogger("marketingos.knowledge")

ROLE_ID = "knowledge_compiler"

#: How much material one evidence-extraction call reads. Small enough that the
#: model can hold every page in attention while quoting from it - accuracy of
#: the quote is the entire product of this pass.
_EVIDENCE_BATCH_CHARS = 14_000
_PROFILE_DIGEST_CHARS = 40_000
_AUDIENCE_DIGEST_CHARS = 24_000
_VOICE_DIGEST_CHARS = 20_000

#: Ceiling on everything the evidence pass reads, across every call.
#:
#: There has to be one, because the number of calls this pass makes is now
#: driven by how much material there is rather than by how many documents
#: there are - which is the point, and is also how a single 20 MB upload
#: could otherwise turn one compile into an open cheque. Generous against the
#: real case: a full crawl at the default twelve pages plus a couple of
#: uploaded documents is well inside it. Whatever it cuts off is reported.
_EVIDENCE_TOTAL_CHARS = 240_000

#: Evidence readings in flight at once. The same order of concurrency the loop
#: already runs elsewhere - a bake-off reads four candidates by three personas
#: at the same time - so this is not new pressure on the CLI, and it turns the
#: longest serial stretch in a run into a handful of rounds.
_EVIDENCE_CONCURRENCY = 4

_BLOCK_SPLIT_RE = re.compile(r"\n\s*\n")

#: Shortest quote that can support a claim. Below this the "verbatim" is a
#: fragment that would match almost any page.
_MIN_QUOTE_CHARS = 12


class _ProfilePass(BaseModel):
    business: BusinessProfile
    offer: OfferSheet


class _EvidenceDraft(BaseModel):
    """One candidate fact, before code has checked its quote is real."""

    kind: EvidenceKind = EvidenceKind.FEATURE
    claim: str
    verbatim: str
    document_id: str = ""
    strength: EvidenceStrength = EvidenceStrength.MODERATE
    #: Which shelf of the knowledge base this belongs on. A plain string
    #: rather than the enum on purpose: an unrecognised value here must cost
    #: one entry's classification, not the whole batch. Anything the model
    #: does not answer, or answers wrongly, is classified in code instead -
    #: see `_shelf`.
    category: str = ""


class _EvidencePass(BaseModel):
    entries: list[_EvidenceDraft] = Field(default_factory=list)


class _VoicePass(BaseModel):
    voice: VoiceProfile


class _AudiencePass(BaseModel):
    audience: AudienceModel


ProgressHook = Callable[[str, str], None]


class KnowledgeCompiler:
    """Turns a SourceCorpus into the artifacts every campaign is written from."""

    def __init__(self, session: ModelSession) -> None:
        self._session = session

    async def compile(
        self,
        corpus: SourceCorpus,
        on_progress: ProgressHook | None = None,
    ) -> KnowledgeArtifacts:
        def progress(stage: str, message: str) -> None:
            if on_progress is not None:
                on_progress(stage, message)

        if corpus.is_empty:
            # Nothing to read is a legitimate state - the user may have given
            # only a product description. Say so in the artifacts rather than
            # inventing a business.
            return KnowledgeArtifacts(
                gaps=GapReport(gaps=[_NO_MATERIAL_GAP]),
                notes=["The user provided no website, document or image to read."],
            )

        # Three of the four passes read only the material, so they are three
        # independent questions about the same pages and there is no reason to
        # ask them one at a time. Run in sequence - which is how this stood -
        # a normal twelve-page site is ten serial deep-tier calls before the
        # Strategist can begin, minutes of a run spent waiting for answers
        # that never depended on each other. Only the audience pass has real
        # inputs: it is written from the profile and the ledger, so it waits.
        progress(
            "reading",
            f"Reading {len(corpus.documents)} document(s): what the business is, every fact "
            "the copy may claim, and how the company sounds",
        )
        profile, evidence, voice = await asyncio.gather(
            self._profile(corpus), self._evidence(corpus), self._voice(corpus)
        )
        ledger, intake = evidence
        progress(
            "evidence",
            f"{len(ledger.entries)} fact(s) the copy may claim, from "
            f"{intake.readings} reading(s)"
            + (
                f" - {intake.unverifiable} candidate(s) were dropped because their quote is "
                "not really in the source"
                if intake.unverifiable
                else ""
            ),
        )

        progress("audience", "Working out who buys this and why they hesitate")
        audience = await self._audience(corpus, profile, ledger)

        artifacts = KnowledgeArtifacts(
            business=profile.business,
            offer=profile.offer,
            evidence=ledger,
            voice=voice,
            audience=audience,
            source_document_ids=[document.id for document in corpus.documents],
            notes=intake.notes(),
        )
        artifacts.gaps = find_gaps(artifacts)
        progress(
            "compiled",
            f"Knowledge compiled: {len(ledger.entries)} facts, "
            f"{len(audience.segments)} segment(s), {len(artifacts.gaps.unanswered)} gap(s)",
        )
        return artifacts

    # -------------------------------------------------------------- passes

    async def _profile(self, corpus: SourceCorpus) -> _ProfilePass:
        return await self._session.structured(
            role=ROLE_ID,
            tier=ModelTier.BALANCED,
            template="knowledge_profile",
            variables={"material": corpus.digest(_PROFILE_DIGEST_CHARS)},
            task="Read the material and write down what this business is and what it sells.",
            schema=_ProfilePass,
        )

    async def _evidence(self, corpus: SourceCorpus) -> tuple[EvidenceLedger, "_Intake"]:
        """Every reading of the material, extracted and then verified.

        The readings are independent - each one sees its own pages and quotes
        from them - so they are made concurrently. They used to run one after
        another, which on a normal twelve-page site is seven serial deep-tier
        calls, several minutes of a run in which nothing else can start,
        for exactly the same answer and exactly the same money.

        Ids are assigned afterwards, in reading order, so a compile of the
        same material twice produces the same E1..En however the calls
        happened to return.
        """
        plan = _readings(corpus, _EVIDENCE_BATCH_CHARS, _EVIDENCE_TOTAL_CHARS)
        gate = asyncio.Semaphore(_EVIDENCE_CONCURRENCY)

        async def extract(batch: list["_Reading"]) -> list[_EvidenceDraft] | BaseException:
            material = "\n\n".join(reading.render() for reading in batch)
            async with gate:
                try:
                    result = await self._session.structured(
                        role=ROLE_ID,
                        tier=ModelTier.BALANCED,
                        template="knowledge_evidence",
                        variables={"material": material},
                        task=(
                            "List every checkable fact in these documents. Quote the exact "
                            "supporting text for each one and give the document id it came from."
                        ),
                        schema=_EvidencePass,
                    )
                except ModelRuntimeError as exc:
                    # One reading that never came back costs the facts on those
                    # pages, not the compile - and a compile is the artifact
                    # every future campaign for this business is written from,
                    # so finishing with a smaller ledger and saying so beats
                    # failing and starting over.
                    logger.warning("knowledge compiler: one reading did not come back - %s", exc)
                    return exc
            return result.entries

        results = await asyncio.gather(*(extract(batch) for batch in plan.batches))

        entries: list[Evidence] = []
        intake = _Intake(readings=len(plan.batches), unread=plan.unread)
        for batch, drafts in zip(plan.batches, results, strict=True):
            if isinstance(drafts, BaseException):
                intake.failed_readings += 1
                continue
            by_id = {reading.document.id: reading.document for reading in batch}
            for draft in drafts:
                document = by_id.get(draft.document_id) or (
                    batch[0].document if len({reading.document.id for reading in batch}) == 1
                    else None
                )
                haystack = document.content if document else corpus.text
                intake.proposed += 1
                if not _quote_is_real(draft.verbatim, haystack):
                    intake.unverifiable += 1
                    logger.info(
                        "knowledge compiler: dropped unverifiable evidence %r", draft.claim[:80]
                    )
                    continue
                claim = collapse(draft.claim)
                verbatim = collapse(draft.verbatim, 400)
                entries.append(
                    Evidence(
                        id=f"E{len(entries) + 1}",
                        kind=draft.kind,
                        claim=claim,
                        verbatim=verbatim,
                        source=document.source if document else "",
                        document_id=document.id if document else None,
                        strength=draft.strength,
                        category=_shelf(draft, claim, verbatim),
                    )
                )
        return EvidenceLedger(entries=entries), intake

    async def _voice(self, corpus: SourceCorpus) -> VoiceProfile:
        """Learn the company's voice from copy it actually published.

        Exemplars are the payload here, so an exemplar that is not verbatim is
        worse than none - it would teach a writer to sound like a model's idea
        of this company. Unverified ones are dropped, and a profile left with
        no exemplars is honestly reported as the house default.
        """
        result = await self._session.structured(
            role=ROLE_ID,
            tier=ModelTier.BALANCED,
            template="knowledge_voice",
            variables={"material": corpus.digest(_VOICE_DIGEST_CHARS)},
            task="Describe how this company writes, and quote passages that show it.",
            schema=_VoicePass,
        )
        voice = result.voice
        voice.exemplars = [
            collapse(passage, 600)
            for passage in voice.exemplars
            if _quote_is_real(passage, corpus.text)
        ][:5]
        if not voice.exemplars:
            default = VoiceProfile.house_default()
            # Keep whatever the model could observe about register even when
            # no quotable passage survived - it is still better than nothing.
            default.tone = voice.tone or default.tone
            return default
        voice.learned = True
        return voice

    async def _audience(
        self, corpus: SourceCorpus, profile: _ProfilePass, ledger: EvidenceLedger
    ) -> AudienceModel:
        result = await self._session.structured(
            role=ROLE_ID,
            tier=ModelTier.DEEP,
            template="knowledge_audience",
            variables={
                "business": profile.business.render(),
                "offer": profile.offer.render(),
                "evidence": ledger.render(),
                "material": corpus.digest(_AUDIENCE_DIGEST_CHARS),
            },
            task=(
                "Work out who actually buys this, what they are trying to get done, and the "
                "real reasons they would not buy."
            ),
            schema=_AudiencePass,
        )
        audience = result.audience
        # An objection pointing at evidence that does not exist would send a
        # writer looking for an answer it cannot find.
        known = ledger.ids
        for objection in audience.objections:
            objection.evidence_ids = [id_ for id_ in objection.evidence_ids if id_ in known]
        return audience


def _shelf(draft: _EvidenceDraft, claim: str, verbatim: str) -> FactCategory:
    """Which shelf a fact lands on: the model's answer if it gave a real one.

    The model read the whole page and knows that "we never train on your data"
    is a trust fact rather than a technical one, which a lexicon over that one
    sentence cannot. It also costs nothing to ask - it is another field in a
    call that was already being made. But it is a model, so the answer is a
    suggestion: anything unrecognised falls through to the classifier, which
    is deterministic and never wrong in an interesting way.
    """
    try:
        return FactCategory(draft.category.strip().lower())
    except ValueError:
        return classify(f"{claim} {verbatim}", str(draft.kind))


# ---------------------------------------------------------------------- gaps

_NO_MATERIAL_GAP = Gap(
    id="G-material",
    missing="No website, document or image was provided",
    impact="every specific in the copy would have to be invented - it will read as generic",
    question="What is your website, or what can you upload about the product?",
    severity="blocking",
)


def find_gaps(artifacts: KnowledgeArtifacts) -> GapReport:
    """What is missing, computed rather than asked of a model.

    A gap only belongs here if it changes the copy. "No employee count" is
    trivia; "no price anywhere in the material" decides whether an email can
    name one, so it is a gap.
    """
    gaps: list[Gap] = []

    priced = any(plan.price for plan in artifacts.offer.plans) or bool(artifacts.offer.free_entry)
    if not priced:
        gaps.append(
            Gap(
                id="G-price",
                missing="No price or free-entry terms found",
                impact="emails cannot name a price, a trial length or a risk reversal",
                question="What does it cost, and is there a free trial or free tier?",
                severity="significant",
            )
        )
    if not artifacts.offer.calls_to_action:
        gaps.append(
            Gap(
                id="G-cta",
                missing="No action a reader can actually be asked to take",
                impact="every email would have to end on a vague ask",
                question="What should a reader do next - start a trial, book a demo, reply?",
                severity="blocking",
            )
        )
    if not artifacts.evidence.of_kind(EvidenceKind.TESTIMONIAL, EvidenceKind.CUSTOMER):
        gaps.append(
            Gap(
                id="G-proof",
                missing="No customer names, quotes or case studies found",
                impact="the copy can describe the product but cannot prove anyone uses it",
                question="Which customers or quotes may we name?",
                severity="significant",
            )
        )
    if not artifacts.evidence.of_kind(EvidenceKind.METRIC):
        gaps.append(
            Gap(
                id="G-numbers",
                missing="No measurable results found",
                impact="claims stay qualitative, and adjectives convert worse than numbers",
                question="What measurable result do customers get, and how do you know?",
                severity="significant",
            )
        )
    if not artifacts.voice.learned:
        gaps.append(
            Gap(
                id="G-voice",
                missing="No existing copy to learn the brand voice from",
                impact="the emails will sound competent but not like this company",
                question="Can you share two or three emails or posts you have sent?",
                severity="minor",
            )
        )
    if not artifacts.audience.segments:
        gaps.append(
            Gap(
                id="G-audience",
                missing="Who buys this could not be established from the material",
                impact="the copy is written to a guess",
                question="Who is your best customer, in one sentence?",
                severity="blocking",
            )
        )
    return GapReport(gaps=gaps)


# ------------------------------------------------------------------ internals


@dataclass(frozen=True)
class _Reading:
    """One slice of one document, as one extraction call will see it."""

    document: Document
    text: str
    #: Which slice of the document this is, and how many there are. Told to
    #: the model so it does not report a sentence as the start of a page when
    #: it is the middle of one.
    part: int = 1
    parts: int = 1

    def render(self) -> str:
        where = (
            f' part="{self.part} of {self.parts}"' if self.parts > 1 else ""
        )
        return (
            f'<document id="{self.document.id}" title="{self.document.title}"{where}>\n'
            f"{self.text}\n</document>"
        )


@dataclass
class _Intake:
    """What the evidence pass read, proposed and kept.

    Recorded because every one of these numbers used to be invisible. A
    compile that read half a page, or threw away a third of what it found
    because the quotes did not match, produced a thin ledger and a thin
    campaign, and looked exactly like a business with little to say.
    """

    readings: int = 0
    failed_readings: int = 0
    proposed: int = 0
    unverifiable: int = 0
    #: Characters of material the reading budget could not reach.
    unread: int = 0

    @property
    def kept(self) -> int:
        return self.proposed - self.unverifiable

    def notes(self) -> list[str]:
        notes: list[str] = []
        if self.unverifiable:
            notes.append(
                f"{self.unverifiable} of {self.proposed} candidate fact(s) were discarded "
                "because the quote supporting them could not be found in the source."
            )
        if self.failed_readings:
            notes.append(
                f"{self.failed_readings} of {self.readings} reading(s) of the material did not "
                "come back - facts on those pages are missing from this compile."
            )
        if self.unread:
            notes.append(
                f"{self.unread:,} characters of material were past the reading budget and were "
                "not read."
            )
        return notes


def _split(text: str, budget: int) -> list[str]:
    """One document's text in pieces no larger than `budget`, cut on blank
    lines so a piece never starts mid-sentence."""
    if len(text) <= budget:
        return [text]
    pieces: list[str] = []
    current: list[str] = []
    size = 0
    for block in _BLOCK_SPLIT_RE.split(text):
        if not block.strip():
            continue
        if size and size + len(block) > budget:
            pieces.append("\n\n".join(current))
            current, size = [], 0
        # A single block over budget is cut where it has to be: the
        # alternative is one call carrying a whole book.
        while len(block) > budget:
            pieces.append(block[:budget])
            block = block[budget:]
        current.append(block)
        size += len(block) + 2
    if current:
        pieces.append("\n\n".join(current))
    return pieces


@dataclass(frozen=True)
class _ReadingPlan:
    """Every call the evidence pass will make, and what it could not reach."""

    batches: list[list[_Reading]]
    unread: int = 0


def _readings(corpus: SourceCorpus, budget: int, total: int) -> _ReadingPlan:
    """Every call the evidence pass will make, and what each one reads.

    A document longer than one call's budget used to be *truncated* to it -
    `document.content[:budget]` - so everything past 14,000 characters was
    never read by this pass on any code path, ever. That is the same "all or
    nothing" failure the corpus module was written to remove, still living in
    the one pass whose entire product is the facts the copy may claim, and it
    bit hardest on exactly the pages worth reading: a long pricing table, a
    customers page with eight case studies, an uploaded PDF.

    Long documents are now read in several passes instead. The whole thing is
    bounded by `total`, because a 20 MB upload should cost a compile rather
    than an open cheque, and whatever the bound cuts off is reported rather
    than dropped silently.
    """
    readings: list[_Reading] = []
    spent = 0
    unread = 0
    for document in corpus.documents:
        pieces = _split(document.content, budget)
        for index, piece in enumerate(pieces, start=1):
            if spent + len(piece) > total:
                unread += len(piece)
                continue
            spent += len(piece)
            readings.append(
                _Reading(document=document, text=piece, part=index, parts=len(pieces))
            )
    if unread:
        logger.warning(
            "knowledge compiler: %d characters past the %d-character reading budget", unread, total
        )

    # One call per reading where a document needed splitting; several small
    # documents share a call, which is what keeps a twelve-page site to a
    # handful of calls rather than twelve.
    batches: list[list[_Reading]] = []
    current: list[_Reading] = []
    size = 0
    for reading in readings:
        if current and size + len(reading.text) > budget:
            batches.append(current)
            current, size = [], 0
        current.append(reading)
        size += len(reading.text)
    if current:
        batches.append(current)
    return _ReadingPlan(batches=batches, unread=unread)


def _quote_is_real(quote: str, haystack: str) -> bool:
    """Is this quote actually in the source, ignoring how it was typeset?

    Loaders reflow text (markdown conversion, PDF extraction), so an exact
    match is too strict; a normalized substring is the honest test.

    Typography is normalized for the same reason whitespace is, and it was
    the more expensive of the two. Published pages come out of a CMS with
    curly quotes, curly apostrophes and en dashes; a model asked to quote one
    back answers in plain ASCII about half the time. Every one of those was a
    real fact, correctly quoted, thrown away here for a character - and the
    entries it hit hardest were testimonials, which is the one kind of
    evidence the preflight will stop a whole run for the lack of.
    """
    needle = fold(quote)
    if len(needle) < _MIN_QUOTE_CHARS:
        return False
    return needle in fold(haystack)
