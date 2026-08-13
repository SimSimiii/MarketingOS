from datetime import UTC, datetime

from sqlmodel import Session

from app.models.user_settings import UserSettings
from app.repositories.settings_repository import UserSettingsRepository
from app.schemas.settings import UserSettingsUpdate


class SettingsService:
    def __init__(self, session: Session) -> None:
        self._settings = UserSettingsRepository(session)

    def get_settings(self) -> UserSettings:
        return self._settings.get_singleton()

    def update_settings(self, data: UserSettingsUpdate) -> UserSettings:
        settings = self._settings.get_singleton()
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(settings, field, value)
        settings.updated_at = datetime.now(UTC)
        return self._settings.update(settings)
