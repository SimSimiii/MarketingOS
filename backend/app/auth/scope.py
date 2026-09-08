"""The tenancy rule, in one place.

Every table in this application hangs off a brand or a campaign, so those two
carry `owner_id` and everything else is reached through them. That makes this
module the whole of multi-tenancy: if a query for a root row goes through
`owned()`, the rows under it cannot be reached by the wrong account.
"""

from sqlmodel import col
from sqlmodel.sql.expression import SelectOfScalar

from app.auth.principal import Principal


def owned[T](
    statement: SelectOfScalar[T], model: type, principal: Principal
) -> SelectOfScalar[T]:
    """Narrow a select over an owned root table to what `principal` may read.

    Three cases, and the middle one is the one worth explaining:

    - No account (single-user mode): no filter. One workspace, as before.
    - An account on an install that does not require auth: own rows *and*
      unowned ones. A local database predates accounts, and a developer who
      signs in for the first time should not find their brands gone. Run
      `scripts/claim_workspace.py` to adopt them properly.
    - An account on a deployment that requires auth: own rows only. An unowned
      row on a server is a bug or a leftover, and either way it is not theirs.
    """
    if principal.user is None:
        return statement
    if principal.enforced:
        return statement.where(col(model.owner_id) == principal.user.id)
    return statement.where(
        col(model.owner_id).is_(None) | (col(model.owner_id) == principal.user.id)
    )


def may_read(row: object, principal: Principal) -> bool:
    """The same rule applied to a row already loaded by primary key.

    `session.get()` cannot carry a WHERE clause, and rewriting every lookup as
    a filtered select to get one would be a lot of noise for a check that is
    this short.
    """
    if principal.user is None:
        return True
    owner_id = getattr(row, "owner_id", None)
    if owner_id == principal.user.id:
        return True
    return owner_id is None and not principal.enforced
