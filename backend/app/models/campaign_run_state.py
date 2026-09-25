"""The state a campaign run carries between steps, when the steps are separate processes.

A run on a laptop keeps all of this in local variables: `EmailCampaignPipeline.run`
holds the brief, the accepted emails and the outcomes for the minutes it takes,
and none of it needs a name. Split the same run across Lambda invocations and
every one of those locals has to survive a process that no longer exists.

Only what cannot be recomputed lives here. That is a short list, and keeping it
short is the design:

  - **The brief** comes from one Strategist call. Re-planning between two
    emails would be a second, differently-worded plan, and emails 3 and 4 would
    be arguing a campaign emails 1 and 2 never agreed to.
  - **The accepted emails** are what `CraftLoop.craft(previous=...)` reads.
    Email N is written knowing what N-1 said; without them the sequence is five
    first emails.
  - **The outcomes** are what the report is built from at the end.

Everything else is deliberately absent because it is already durable somewhere
better: the artifacts are in `KnowledgeArtifactSet` keyed by a fingerprint of
the corpus, the corpus is in `KnowledgeDocument`, the positioning and demand
maps are in the market tables, and the contract is a pure function of the
request. A step reloads those rather than carrying them, which is also what
keeps this row far below Step Functions' 256 KB payload limit - the state
machine passes an execution id and a position, never the state itself.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class CampaignRunState(SQLModel, table=True):
    """One row per stepped execution. Absent for a run that happened in one process."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    #: Unique rather than merely indexed: two rows for one execution would mean
    #: two different ideas of which email comes next, and the loop would either
    #: skip one or write it twice.
    execution_id: UUID = Field(foreign_key="campaignexecution.id", index=True, unique=True)

    #: `CampaignBrief.model_dump(mode="json")`. Written once by the plan step
    #: and never rewritten - see the module docstring.
    brief: dict | None = Field(default=None, sa_column=Column(JSON))

    #: `list[Email]`, in position order, as the craft step accepts them. This
    #: is what becomes `previous=` on the next email.
    accepted: list = Field(default_factory=list, sa_column=Column(JSON))

    #: `list[EmailVersion]` - the full record of what judged each email, which
    #: the report is built from. Serialized through a Pydantic TypeAdapter
    #: rather than by hand: `EmailVersion` is a dataclass of dataclasses and
    #: Pydantic models, and a hand-written encoder would drift from it the
    #: first time a field was added.
    outcomes: list = Field(default_factory=list, sa_column=Column(JSON))

    #: The trace of the intelligence pass, when there was one. Recomputing it
    #: would be a second model call for an answer already paid for.
    intelligence: dict | None = Field(default=None, sa_column=Column(JSON))

    #: How the request was read. Cheap to recompute - `parse_contract` is pure -
    #: but stored so that a step and the step before it cannot disagree about
    #: how many emails were promised.
    contract: dict | None = Field(default=None, sa_column=Column(JSON))

    #: The position the craft step should write next, 1-based. The state
    #: machine's Choice compares it against `total`, so this row is the single
    #: answer to "are we done" - a retried step that already wrote its email
    #: sees the advanced position and is idempotent.
    next_position: int = 1
    total_positions: int = 0

    #: Set when a step stops the run deliberately - cancelled, out of budget,
    #: nothing to argue from. Carried so the finish step reports the same
    #: reason the pipeline would have, rather than a generic failure.
    abort_reason: str | None = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
