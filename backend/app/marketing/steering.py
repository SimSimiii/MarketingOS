"""What the user chose to steer, before a run, and how the run keeps to it.

Optional from end to end. A campaign with no steering takes exactly the path
it took before this existed: `apply_steering` returns the brief untouched, the
brief renders no extra section, and the gate has nothing to compare against.
Nothing on the form becomes required because this exists.

Three things are kept apart on purpose, because a user ticking a box is not
a source of truth:

  - **usable** facts are ledger entries the evidence gate already licenses.
    Including one assigns it to an email, so it is argued from rather than
    mentioned.
  - **strategic** context - audiences, objections, competition, which action
    to ask for - shapes the plan and is never stated as a fact.
  - **to confirm** is anything the material does not establish well enough to
    state: a weak or scope-inferred fact, a price with no ledger entry behind
    it. Selecting it makes it context for the plan and nothing more.
    Selecting a fact does not verify it.

Choices are applied in code, once, to the brief the Strategist produced, and
ride on each `EmailBrief` from there. Every rewrite, critique and sequence
rework renders the brief, so a preference set before the run survives every
pass that follows it rather than living in one prompt and dying in the next.
An exclusion also has a deterministic tooth: `steering_gate` blocks a draft
that carries a figure or quotation found only in material the user excluded.
Preferences never outrank the factual checks - where they collide, the
evidence limits win and the collision is reported.
"""

import hashlib
import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.knowledge.artifacts import Grounding, KnowledgeArtifacts
from app.knowledge.ledger import (
    ClaimKind,
    Evidence,
    EvidenceKind,
    EvidenceStrength,
    context_of,
    extract_claims,
    unconfirmed_billing,
)
from app.market.positioning import PositioningMap, Territory
from app.marketing.briefs import CampaignBrief, EmailSteering
from app.marketing.email_copy import Email, render_review
from app.marketing.gates import GateIssue, GateReport, GateSeverity
from app.marketing.substantiation import assess_text

#: Free-text directions are preferences, not a second brief. A paragraph here
#: competes with the plan for the writer's attention, and a bound keeps the
#: preference legible to every role that has to honour it.
MAX_INSTRUCTION_CHARS = 500
MAX_INSTRUCTIONS = 8
MAX_ITEMS = 120

SteeringGroup = Literal["facts", "proof", "offer", "price", "audience", "competition"]
SteeringStatus = Literal["usable", "strategic", "to_confirm"]
SteeringChoice = Literal["include", "exclude"]

_PROOF_KINDS = {EvidenceKind.TESTIMONIAL, EvidenceKind.CUSTOMER, EvidenceKind.METRIC,
                EvidenceKind.AWARD, EvidenceKind.CERTIFICATION}
#: Kinds of extracted claim that are specific enough to trace back to one
#: source. A bare word is not: blocking it would block ordinary prose.
_TRACEABLE = {ClaimKind.MONEY, ClaimKind.PERCENT, ClaimKind.MULTIPLIER,
              ClaimKind.DURATION, ClaimKind.QUANTITY, ClaimKind.QUOTE}


class SteeringItem(BaseModel):
    """One choice the user made. Absent means "the system decides"."""

    id: str = Field(min_length=1, max_length=200)
    choice: SteeringChoice


class SteeringInstruction(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_INSTRUCTION_CHARS)
    scope: Literal["sequence", "email"] = "sequence"
    #: 1-based, and only meaningful when the scope is one email.
    position: int | None = Field(default=None, ge=1, le=12)

    @field_validator("text")
    @classmethod
    def _stripped(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("an instruction cannot be blank")
        return value


class CampaignSteering(BaseModel):
    items: list[SteeringItem] = Field(default_factory=list, max_length=MAX_ITEMS)
    instructions: list[SteeringInstruction] = Field(default_factory=list, max_length=MAX_INSTRUCTIONS)

    @property
    def is_empty(self) -> bool:
        return not self.items and not self.instructions

    def choice(self, item_id: str) -> SteeringChoice | None:
        return next((item.choice for item in self.items if item.id == item_id), None)


class SteeringOption(BaseModel):
    """One thing the user can steer, as the analyses describe it."""

    id: str
    group: SteeringGroup
    status: SteeringStatus
    label: str
    detail: str = ""
    #: Why it carries this status, in one line the form can show.
    status_reason: str = ""
    evidence_id: str = ""
    #: Normalized figures a price or proof carries. Used for conflict
    #: detection and for the exclusion gate, never shown as a claim.
    values: list[str] = Field(default_factory=list)
    #: True when the selected audience's researched claim contract forbids
    #: this fact. Including it does nothing but say so: its text is never
    #: written into a plan or a draft, because naming a forbidden claim in a
    #: prompt - even as "do not state" - is how a live run once shipped it.
    outside_boundary: bool = False


class SteeringConflict(BaseModel):
    severity: Literal["conflict", "notice"]
    message: str
    item_ids: list[str] = Field(default_factory=list)


class SteeringCheck(BaseModel):
    options: list[SteeringOption] = Field(default_factory=list)
    conflicts: list[SteeringConflict] = Field(default_factory=list)
    #: False when nothing has been compiled yet. The section still saves free
    #: directions; there is simply nothing to pick from until the first run.
    knowledge_ready: bool = False


# ------------------------------------------------------------------ options


def _key(prefix: str, text: str) -> str:
    return f"{prefix}:" + hashlib.sha256(" ".join(text.casefold().split()).encode()).hexdigest()[:12]


def _values(text: str) -> list[str]:
    return list(dict.fromkeys(
        claim.normalized for claim in extract_claims(text) if claim.kind in _TRACEABLE
    ))


def _evidence_status(entry: Evidence) -> tuple[SteeringStatus, str]:
    context = context_of(entry)
    if unconfirmed_billing(entry):
        return "to_confirm", "The payment conditions for this price need confirmation."
    if not entry.verbatim.strip():
        return "to_confirm", "No source text licenses it."
    if entry.strength is EvidenceStrength.WEAK:
        return "to_confirm", "The source states it only vaguely."
    if "review" in context.verification or "inferred" in context.verification:
        return "to_confirm", "Its scope was inferred and needs review."
    if entry.user_attested:
        return "usable", "You stated it; the copy may use it within its wording."
    return "usable", "Found in your material; the copy may state it within its source wording."


def _evidence_group(entry: Evidence) -> SteeringGroup:
    if entry.kind is EvidenceKind.PRICE:
        return "price"
    if entry.kind is EvidenceKind.GUARANTEE:
        return "offer"
    if entry.kind in _PROOF_KINDS:
        return "proof"
    return "facts"


def claim_boundary(intelligence, artifacts: KnowledgeArtifacts | None) -> frozenset[str]:
    """Evidence ids the selected audience's research forbids this campaign.

    The same set the Strategist's normalization writes into every brief's
    `forbidden_evidence_ids`, computed once here so the form, the plan and the
    post-pass cannot disagree about what the user is allowed to include.
    """
    if intelligence is None or artifacts is None:
        return frozenset()
    forbidden = set(intelligence.forbidden_evidence_ids)
    if intelligence.v2_claim_boundary:
        forbidden |= artifacts.evidence.ids - set(intelligence.allowed_evidence_ids)
    return frozenset(forbidden)


def release_selling_facts(
    brief: CampaignBrief, artifacts: KnowledgeArtifacts, intelligence,
) -> None:
    """Take the reasons to buy on each email's destination back out of its boundary.

    The boundary is wider than what is false. It holds every fact the audience's
    dossier did not connect to that audience's problem - 860 of Cabaia's 883,
    its price and its rating among them - so the writer could not say what the
    bag costs in an email selling the bag. `ClaimContract` draws the line this
    keeps: forbidden is "this claim is not licensed", withheld is "true, and
    not spent here". A reason to buy on the page the button leads to is the
    second kind, and only the first kind stays out.

    Run before the user's choices are applied, so what they exclude stays
    excluded. A legacy dossier has no contract and so no line to read: its
    boundary stands whole.
    """
    contract = getattr(intelligence, "claim_contract", None)
    if contract is None:
        return
    unlicensed = frozenset(
        id_ for claim in contract.forbidden_claims for id_ in claim.evidence_ids
    ) | frozenset(entry.id for entry in artifacts.evidence.entries if unconfirmed_billing(entry))
    for email in brief.emails:
        destinations = [
            brief.fixed_cta_url or email.next_step_url,
            *(alternative.next_step_url for alternative in email.alternative_arguments),
        ]
        released: set[str] = set()
        for destination in destinations:
            released |= artifacts.selling_facts(destination, excluded_ids=unlicensed).ids
        email.forbidden_evidence_ids = [
            id_ for id_ in email.forbidden_evidence_ids if id_ not in released
        ]


_OUTSIDE_BOUNDARY = ("Outside the claims this audience's research allows. The plan will not be "
                     "built on it, whatever you choose.")


def steering_options(
    artifacts: KnowledgeArtifacts | None,
    positioning: PositioningMap | None = None,
    boundary: frozenset[str] = frozenset(),
) -> list[SteeringOption]:
    """Everything the existing analyses offer to steer, with an honest status."""
    if artifacts is None:
        return []
    options: list[SteeringOption] = []
    for entry in artifacts.evidence.entries:
        status, reason = _evidence_status(entry)
        outside = entry.id in boundary
        if outside:
            status, reason = "to_confirm", _OUTSIDE_BOUNDARY
        context = context_of(entry)
        options.append(SteeringOption(
            id=f"evidence:{entry.id}", group=_evidence_group(entry), status=status,
            label=entry.claim, evidence_id=entry.id, status_reason=reason,
            detail="; ".join(filter(None, (entry.source, context.conditions, context.limitations))),
            values=_values(f"{entry.verbatim} {entry.claim}"), outside_boundary=outside,
        ))
    usable = {option.evidence_id for option in options if option.status == "usable"}
    for plan in artifacts.offer.plans:
        evidence_id = plan.provenance.evidence_id if plan.provenance else ""
        backed = evidence_id in usable
        options.append(SteeringOption(
            id=f"plan:{plan.reference_id}", group="price" if plan.price else "offer",
            status="usable" if backed else "to_confirm",
            label=f"{plan.name}" + (f" - {plan.price}" if plan.price else ""),
            detail="; ".join(plan.includes[:4]), evidence_id=evidence_id if backed else "",
            status_reason=("Backed by a fact in your material." if backed
                           else "No fact in the ledger licenses this plan's terms."),
            values=_values(plan.price),
        ))
    for action in artifacts.offer.calls_to_action:
        options.append(SteeringOption(
            id=f"cta:{action.reference_id}", group="offer", status="strategic",
            label=f"Ask: {action.label}", detail=action.url or action.intent,
            status_reason="Decides what the email asks for; not a claim.",
        ))
    if artifacts.offer.free_entry.strip():
        options.append(SteeringOption(
            id=_key("offer", artifacts.offer.free_entry), group="offer", status="to_confirm",
            label=f"Free entry: {artifacts.offer.free_entry}",
            status_reason="Summarised by the analysis; state it only through a matching fact.",
        ))
    for guarantee in artifacts.offer.guarantees:
        options.append(SteeringOption(
            id=_key("guarantee", guarantee), group="offer", status="to_confirm",
            label=f"Guarantee: {guarantee}",
            status_reason="Summarised by the analysis; state it only through a matching fact.",
        ))
    for segment in artifacts.audience.segments:
        options.append(SteeringOption(
            id=_key("segment", segment.name), group="audience", status="strategic",
            label=segment.name, detail=segment.situation,
            status_reason="Who the plan is written to; never a fact about the recipient.",
        ))
    for objection in artifacts.audience.objections:
        grounded = objection.grounding is not Grounding.INFERRED
        options.append(SteeringOption(
            id=_key("objection", objection.objection), group="audience",
            status="strategic" if grounded else "to_confirm",
            label=f"Objection: {objection.objection}", detail=objection.answer,
            status_reason=("Grounded in your material or research." if grounded
                           else "Inferred by the analysis; not observed."),
        ))
    if positioning is not None and not positioning.is_empty:
        for reading in positioning.readings:
            label = reading.proposition or str(reading.axis)
            territory = {
                Territory.OPEN: "open ground", Territory.CONTESTED: "contested",
                Territory.TABLE_STAKES: "every competitor says it",
                Territory.EXPOSED: "competitors claim it, our material does not",
            }[reading.territory]
            options.append(SteeringOption(
                id=_key("positioning", label), group="competition", status="strategic",
                label=label, detail=territory,
                status_reason="Market context; a comparison still needs a source.",
            ))
    return options


# ---------------------------------------------------------------- conflicts

_PRICE_WORDS = re.compile(r"\b(?:price|pricing|prices|cost|costs|tarif|tarifs|prix|co[uû]t)\b|[$€£]",
                          re.IGNORECASE)
#: Pairs of directions that cannot both be followed. Small and closed on
#: purpose: it catches the obvious collision, and a pair it does not know is
#: left to the writer rather than guessed at.
_OPPOSITES = (
    (re.compile(r"\b(?:short(?:er)?|brief|concise|court|courte|bref|concis)\b", re.IGNORECASE),
     re.compile(r"\b(?:long(?:er)?|detailed|d[ée]taill[ée]e?|plus long)\b", re.IGNORECASE)),
    (re.compile(r"\b(?:formal|formel|formelle|vouvoie\w*)\b", re.IGNORECASE),
     re.compile(r"\b(?:casual|informal|informel|familier|tutoie\w*)\b", re.IGNORECASE)),
    (re.compile(r"\b(?:no|without|sans|pas de)\s+(?:price|pricing|prix|tarif)", re.IGNORECASE),
     re.compile(r"\b(?:show|state|mention|include|indique\w*|mentionne\w*|donne\w*)\b[^.]{0,30}"
                r"\b(?:price|pricing|prix|tarif)", re.IGNORECASE)),
)


def check_steering(
    steering: CampaignSteering,
    options: list[SteeringOption],
    *,
    email_count: int | None = None,
) -> list[SteeringConflict]:
    """Collisions worth showing before anything is spent. Deterministic.

    None of these stop a run: the user may mean it, and the rule for every
    collision is already fixed - exclusions and evidence limits outrank
    directions. They are said out loud so nobody discovers it in the copy.
    """
    by_id = {option.id: option for option in options}
    conflicts: list[SteeringConflict] = []
    included = [by_id[item.id] for item in steering.items
                if item.choice == "include" and item.id in by_id]
    excluded = [by_id[item.id] for item in steering.items
                if item.choice == "exclude" and item.id in by_id]
    stale = [item.id for item in steering.items if item.id not in by_id]
    if stale and options:
        conflicts.append(SteeringConflict(
            severity="notice", item_ids=stale,
            message=f"{len(stale)} choice(s) refer to material no longer in the analysis and will be ignored.",
        ))
    for option in included:
        if option.outside_boundary:
            conflicts.append(SteeringConflict(
                severity="conflict", item_ids=[option.id],
                message=f'"{option.label}" is outside the claims this audience\'s research allows. '
                        "It will be kept out of the plan and the copy; choose another audience "
                        "or leave it on Auto.",
            ))
        elif option.status == "to_confirm":
            conflicts.append(SteeringConflict(
                severity="notice", item_ids=[option.id],
                message=f'"{option.label}" is not verified. It will inform the plan but will not be '
                        "stated as a fact. Confirm it in your material to use it in the copy.",
            ))
    prices = [option for option in included if option.group == "price" and option.values]
    if len({tuple(option.values) for option in prices}) > 1:
        conflicts.append(SteeringConflict(
            severity="conflict", item_ids=[option.id for option in prices],
            message="Several different prices are selected. Each will be kept with its own plan "
                    "and conditions; check that this is what you want readers to compare.",
        ))
    texts = [instruction.text for instruction in steering.instructions]
    excluded_prices = [option for option in excluded if option.group == "price"]
    asks_price = [text for text in texts if _PRICE_WORDS.search(text)
                  and not _OPPOSITES[2][0].search(text)]
    if asks_price and excluded_prices:
        conflicts.append(SteeringConflict(
            severity="conflict", item_ids=[option.id for option in excluded_prices],
            message=f'The direction "{asks_price[0]}" mentions price, but you excluded '
                    f"{len(excluded_prices)} price item(s). Excluded prices will not appear; "
                    "only prices you left in can be used.",
        ))
    for option in excluded:
        for text in texts:
            overlap = set(_values(text)) & set(option.values)
            if overlap:
                conflicts.append(SteeringConflict(
                    severity="conflict", item_ids=[option.id],
                    message=f'The direction "{text}" uses {", ".join(sorted(overlap))}, which comes '
                            f'from "{option.label}" - an item you excluded. The exclusion wins.',
                ))
    joined = "\n".join(texts)
    for first, second in _OPPOSITES:
        if first.search(joined) and second.search(joined):
            conflicts.append(SteeringConflict(
                severity="conflict",
                message="Two directions pull in opposite ways ("
                        + first.search(joined).group(0) + " / " + second.search(joined).group(0)
                        + "). Scope them to different emails or keep one.",
            ))
    if email_count is not None:
        for instruction in steering.instructions:
            if instruction.scope == "email" and (instruction.position or 0) > email_count:
                conflicts.append(SteeringConflict(
                    severity="conflict",
                    message=f'"{instruction.text}" targets email {instruction.position}, but the '
                            f"campaign asks for {email_count}. It will be ignored.",
                ))
    for instruction in steering.instructions:
        if instruction.scope == "email" and instruction.position is None:
            conflicts.append(SteeringConflict(
                severity="conflict",
                message=f'"{instruction.text}" is scoped to one email but names none.',
            ))
    if len([option for option in included if option.group == "audience"
            and option.id.startswith("segment:")]) > 1:
        conflicts.append(SteeringConflict(
            severity="notice",
            message="Several audiences are included. The campaign is still written to one "
                    "reader; the others become context for the plan.",
        ))
    proof = [option for option in options if option.group == "proof" and option.status == "usable"]
    if proof and all(steering.choice(option.id) == "exclude" for option in proof):
        conflicts.append(SteeringConflict(
            severity="conflict", item_ids=[option.id for option in proof],
            message="Every usable proof is excluded. The emails can only argue from what the "
                    "product does, with nothing a third party said about it.",
        ))
    return conflicts


# ------------------------------------------------------------ applying it


def render_for_strategy(steering: CampaignSteering | None, options: list[SteeringOption]) -> str:
    """The block the Strategist reads beside the user's own request."""
    if steering is None or steering.is_empty:
        return ""
    by_id = {option.id: option for option in options}
    use, consider, avoid, unverified = [], [], [], []
    for item in steering.items:
        option = by_id.get(item.id)
        # A forbidden claim is never named to the planner, not even as one to
        # avoid: the brief's own boundary already keeps it out, and its text in
        # a prompt is how a live run once argued from it anyway.
        if option is None or option.outside_boundary:
            continue
        line = f"{option.label}" + (f" [{option.evidence_id}]" if option.evidence_id else "")
        if item.choice == "exclude":
            avoid.append(line)
        elif option.status == "usable":
            use.append(line)
        elif option.status == "strategic":
            consider.append(line)
        else:
            unverified.append(line)
    sections = [("User steering, set before this run. These are the user's preferences and "
                 "outrank your own choices; they never license a claim the evidence does not.")]
    for title, lines in (
        ("Must be used somewhere in the campaign (verified)", use),
        ("Prefer as strategic context (never state as fact)", consider),
        ("Must not be used, mentioned or argued from", avoid),
        ("Selected but unverified - may inform the plan, may not be stated", unverified),
    ):
        if lines:
            sections.append(f"{title}:\n" + "\n".join(f"- {line}" for line in lines))
    sequence = [i.text for i in steering.instructions if i.scope == "sequence"]
    if sequence:
        sections.append("Directions for every email:\n" + "\n".join(f"- {t}" for t in sequence))
    for instruction in steering.instructions:
        if instruction.scope == "email" and instruction.position:
            sections.append(f"Direction for email {instruction.position} only: {instruction.text}")
    return "\n\n".join(sections)


def apply_steering(brief: CampaignBrief, steering: CampaignSteering | None,
                   artifacts: KnowledgeArtifacts,
                   options: list[SteeringOption] | None = None) -> list[str]:
    """Fix the user's choices into the brief, in code. Returns what was done
    or refused, for the run's own log. A no-op without steering."""
    if steering is None or steering.is_empty or not brief.emails:
        return []
    options = options if options is not None else steering_options(artifacts)
    by_id = {option.id: option for option in options}
    notes: list[str] = []
    excluded_ids: set[str] = set()
    include_evidence: list[str] = []
    strategic, avoid, context_only, excluded_text = [], [], [], []
    for item in steering.items:
        option = by_id.get(item.id)
        if option is None:
            notes.append(f"Ignored a choice for material no longer in the analysis ({item.id}).")
            continue
        if option.outside_boundary:
            if item.choice == "include":
                notes.append(f"Kept [{option.evidence_id}] out: this audience's claim boundary "
                             "forbids it, and the user's choice does not override a factual check.")
            continue
        if item.choice == "exclude":
            avoid.append(option.label)
            excluded_text.extend([option.label, *option.values])
            if option.evidence_id:
                excluded_ids.add(option.evidence_id)
                if (entry := artifacts.evidence.get(option.evidence_id)) is not None:
                    excluded_text.append(entry.verbatim)
        elif option.status == "usable" and option.evidence_id:
            include_evidence.append(option.evidence_id)
        elif option.status == "strategic":
            strategic.append(f"{option.label} (strategic context, not a claim)")
        else:
            context_only.append(option.label)
            notes.append(f'"{option.label}" is unverified: used as context only, not as a claim.')

    # A value counts as excluded only when no material the user kept states it
    # too: "14 days" in an excluded testimonial and a kept trial fact is the
    # trial, not the testimonial.
    kept = " ".join(entry.verbatim for entry in artifacts.evidence.entries
                    if entry.id not in excluded_ids)
    excluded_values = sorted(set(_values(" ".join(excluded_text))) - set(_values(kept)))
    sequence = [i.text for i in steering.instructions if i.scope == "sequence"]

    # The boundary the run already had - a researched audience's claim
    # contract, say - before the user's exclusions are folded into it.
    # Inclusion may not cross it: a preference is not a verification.
    boundary = {email.position: set(email.forbidden_evidence_ids) for email in brief.emails}
    for email in brief.emails:
        email.evidence_ids = [i for i in email.evidence_ids if i not in excluded_ids]
        email.next_step_evidence_ids = [i for i in email.next_step_evidence_ids
                                        if i not in excluded_ids]
        email.forbidden_evidence_ids = list(dict.fromkeys(
            [*email.forbidden_evidence_ids, *sorted(excluded_ids)]))
        for alternative in email.alternative_arguments:
            alternative.evidence_ids = [i for i in alternative.evidence_ids if i not in excluded_ids]
            alternative.next_step_evidence_ids = [i for i in alternative.next_step_evidence_ids
                                                  if i not in excluded_ids]
        email.steering = EmailSteering(
            exclude_evidence_ids=sorted(excluded_ids), avoid=list(avoid),
            context_only=list(context_only), excluded_values=excluded_values,
            use=list(strategic), directions=list(sequence),
        )

    for instruction in steering.instructions:
        if instruction.scope != "email":
            continue
        target = brief.brief_for(instruction.position or 0)
        if target is None:
            notes.append(f'Ignored "{instruction.text}": the campaign has '
                         f"{len(brief.emails)} email(s).")
            continue
        target.steering.directions.append(instruction.text)

    for evidence_id in dict.fromkeys(include_evidence):
        allowed = [e for e in brief.emails if evidence_id not in boundary[e.position]]
        if not allowed:
            notes.append(f"Kept [{evidence_id}] out: this audience's claim boundary forbids it, "
                         "and the user's choice does not override a factual check.")
            continue
        holder = next((e for e in allowed if evidence_id in e.evidence_ids), None)
        if holder is None:
            holder = min(allowed, key=lambda e: (len(e.evidence_ids), e.position))
            holder.evidence_ids.append(evidence_id)
        holder.forbidden_evidence_ids = [i for i in holder.forbidden_evidence_ids
                                         if i != evidence_id]
        holder.steering.include_evidence_ids.append(evidence_id)
        holder.steering.use.append(f"[{evidence_id}] {by_id[f'evidence:{evidence_id}'].label}")
        for alternative in holder.alternative_arguments:
            if evidence_id not in alternative.evidence_ids:
                alternative.evidence_ids.append(evidence_id)
        notes.append(f"[{evidence_id}] assigned to email {holder.position} at the user's request.")
    if excluded_ids or excluded_values:
        notes.append(f"Excluded {len(excluded_ids)} fact(s) from every email; "
                     f"{len(excluded_values)} figure(s) found only there are blocked by a check.")
    return notes


# --------------------------------------------------------------------- gate


def steering_gate(draft: Email, steering: EmailSteering, ledger: list[Evidence]) -> GateReport:
    """Exclusions block; inclusions advise.

    An excluded figure in the copy is a fact: the user removed its source, and
    a draft that still carries it ignored them. A requested fact that did not
    make it in is a judgment call the writer may have lost for a good reason -
    it is handed back as advice, the way an unspent assignment is.
    """
    if steering.is_empty:
        return GateReport()
    text = render_review(draft)
    excluded = set(steering.excluded_values)
    issues = [
        GateIssue(
            gate="user-steering",
            detail=f'"{claim.text}" comes only from material the user excluded - remove it',
        )
        for claim in extract_claims(text)
        if claim.kind in _TRACEABLE and claim.normalized in excluded
    ]
    wanted = [entry for entry in ledger if entry.id in steering.include_evidence_ids]
    if wanted:
        reading = assess_text(text, wanted, ledger)
        issues += [
            GateIssue(
                gate="user-steering", severity=GateSeverity.ADVISORY,
                detail=f"the user asked for [{entry.id}] ({entry.claim}) and this draft does not "
                       "use it - work it in where it serves the argument",
            )
            for entry in reading.unspent
        ]
    return GateReport(issues=issues)
