"""What the model picker needs, in one response.

The frontend renders this catalog rather than restating it. A list of models
and agents hardcoded in TypeScript is a list that disagrees with the router the
first time either side changes - and the router is the side that decides where
the money goes.
"""

from pydantic import BaseModel

from app.ai.models import MODEL_CATALOG, ModelTier, ModelVendor
from app.ai.roles import ROLE_CATALOG, RolePhase


class ModelOption(BaseModel):
    """One selectable model."""

    id: str
    vendor: ModelVendor
    label: str
    blurb: str
    #: The tier this model is the automatic choice for, if any.
    default_for: ModelTier | None = None
    #: Capability names (`web_search`, `web_fetch`). The picker greys a model
    #: out for an agent whose own list is not covered by this one.
    tools: list[str]
    #: A plan or install the model needs, when it needs one. Shown as a caveat.
    requires: str | None = None


class AgentOption(BaseModel):
    """One role a model can be pinned to."""

    id: str
    label: str
    blurb: str
    phase: RolePhase
    #: What this agent resolves to when nothing is pinned.
    tier: ModelTier
    #: Capabilities this agent's calls pass. Non-empty means the agent reads
    #: the open web, which narrows which models can run it.
    tools: list[str]


class ModelCatalogRead(BaseModel):
    """Everything the picker renders, plus what "no override" resolves to.

    `tier_defaults` is sent so the UI can show the model an agent would use
    anyway, next to the one being chosen for it. Without it every unpinned row
    reads as "unset", which is exactly the confusion that makes people pin
    things they did not need to.
    """

    models: list[ModelOption]
    agents: list[AgentOption]
    tier_defaults: dict[ModelTier, str]
    #: The id the picker uses for "every agent" - the blanket override.
    wildcard: str


def build_catalog() -> ModelCatalogRead:
    from app.ai.models import DEFAULT_TIER_MODELS
    from app.ai.roles import WILDCARD_ROLE

    return ModelCatalogRead(
        models=[
            ModelOption(
                id=spec.id,
                vendor=spec.vendor,
                label=spec.label,
                blurb=spec.blurb,
                default_for=spec.default_for,
                tools=sorted(str(tool) for tool in spec.tools),
                requires=spec.requires,
            )
            for spec in MODEL_CATALOG.values()
        ],
        agents=[
            AgentOption(
                id=spec.id,
                label=spec.label,
                blurb=spec.blurb,
                phase=spec.phase,
                tier=spec.tier,
                tools=sorted(str(tool) for tool in spec.tools),
            )
            for spec in ROLE_CATALOG.values()
        ],
        tier_defaults=dict(DEFAULT_TIER_MODELS),
        wildcard=WILDCARD_ROLE,
    )
