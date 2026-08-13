from sqlmodel import select

from app.models.user_settings import UserSettings
from app.repositories.base import BaseRepository


class UserSettingsRepository(BaseRepository[UserSettings]):
    model = UserSettings

    def get_singleton(self) -> UserSettings:
        """This MVP is single-user: return the one settings row, creating it on first use."""
        existing = self.session.exec(select(UserSettings)).first()
        if existing is not None:
            return existing
        return self.create(UserSettings())
