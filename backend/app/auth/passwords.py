"""Password hashing: bcrypt over a peppered digest.

bcrypt alone is already the right answer to "someone stole the table". The
pepper answers the sharper version of it - someone stole the table *and*
nothing else - because it lives in the process environment rather than the
database, and without it no amount of GPU turns a hash back into a password.

The HMAC pre-hash is not decoration. bcrypt silently truncates its input at 72
bytes, so a long passphrase would otherwise be no stronger than its first 72
characters; hashing to a fixed 64-char digest first makes every password the
same, safe length.
"""

import hashlib
import hmac

import bcrypt

from app.core.config import get_settings

#: bcrypt work factor. 12 is roughly 250ms on a small Lambda - slow enough to
#: make offline guessing expensive, fast enough that a login is not a spinner.
_ROUNDS = 12


def _peppered(password: str) -> bytes:
    pepper = get_settings().password_pepper.encode()
    return hmac.new(pepper, password.encode("utf-8"), hashlib.sha256).hexdigest().encode()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_peppered(password), bcrypt.gensalt(rounds=_ROUNDS)).decode()


def verify_password(password: str, password_hash: str) -> bool:
    """False rather than an exception on a malformed hash.

    A row whose hash was truncated by a bad import is a login that fails, not a
    500 - and never a login that succeeds.
    """
    try:
        return bcrypt.checkpw(_peppered(password), password_hash.encode())
    except (ValueError, TypeError):
        return False
