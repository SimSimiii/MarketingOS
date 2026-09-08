from uuid import UUID

from sqlmodel import col, select

from app.models.user_settings import UserSettings
from app.repositories.base import BaseRepository


class UserSettingsRepository(BaseRepository[UserSettings]):
    model = UserSettings

    def get_for(self, user_id: UUID | None) -> UserSettings:
        """The settings row for one account, created on first read.

        `user_id=None` is the single-user install's row - the one this table
        held back when there was only ever one of them. Keeping it addressable
        rather than migrating it away is what lets a laptop keep its settings
        after accounts arrive.
        """
        existing = self.session.exec(
            select(UserSettings).where(col(UserSettings.user_id) == user_id)
            if user_id is not None
            else select(UserSettings).where(col(UserSettings.user_id).is_(None))
        ).first()
        if existing is not None:
            return existing
        return self.create(UserSettings(user_id=user_id))
