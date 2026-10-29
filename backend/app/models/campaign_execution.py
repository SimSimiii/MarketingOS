from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.models.enums import ExecutionStatus


class CampaignExecution(SQLModel, table=True):
    """One orchestrated run of the agent pipeline for a given Campaign."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    campaign_id: UUID = Field(foreign_key="campaign.id", index=True)
    status: ExecutionStatus = Field(default=ExecutionStatus.PENDING, index=True)
    result: dict | None = Field(default=None, sa_column=Column(JSON))
    #: The exact persisted recommendation shown before this run. Kept even if
    #: the run crashes, so an override remains auditable.
    recommendation_snapshot: dict | None = Field(default=None, sa_column=Column(JSON))
    generated_despite_recommendation: bool = False
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    #: Campaign-wide totals, summed across every model call made during this
    #: run. Populated on finalize; see CampaignOrchestrator.
    #:
    #: `total_input_tokens` counts every input token the run consumed, cached
    #: input included - which is what quota is actually spent on. Runs recorded
    #: before this column existed carry only the uncached fraction, so a
    #: historical row may read implausibly low beside a recent one.
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    #: The cached share of the input above, kept separately so the cost of a
    #: run can be explained rather than just stated.
    total_cache_read_tokens: int = 0
    estimated_cost_usd: float = 0.0

    @property
    def needs_review(self) -> bool:
        """A completed process can still have an incomplete delivery."""
        return self.status == ExecutionStatus.COMPLETED and bool(self.review_reasons)

    @property
    def review_reasons(self) -> list[str]:
        result = self.result or {}
        if self.status != ExecutionStatus.COMPLETED:
            return []
        reasons: list[str] = []
        if self.error_message:
            reasons.append("The run retained drafts after an interrupted step.")
        report = result.get("report") or {}
        if report.get("delivered", 0) < report.get("promised", 0):
            reasons.append("Some requested deliverables are missing.")
        emails = report.get("emails") or []
        if any(email.get("clean") is False for email in emails):
            reasons.append("Some drafts retain unresolved automatic checks.")
        elif any(email.get("unresolved") for email in emails):
            reasons.append("Some drafts retain unresolved strategy or review findings.")
        if any(email.get("landed") is False or email.get("understood") is False for email in emails):
            reasons.append("Some drafts still need editorial review.")
        if result.get("run_status") in {"degraded", "budget_exhausted", "cancelled", "failed"} and not reasons:
            reasons.append("The run finished with unresolved review requirements.")
        return reasons

    @property
    def outcome_status(self) -> str:
        """Delivery outcome, separate from the process state used by polling."""
        if self.needs_review:
            return "degraded"
        return self.status.value
