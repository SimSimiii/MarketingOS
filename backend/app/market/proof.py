"""Looking outside the company's own website for someone who vouched for it.

The gap this closes was measured rather than guessed. A real run compiled 162
facts about a business and reported:

    "No customer names, quotes or case studies found - the copy can describe
    the product but cannot prove anyone uses it"

Then `attributions: 0` on the receipt: the finished email argued from nothing
anybody had vouched for, because there was nothing. And no rewrite has ever
added a proof the material did not contain, so the craft loop spent its budget
rewording an unprovable claim.

The material did not contain it. That does not mean it does not exist. A
company with no testimonial on its own site routinely has a review on a
marketplace, a mention in a comparison post, a customer who wrote about the
integration, a launch thread where somebody said it worked. The company knows
this and never thought to put it in a marketing tool.

So this role goes and finds it. What it produces is deliberately **not**
evidence: it is a *candidate*, and it waits for the user to say yes.

That queue is not friction to be optimised away. A claim about a company,
sourced from a page that company does not control, is the one kind of fact
where being wrong is not a quality problem - it is the user's name under
somebody else's sentence. The person whose company it is takes ten seconds to
know whether a quotation is real, and no amount of model confidence
substitutes for that. Approval is also the moment the user learns the system
found something they had forgotten they had, which is the moment the product
stops being a text generator.
"""

import logging
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

from app.ai.base import ResearchTool
from app.ai.model_router import ModelTier
from app.knowledge.artifacts import BusinessProfile
from app.knowledge.ledger import Evidence, EvidenceKind, EvidenceStrength
from app.runtime.model_session import ModelSession

logger = logging.getLogger("marketingos.market")

ROLE_ID = "proof_hunter"

#: What a found proof can be. A narrower list than `EvidenceKind` because
#: these are the only kinds worth searching the open web for: everything else
#: a company publishes about itself, and its own site is a better source.
class ProofKind(StrEnum):
    #: Somebody said it worked, in their own words.
    TESTIMONIAL = "testimonial"
    #: A named company that uses it.
    CUSTOMER = "customer"
    #: A number somebody other than the company attached to it.
    OUTCOME = "outcome"
    #: A review with a rating, on a marketplace or review site.
    REVIEW = "review"
    #: Being listed, integrated or partnered with somewhere credible.
    LISTING = "listing"
    #: Coverage, an award, a mention that carries weight.
    MENTION = "mention"


_EVIDENCE_KIND: dict[ProofKind, EvidenceKind] = {
    ProofKind.TESTIMONIAL: EvidenceKind.TESTIMONIAL,
    ProofKind.CUSTOMER: EvidenceKind.CUSTOMER,
    ProofKind.OUTCOME: EvidenceKind.METRIC,
    ProofKind.REVIEW: EvidenceKind.TESTIMONIAL,
    ProofKind.LISTING: EvidenceKind.INTEGRATION,
    ProofKind.MENTION: EvidenceKind.AWARD,
}


class ProofStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ProofCandidate(BaseModel):
    """Something the web says about this company, waiting to be confirmed."""

    kind: ProofKind = ProofKind.MENTION
    #: The claim in a form copy could use: "Acme cut onboarding from 3 days to
    #: 20 minutes". Never the URL, never the publication.
    claim: str
    #: The exact sentence on the page. This is what the evidence gate will
    #: check a draft against once approved, so a paraphrase here poisons
    #: everything downstream - it licenses words nobody wrote.
    verbatim: str = ""
    #: Where it was read. Required: a proof without a source is an assertion
    #: with a nicer provenance story.
    url: str = ""
    #: Who said it - the person, the company, the publication.
    attributed_to: str = ""
    #: Where the page lives, for the user's judgment: "g2.com", "a customer's
    #: engineering blog", "Hacker News".
    venue: str = ""
    #: What the hunter thinks the odds are this is really about this company
    #: and really says what it says. Advisory to the user, never a gate.
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    #: Why this might not be what it looks like - a same-named company, an old
    #: version of the product, a review of a competitor that mentions us. The
    #: field that makes the approval queue a ten-second decision instead of a
    #: research task.
    caveat: str = ""
    status: ProofStatus = ProofStatus.PENDING
    found_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("url")
    @classmethod
    def _normalize(cls, value: str) -> str:
        url = value.strip()
        if url and not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        return url

    @property
    def usable(self) -> bool:
        """Whether this could become evidence at all. A candidate with no
        quotation cannot: the gate downstream licenses copy by matching
        against verbatim text, so an entry without any is an entry that
        licenses nothing and can only mislead the writer into thinking it
        does."""
        return bool(self.claim.strip() and self.verbatim.strip() and self.url)

    def as_evidence(self, evidence_id: str) -> Evidence:
        """The ledger entry this becomes once a human says yes.

        `strength` is never STRONG, however good the find. Strong is reserved
        for a specific verifiable fact the company states about itself, which
        the user is accountable for; this is a sentence somebody else wrote on
        a page neither of us controls, and the copy should lean on it
        accordingly.
        """
        return Evidence(
            id=evidence_id,
            kind=_EVIDENCE_KIND[self.kind],
            claim=self.claim,
            verbatim=self.verbatim,
            source=self.url,
            strength=(
                EvidenceStrength.MODERATE
                if self.confidence >= 0.7
                else EvidenceStrength.WEAK
            ),
        )

    def render(self) -> str:
        who = f" - {self.attributed_to}" if self.attributed_to else ""
        return f"[{self.kind}] {self.claim}{who} ({self.venue or self.url})"


class ProofHunt(BaseModel):
    """One pass over the open web, and what it turned up."""

    candidates: list[ProofCandidate] = Field(default_factory=list)
    #: What was searched for. Reported so an empty hunt is a finding the user
    #: can act on ("nobody has written about us anywhere") rather than a
    #: silence they have to interpret.
    searched: list[str] = Field(default_factory=list)
    #: The hunter's own account of why it found little, where it did.
    note: str = ""

    @property
    def usable(self) -> list[ProofCandidate]:
        return [candidate for candidate in self.candidates if candidate.usable]


class ProofHunter:
    """Searches the web for third-party proof about one business."""

    def __init__(self, session: ModelSession) -> None:
        self._session = session

    async def hunt(
        self, business: BusinessProfile, website: str = "", limit: int = 8
    ) -> ProofHunt:
        hunt = await self._session.structured(
            role=ROLE_ID,
            tier=ModelTier.BALANCED,
            template="proof_hunt",
            variables={
                "company": business.company_name or "this company",
                "what_it_does": business.what_it_does,
                "category": business.category,
                "website": website,
                "limit": limit,
            },
            task=(
                "Search now. Report only things you actually found on a page you can name, "
                "with the sentence quoted exactly as it appears there."
            ),
            schema=ProofHunt,
            tools=[ResearchTool.WEB_SEARCH, ResearchTool.WEB_FETCH],
        )
        # A candidate with no quotation or no URL is dropped here rather than
        # shown to the user, because there is nothing for them to judge: the
        # decision the queue asks for is "is this sentence really on that
        # page", and both halves of that question have to be present.
        dropped = len(hunt.candidates) - len(hunt.usable)
        if dropped:
            logger.info("proof: discarded %d candidate(s) with no quote or source", dropped)
        hunt.candidates = hunt.usable
        return hunt


def next_evidence_id(existing: set[str]) -> str:
    """An id for an approved proof that cannot collide with the compiler's.

    The compiler numbers its entries E1, E2, ... and recompiles whenever the
    material changes, so an approved proof numbered into that same sequence
    would be silently reassigned to a different fact the next time the user
    uploads a page. A separate prefix means an id in a shipped email still
    points at the fact it pointed at when the copy was written.
    """
    used = {item for item in existing if item.startswith("P")}
    index = 1
    while f"P{index}" in used:
        index += 1
    return f"P{index}"
