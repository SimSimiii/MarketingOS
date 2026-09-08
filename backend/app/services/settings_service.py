from datetime import UTC, datetime

from sqlmodel import Session

from app.auth.principal import Principal
from app.models.user_settings import UserSettings
from app.repositories.settings_repository import UserSettingsRepository
from app.schemas.settings import UserSettingsUpdate


class SettingsService:
    """One account's preferences.

    The principal decides which row that is - see
    UserSettingsRepository.get_for. Without one (single-user mode) it is the
    unowned row, which is the row this table has always had.
    """

    def __init__(self, session: Session, principal: Principal | None = None) -> None:
        self._settings = UserSettingsRepository(session)
        self._owner_id = principal.owner_id if principal is not None else None

    def get_settings(self) -> UserSettings:
        return self._settings.get_for(self._owner_id)

    def update_settings(self, data: UserSettingsUpdate) -> UserSettings:
        settings = self._settings.get_for(self._owner_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(settings, field, value)
        settings.updated_at = datetime.now(UTC)
        return self._settings.update(settings)
