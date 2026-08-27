from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.marketing.policy import PolicyPreset
from app.marketing.render_html import EmailTier
from app.models.enums import AssetType, CampaignStatus, ExecutionStatus
from app.schemas.types import UtcDatetime


class CampaignCreateRequest(BaseModel):
    """What the user fills in: their ask, in their own words, plus context."""

    name: str
    request: str = Field(
        min_length=10,
        description="What you want, in your own words - e.g. 'write me 3 emails "
        "that convince people to buy my product'",
    )
    product_description: str
    product_url: str | None = None
    target_market: str | None = None
    goals: str | None = None
    #: Who the emails are from - a person and their job. Optional, and the
    #: cheapest conversion in the form: without it every email is signed by a
    #: team, which reads as a broadcast because it is one.
    sender_name: str | None = None
    sender_role: str | None = None
    #: The business this campaign is for. Attaching it means the knowledge
    #: compiled for an earlier campaign is reused instead of recompiled.
    brand_id: UUID | None = None
    #: The name of a segment from this brand's audience map, if the user
    #: picked one. Optional, and the single field on this form that changes
    #: who the emails are written to: with it set the run plans against the
    #: buyer the market suggested rather than the one the company's own site
    #: describes. A name rather than an id - see app.models.campaign.
    audience_segment: str | None = None
    #: Where the call to action points, if the user knows. Falls back to the
    #: brand's website; without either, the CTA renders as a marked slot.
    cta_url: str | None = None
    #: How designed the finished email should look - see
    #: app.marketing.render_html. `plain` is typography only and is the right
    #: answer for cold outreach; `branded` adds the logo, the brand colour, a
    #: real button and a footer, and is the right answer for the mail a reader
    #: expects to come from a company. None takes the system default (plain).
    #:
    #: Stored inside `policy` rather than as its own column because that is
    #: where the orchestrator already reads it from, and because it is a
    #: property of how this campaign is run rather than of what it says.
    email_tier: EmailTier | None = None
    #: One of "fast" / "balanced" (default) / "maximum" - see app.marketing.policy.
    policy_preset: PolicyPreset | None = None
    #: Per-role model overrides, e.g. {"email_writer": "opus"} or {"*": "haiku"}.
    model_overrides: dict[str, str] | None = None
    #: Re-read and recompile the brand's knowledge even if nothing has
    #: changed since the last compile. None defers to the pipeline's own
    #: default (reuse) - see ExecutionPolicy.force_recompile.
    force_recompile: bool | None = None


class CampaignRead(BaseModel):
    # validate_assignment so the last-run fields, which the list route fills
    # in after construction, still get the UtcDatetime treatment - a plain
    # attribute assignment skips validators otherwise.
    model_config = ConfigDict(from_attributes=True, validate_assignment=True)

    id: UUID
    name: str
    request: str
    product_description: str
    product_url: str | None
    target_market: str | None
    goals: str | None
    sender_name: str | None = None
    sender_role: str | None = None
    brand_id: UUID | None = None
    audience_segment: str | None = None
    cta_url: str | None = None
    status: CampaignStatus
    archived_at: UtcDatetime | None
    policy: dict | None
    model_overrides: dict[str, str] | None
    created_at: UtcDatetime
    updated_at: UtcDatetime
    #: Status of this campaign's most recent run, so the list can show
    #: progress without a request per row. None = never run.
    last_run_status: ExecutionStatus | None = None
    last_run_at: UtcDatetime | None = None


class CampaignPolicyUpdate(BaseModel):
    preset: PolicyPreset | None = None
    #: How designed the finished emails look. Here as well as on creation
    #: because it is the one presentation decision a user changes their mind
    #: about after seeing a run - and re-running is cheap where re-creating
    #: the campaign is not. None leaves what is stored alone.
    email_tier: EmailTier | None = None
    #: Partial ExecutionPolicy field overrides layered on top of `preset`.
    overrides: dict | None = None
    #: Per-agent model choice, `{role_id: model}` - the "custom models" panel.
    #: Orthogonal to `preset`, which decides the *shape* of a run (how many
    #: drafts, which judges, what budget) and not only which models run it. An
    #: override replaces whatever the preset resolved for that agent; `{}`
    #: clears every pin and hands the choice back to the preset.
    #:
    #: `None` means "leave what is stored alone", so a caller changing only the
    #: preset does not silently wipe a picker the user filled in.
    model_overrides: dict[str, str] | None = None


class GeneratedAssetRead(BaseModel):
    """A deliverable, ready to copy and paste."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    asset_type: AssetType
    title: str
    content: str
    #: The same deliverable rendered as HTML. Null for anything that is not an
    #: email, and for emails written before rendering existed.
    content_html: str | None = None
    position: int
    asset_metadata: dict | None
    created_at: UtcDatetime


class AgentExecutionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    agent_id: str
    agent_name: str
    sequence_order: int
    status: ExecutionStatus
    input_data: dict | None
    output_data: dict | None
    error_message: str | None
    started_at: UtcDatetime | None
    completed_at: UtcDatetime | None
    model: str | None
    input_tokens: int
    output_tokens: int
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    cost_usd: float = 0.0
    duration_ms: float
    attempt: int


class RunForecast(BaseModel):
    """What running this campaign will cost, before anything is spent.

    The call count is arithmetic: no model call in this system decides what
    happens next, so the shape of a run follows from the policy and from the
    number of emails parsed out of the request. The money is not arithmetic
    and is not guessed - it is what the user's own past runs on this preset
    actually cost, and it is absent until there are some.
    """

    preset: str
    emails: int
    #: False when the user did not name a number, so `emails` is the working
    #: assumption rather than a promise and the estimate moves with it.
    count_is_explicit: bool

    #: Model calls: the run where every email lands first time, and the run
    #: that buys every rewrite and rework it is allowed.
    low: int
    high: int
    #: The share of the above that is reading this business's material.
    compile_low: int
    compile_high: int
    #: True when nothing the user attached has changed since the last compile,
    #: so this run reads none of it again. The largest saving in the system
    #: and the one nobody knows about.
    knowledge_reused: bool

    #: Finished runs on this preset that actually delivered, and what one
    #: delivered email cost on the middle one of them.
    #:
    #: Per email rather than per run, because past runs were different lengths.
    #: The median rather than the range, for the same reason the reader panel
    #: reports one: a run that died two calls in and a run that bought every
    #: rewrite it was allowed are both real and neither is what to plan
    #: around. Zero runs means no figure is offered, not a figure of zero.
    observed_runs: int = 0
    observed_cost_per_email: float = 0.0


class CampaignExecutionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    campaign_id: UUID
    status: ExecutionStatus
    error_message: str | None
    started_at: UtcDatetime | None
    completed_at: UtcDatetime | None
    created_at: UtcDatetime
    total_input_tokens: int
    total_output_tokens: int
    #: The cached share of the input above. Defaulted rather than required so
    #: runs recorded before the column existed still deserialize.
    total_cache_read_tokens: int = 0
    estimated_cost_usd: float


class RunningExecutionRead(CampaignExecutionRead):
    """A run in flight, named. The live dashboard lists these, so it carries
    the campaign's name and request rather than making the client resolve
    every campaign id itself."""

    campaign_name: str
    campaign_request: str


class CampaignExecutionDetail(CampaignExecutionRead):
    agent_executions: list[AgentExecutionRead] = []
    assets: list[GeneratedAssetRead] = []


class CampaignResultRead(CampaignExecutionDetail):
    result: dict | None = None
