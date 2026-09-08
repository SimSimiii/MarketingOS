from dataclasses import dataclass
from uuid import UUID

from app.models.user import User


@dataclass(frozen=True)
class Principal:
    """Who the request is acting as, and whether that identity constrains it.

    `user is None` is not an error - it is single-user mode, the shape the
    product had before accounts existed and the shape a laptop install keeps
    (see app.core.config.Settings.auth_required). Rows it creates have no
    owner and it sees everything, which is exactly one workspace.
    """

    user: User | None
    #: True when the deployment demands a token. Read by app.auth.scope to
    #: decide whether an unowned legacy row is visible - it is, on a
    #: single-workspace install being upgraded; it never is on a server.
    enforced: bool = False

    @property
    def owner_id(self) -> UUID | None:
        """Stamped onto every root row this request creates."""
        return self.user.id if self.user is not None else None

    @property
    def is_authenticated(self) -> bool:
        return self.user is not None
