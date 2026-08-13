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

import logging
from collections.abc import Callable

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
from app.knowledge.corpus import SourceCorpus, collapse
from app.knowledge.ledger import (
    Evidence,
    EvidenceKind,
    EvidenceLedger,
    EvidenceStrength,
)
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

        progress("profile", "Reading the material for what this business is and sells")
        profile = await self._profile(corpus)

        progress("evidence", "Collecting every fact the copy will be allowed to claim")
        ledger = await self._evidence(corpus)

        progress("voice", "Learning how this company sounds in its own words")
        voice = await self._voice(corpus)

        progress("audience", "Working out who buys this and why they hesitate")
        audience = await self._audience(corpus, profile, ledger)

        artifacts = KnowledgeArtifacts(
            business=profile.business,
            offer=profile.offer,
            evidence=ledger,
            voice=voice,
            audience=audience,
            source_document_ids=[document.id for document in corpus.documents],
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

    async def _evidence(self, corpus: SourceCorpus) -> EvidenceLedger:
        """Extract candidate facts batch by batch, then keep only the ones
        whose supporting quote is really in the source."""
        entries: list[Evidence] = []
        for batch in _batches(corpus, _EVIDENCE_BATCH_CHARS):
            material = "\n\n".join(
                f"<document id=\"{document.id}\" title=\"{document.title}\">\n"
                f"{document.content[:_EVIDENCE_BATCH_CHARS]}\n</document>"
                for document in batch
            )
            result = await self._session.structured(
                role=ROLE_ID,
                tier=ModelTier.BALANCED,
                template="knowledge_evidence",
                variables={"material": material},
                task=(
                    "List every checkable fact in these documents. Quote the exact supporting "
                    "text for each one and give the document id it came from."
                ),
                schema=_EvidencePass,
            )
            by_id = {document.id: document for document in batch}
            for draft in result.entries:
                document = by_id.get(draft.document_id) or (batch[0] if len(batch) == 1 else None)
                haystack = document.content if document else corpus.text
                if not _quote_is_real(draft.verbatim, haystack):
                    logger.info(
                        "knowledge compiler: dropped unverifiable evidence %r", draft.claim[:80]
                    )
                    continue
                entries.append(
                    Evidence(
                        id=f"E{len(entries) + 1}",
                        kind=draft.kind,
                        claim=collapse(draft.claim),
                        verbatim=collapse(draft.verbatim, 400),
                        source=document.source if document else "",
                        document_id=document.id if document else None,
                        strength=draft.strength,
                    )
                )
        return EvidenceLedger(entries=entries)

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


def _batches(corpus: SourceCorpus, budget: int) -> list[list]:
    """Group documents into calls, keeping each call under the budget. A single
    document over budget gets its own call and is truncated there."""
    batches: list[list] = []
    current: list = []
    size = 0
    for document in corpus.documents:
        length = len(document.content)
        if current and size + length > budget:
            batches.append(current)
            current, size = [], 0
        current.append(document)
        size += length
    if current:
        batches.append(current)
    return batches


def _quote_is_real(quote: str, haystack: str) -> bool:
    """Is this quote actually in the source, ignoring how whitespace fell?

    Loaders reflow text (markdown conversion, PDF extraction), so an exact
    match is too strict; a normalized substring is the honest test.
    """
    needle = collapse(quote).lower()
    if len(needle) < _MIN_QUOTE_CHARS:
        return False
    return needle in collapse(haystack).lower()
