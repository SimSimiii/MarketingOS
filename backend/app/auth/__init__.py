"""Who is calling, and what they are allowed to see.

Three separable things live here on purpose:

- `passwords` / `tokens` are cryptography with no opinion about the product.
- `service` is the account lifecycle - register, sign in, refresh, revoke.
- `scope` is the tenancy rule, and it is one function so there is exactly one
  place to read when the question is "can this account see that row".

The back-office is `admin`, and it is separate all the way down: its own
table, its own signing secret, its own role ladder.
"""

from app.auth.passwords import hash_password, verify_password
from app.auth.principal import Principal
from app.auth.scope import owned
from app.auth.tokens import TokenError, create_access_token, decode_access_token

__all__ = [
    "Principal",
    "TokenError",
    "create_access_token",
    "decode_access_token",
    "hash_password",
    "owned",
    "verify_password",
]
