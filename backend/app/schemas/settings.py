from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.types import UtcDatetime


class UserSettingsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_name: str | None
    brand_voice: str | None
    default_ai_provider: str
    default_model: str
    updated_at: UtcDatetime


class UserSettingsUpdate(BaseModel):
    company_name: str | None = None
    brand_voice: str | None = None
    default_ai_provider: str | None = None
    default_model: str | None = None
