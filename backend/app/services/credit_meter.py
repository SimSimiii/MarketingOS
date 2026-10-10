"""Pre-authorize each paid model call, then release the unused hold.

The reserve uses a conservative token bound and the highest supported API
rate for the selected model. A call with no credit never reaches the vendor.
Unknown models and work without an account fail closed in prepaid mode.
"""

from dataclasses import dataclass
from decimal import ROUND_CEILING, Decimal
from math import isfinite
from uuid import UUID, uuid4

from sqlalchemy import Engine
from sqlmodel import Session

from app.ai.base import AIRequest, AIUsage, ResearchTool
from app.ai.models import MODEL_COST_PER_1K_TOKENS, usage_cost_usd
from app.core.config import assert_prepaid_prices_current
from app.core.database import engine as app_engine
from app.models.brand import Brand
from app.models.campaign import Campaign
from app.models.campaign_execution import CampaignExecution
from app.models.enums import UserStatus
from app.models.linkedin import LinkedInRun
from app.models.user import User
from app.services.credit_service import debit, refund

_SUPPORTED = frozenset({"haiku", "sonnet", "opus", "fable5", "gpt-5.6-sol"})
_MAX_SEARCHES = 5
_RESEARCH_INPUT_BOUND = 1_050_000
_PROMPT_OVERHEAD = 8_192


def _credits(cost_usd: Decimal) -> int:
    return max(1, int((cost_usd * Decimal(200)).to_integral_value(rounding=ROUND_CEILING)))


def _model_key(model: str) -> str:
    if model in _SUPPORTED:
        return model
    from app.ai.anthropic_api_provider import resolve_model

    # A future version with the same family prefix may have a different
    # price. Only the exact API aliases this release explicitly routes to
    # may reuse its reviewed rate; unfamiliar returned snapshots need review.
    for alias in _SUPPORTED:
        if resolve_model(alias) == model:
            return alias
    raise ValueError("This model has no verified prepaid price. Choose a supported preset.")


def _rates(model: str) -> tuple[Decimal, Decimal]:
    key = _model_key(model)
    incoming, outgoing = MODEL_COST_PER_1K_TOKENS[key]
    return Decimal(str(incoming)), Decimal(str(outgoing))


def _owner_for(execution_id: str, db: Session) -> UUID | None:
    if execution_id.startswith("vision:"):
        return UUID(execution_id.removeprefix("vision:"))
    if execution_id.startswith(("market:", "knowledge:")):
        brand = db.get(Brand, UUID(execution_id.split(":", 1)[1]))
        return brand.owner_id if brand else None
    if execution_id.startswith("linkedin:"):
        run = db.get(LinkedInRun, UUID(execution_id.split(":", 1)[1]))
        brand = db.get(Brand, run.brand_id) if run else None
        return brand.owner_id if brand else None
    try:
        execution = db.get(CampaignExecution, UUID(execution_id))
    except ValueError:
        return None
    campaign = db.get(Campaign, execution.campaign_id) if execution else None
    return campaign.owner_id if campaign else None


@dataclass(frozen=True)
class CallHold:
    user_id: UUID
    amount: int
    reference: str
    research_surcharge_usd: Decimal


class CreditMeter:
    def __init__(self, execution_id: str, engine: Engine | None = None) -> None:
        self._engine = engine or app_engine
        self._execution_id = execution_id
        with Session(self._engine) as db:
            self._user_id = _owner_for(execution_id, db)

    def reserve(self, request: AIRequest) -> CallHold:
        assert_prepaid_prices_current()
        if self._user_id is None:
            raise ValueError("This paid action has no customer account to charge.")
        with Session(self._engine) as db:
            user = db.get(User, self._user_id)
            if user is None or user.status == UserStatus.SUSPENDED:
                raise ValueError("This account cannot use credits right now.")
        model = request.model or ""
        input_rate, output_rate = _rates(model)
        if request.tools and model.startswith("gpt-"):
            raise ValueError("Paid web research is not available on this model.")
        prompt_bytes = len((request.system_prompt or "").encode("utf-8"))
        prompt_bytes += sum(len(message.content.encode("utf-8")) for message in request.messages)
        if request.image:
            prompt_bytes += len(request.image.data)
        input_bound = prompt_bytes + _PROMPT_OVERHEAD
        if request.tools:
            input_bound = max(input_bound, _RESEARCH_INPUT_BOUND)
        surcharge = (
            Decimal("0.01") * _MAX_SEARCHES
            if ResearchTool.WEB_SEARCH in request.tools else Decimal(0)
        )
        upper_usd = (
            Decimal(input_bound) * input_rate * 2 / 1000
            + Decimal(request.max_tokens) * output_rate / 1000
            + surcharge
        )
        amount = _credits(upper_usd)
        reference = f"call:{self._execution_id}:{uuid4()}"
        with Session(self._engine) as db:
            debit(db, self._user_id, amount, reference, kind="hold")
        return CallHold(self._user_id, amount, reference, surcharge)

    def release_unsent(self, hold: CallHold) -> None:
        """Release only when the request provably never reached a provider."""
        with Session(self._engine) as db:
            refund(db, hold.user_id, hold.amount, f"release:{hold.reference}")

    @staticmethod
    def measured_cost(model: str, usage: AIUsage) -> float:
        """Never substitute another model's estimated price for a paid call."""
        cost = usage_cost_usd(_model_key(model), usage)
        if not isfinite(cost) or cost < 0:
            raise ValueError("The provider returned invalid billing usage; the reserve needs review.")
        return cost

    def settle(self, hold: CallHold, cost_usd: float) -> None:
        charged = _credits(Decimal(str(max(0.0, cost_usd))) + hold.research_surcharge_usd)
        if charged > hold.amount:
            # Preserve the whole hold and stop further work. The provider
            # reported usage outside the bound we authorized, so silently
            # refunding would turn an accounting fault into an undercharge.
            raise RuntimeError("Model usage exceeded the authorized credit hold.")
        unused = hold.amount - charged
        if unused:
            with Session(self._engine) as db:
                refund(db, hold.user_id, unused, f"release:{hold.reference}")
