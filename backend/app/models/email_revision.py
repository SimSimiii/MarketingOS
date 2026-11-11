"""A proposed edit to one finished email, made after the run.

One row per proposal. The asset keeps the version the user chose; these rows
are the history behind it - what was asked, what came back, what the checks
said about *that* text, and what the user decided. A proposal never inherits
the verdicts of the version it edits: its `checks` were computed on its own
words, and it carries no cold-read score because nobody read it cold.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

#: running -> proposed | blocked | unchanged | failed; proposed -> accepted | rejected.
#: `blocked` is a proposal that still fails a deterministic check after its
#: one repair pass. It is shown, so the user sees why, and cannot be accepted.
#: `unchanged` is a pass that returned the same copy - typically a request
#: for a claim the material does not hold - and says so instead.
REVISION_STATES = (
    "running", "proposed", "blocked", "unchanged", "failed", "accepted", "rejected",
)


class EmailRevision(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    asset_id: UUID = Field(foreign_key="generatedasset.id", index=True)
    campaign_execution_id: UUID = Field(foreign_key="campaignexecution.id", index=True)
    #: The revision this one adjusts, or None when it adjusts the original.
    base_revision_id: UUID | None = Field(default=None, foreign_key="emailrevision.id")
    instruction: str
    state: str = Field(default="running", index=True)
    #: The asset id while a proposal is being written: one at a time per
    #: email, enforced by the database rather than by a check-then-insert.
    active_key: str | None = Field(default=None, unique=True)
    #: `Email.model_dump(mode="json")` of the proposed version.
    email: dict | None = Field(default=None, sa_column=Column(JSON))
    content: str = ""
    content_html: str | None = None
    #: `GateReport.model_dump(mode="json")` - this text's own checks.
    checks: dict | None = Field(default=None, sa_column=Column(JSON))
    #: Writer passes spent: one, or two when the first failed a check.
    attempts: int = 0
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    error: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    decided_at: datetime | None = None
