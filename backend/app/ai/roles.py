"""Every reasoning role a run can put on a model, described for the picker.

`ModelRouter` only ever sees role *ids* - opaque strings it looks up in an
override map. That is the right shape for the router and the wrong shape for a
person choosing which model should write their emails: "conversion_critic" and
"inbox_scanner" mean nothing on their own, and the choice between them matters
more than any preset.

So this is the presentation half of routing, and the only place that knows a
role exists at all outside the module implementing it. The ids are literals
rather than imports because every implementing module imports `app.ai`, and
importing them back would close the cycle; `tests/ai/test_roles.py` asserts
this catalog and the `ROLE_ID` constants stay in step, which is the check that
would otherwise be an import.
"""

from dataclasses import dataclass, field
from enum import StrEnum

from app.ai.base import ResearchTool
from app.ai.models import MODEL_CATALOG, ModelTier, tools_for


class RolePhase(StrEnum):
    """Which part of a run a role belongs to - the picker groups by it.

    Grouping matters because the phases have different economics. A campaign
    role runs many times per run; a knowledge role runs once per business and
    is then reused by every campaign attached to it; a market role runs only
    when market intelligence is refreshed, and is the only kind that touches
    the open web.
    """

    KNOWLEDGE = "knowledge"
    CAMPAIGN = "campaign"
    MARKET = "market"


@dataclass(frozen=True)
class RoleSpec:
    """One role, as the per-agent model picker has to present it."""

    id: str
    label: str
    #: What this role decides, in the terms of someone buying the outcome -
    #: not the terms of the class implementing it.
    blurb: str
    phase: RolePhase
    #: The tier this role asks for. What it resolves to depends on the preset;
    #: an override replaces the resolution outright.
    tier: ModelTier
    #: Capabilities the role passes on its calls. A model that cannot offer
    #: all of them cannot run this role - see `validate_overrides`.
    tools: frozenset[ResearchTool] = field(default_factory=frozenset)


_WEB = frozenset({ResearchTool.WEB_SEARCH, ResearchTool.WEB_FETCH})


ROLE_CATALOG: dict[str, RoleSpec] = {
    spec.id: spec
    for spec in (
        RoleSpec(
            id="knowledge_compiler",
            label="Knowledge compiler",
            blurb="Reads the business's own material and writes down what a campaign can use.",
            phase=RolePhase.KNOWLEDGE,
            tier=ModelTier.BALANCED,
        ),
        RoleSpec(
            id="strategist",
            label="Strategist",
            blurb="Decides what the sequence argues and in what order.",
            phase=RolePhase.CAMPAIGN,
            tier=ModelTier.DEEP,
        ),
        RoleSpec(
            id="email_writer",
            label="Email writer",
            blurb="Writes the drafts. The role that most changes what lands in an inbox.",
            phase=RolePhase.CAMPAIGN,
            tier=ModelTier.DEEP,
        ),
        RoleSpec(
            id="conversion_critic",
            label="Conversion critic",
            blurb="Catches brief drift and evidence the draft was handed but never spent.",
            phase=RolePhase.CAMPAIGN,
            tier=ModelTier.DEEP,
        ),
        RoleSpec(
            id="blind_reader",
            label="Cold reader",
            blurb="Reacts to a draft as a stranger would. The busiest role in a run.",
            phase=RolePhase.CAMPAIGN,
            tier=ModelTier.BALANCED,
        ),
        RoleSpec(
            id="preference_judge",
            label="Preference judge",
            blurb="Given two drafts, says which one they would act on.",
            phase=RolePhase.CAMPAIGN,
            tier=ModelTier.BALANCED,
        ),
        RoleSpec(
            id="sequence_reviewer",
            label="Sequence reviewer",
            blurb="Reads the finished sequence end to end, after each email passed alone.",
            phase=RolePhase.CAMPAIGN,
            tier=ModelTier.DEEP,
        ),
        RoleSpec(
            id="subject_writer",
            label="Subject-line writer",
            blurb="Writes the one sentence most recipients ever read.",
            phase=RolePhase.CAMPAIGN,
            tier=ModelTier.DEEP,
        ),
        RoleSpec(
            id="inbox_scanner",
            label="Inbox scanner",
            blurb="Glances at a subject line and says whether it would be opened.",
            phase=RolePhase.CAMPAIGN,
            tier=ModelTier.BALANCED,
        ),
        RoleSpec(
            id="proof_hunter",
            label="Proof hunter",
            blurb="Searches the web for evidence the business's own material never contained.",
            phase=RolePhase.MARKET,
            tier=ModelTier.BALANCED,
            tools=_WEB,
        ),
        RoleSpec(
            id="rival_scout",
            label="Rival scout",
            blurb="Finds who else is making the same promise to the same buyer.",
            phase=RolePhase.MARKET,
            tier=ModelTier.BALANCED,
            tools=_WEB,
        ),
        RoleSpec(
            id="rival_profiler",
            label="Rival profiler",
            blurb="Reads a competitor's pages and writes down what they actually claim.",
            phase=RolePhase.MARKET,
            tier=ModelTier.BALANCED,
            tools=_WEB,
        ),
        RoleSpec(
            id="audience_cartographer",
            label="Audience cartographer",
            blurb=(
                "Works out who would really buy this - including the buyers the company's "
                "own website would never have named."
            ),
            phase=RolePhase.MARKET,
            # The only market role on the deep tier. Every other one extracts
            # from pages it was handed; this one has to notice that a tool sold
            # to support teams is bought harder by parts distributors, which is
            # judgment and is the whole product of the pass.
            tier=ModelTier.DEEP,
            tools=_WEB,
        ),
        RoleSpec(
            id="prospect_finder",
            label="Prospect finder",
            blurb="Names real organisations that match one audience segment.",
            phase=RolePhase.MARKET,
            tier=ModelTier.BALANCED,
            tools=_WEB,
        ),
        RoleSpec(
            id="prospect_reader",
            label="Prospect reader",
            blurb=(
                "Reads one organisation's pages and copies out how they say to reach them."
            ),
            phase=RolePhase.MARKET,
            # No web tools: it only ever sees pages this process fetched, which
            # is the arrangement that makes a contact detail checkable. See
            # app.market.demand.
            tier=ModelTier.BALANCED,
        ),
    )
}


#: The blanket override. Not a role, but valid everywhere a role id is, and the
#: picker offers it as "every agent" - see `ModelRouter.resolve`.
WILDCARD_ROLE = "*"


class InvalidOverrideError(ValueError):
    """A per-role model choice that cannot be honoured.

    A `ValueError` so the API layer turns it into a 422 without a special case,
    and raised eagerly at save time rather than at call time: an override that
    is only discovered to be impossible thirteen minutes into a run has already
    cost the user the run.
    """


def validate_overrides(overrides: dict[str, str] | None) -> dict[str, str]:
    """Check a per-agent model map before it is stored.

    Two things are refused and one is deliberately allowed.

    Refused: a role id nothing in the system answers to - almost always a typo,
    and silently ignored it would look like the override simply did nothing.
    Refused too: a model that cannot offer the capabilities its role passes,
    which today means putting a market-intelligence role on a GPT model. Codex
    has web search but no fetch-this-URL tool, and a research role that loses
    half its access does not come back empty, it comes back with plausible
    competitors the model remembered.

    Allowed: a model slug this build has never heard of. The vendor catalogs
    move faster than this repository does, and refusing an unknown slug would
    mean a model released after the last deploy is unusable until the next one.
    An unknown slug is routed by `vendor_of` and fails loudly at the vendor if
    it is wrong, which is a better failure than being unable to try.
    """
    if not overrides:
        return {}

    cleaned: dict[str, str] = {}
    for role_id, model in overrides.items():
        model = (model or "").strip()
        if not model:
            # An empty value is how the UI says "back to the preset's choice".
            continue
        if role_id == WILDCARD_ROLE:
            # The blanket override is checked against no capabilities on
            # purpose. It is stored per campaign, and a campaign run reaches
            # only the knowledge and campaign roles - none of which pass a
            # tool. The market roles that do are routed separately
            # (`market_service` builds its own bare `ModelRouter`), so a
            # wildcard cannot strand them. Refusing it here would ban the one
            # thing the picker exists for: running a whole campaign on GPT.
            cleaned[role_id] = model
            continue
        if (spec := ROLE_CATALOG.get(role_id)) is None:
            raise InvalidOverrideError(
                f"'{role_id}' is not an agent in this system. Known agents: "
                f"{', '.join(sorted(ROLE_CATALOG))}."
            )
        if missing := sorted(spec.tools - tools_for(model)):
            label = MODEL_CATALOG[model].label if model in MODEL_CATALOG else model
            raise InvalidOverrideError(
                f"{label} cannot run '{spec.label}': that agent reads the open web and "
                f"this model has no {', '.join(missing)}. Pick a Claude model for this one."
            )
        cleaned[role_id] = model
    return cleaned
