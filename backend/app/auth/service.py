"""Account lifecycle: register, sign in, refresh, sign out.

Everything that decides *whether* somebody gets a token lives here, so the
HTTP layer above it is only translation. Two rules are load-bearing and easy
to lose in a refactor, so they are stated once here rather than at each call
site:

- A failed sign-in never says which half was wrong. Distinguishing "no such
  account" from "wrong password" turns the login form into a directory of who
  has bought the product.
- A refresh rotates. The presented token is revoked in the same transaction
  that issues its replacement, so a stolen refresh token is good for one use
  and its replay is visible as a revoked-token attempt.
"""

from datetime import UTC, datetime

from sqlmodel import Session, col, select

from app.auth.passwords import hash_password, verify_password
from app.auth.tokens import (
    create_access_token,
    hash_refresh_token,
    new_refresh_token,
    refresh_expiry,
)
from app.core.config import get_settings
from app.models.enums import UserPlan, UserRole, UserStatus
from app.models.user import User, UserSession


class AuthError(Exception):
    """Credentials were not accepted. Carries the message the user may read."""


class SignupClosedError(AuthError):
    """Public registration is off on this deployment."""


class EmailTakenError(AuthError):
    """That address already has an account."""


class AccountSuspendedError(AuthError):
    """The account exists and is switched off."""


class IssuedTokens:
    """What a successful sign-in hands back."""

    def __init__(self, access_token: str, expires_in: int, refresh_token: str, user: User) -> None:
        self.access_token = access_token
        self.expires_in = expires_in
        self.refresh_token = refresh_token
        self.user = user


def normalise_email(email: str) -> str:
    return email.strip().lower()


def find_by_email(session: Session, email: str) -> User | None:
    return session.exec(select(User).where(col(User.email) == normalise_email(email))).first()


def register(
    session: Session,
    *,
    email: str,
    password: str,
    full_name: str | None = None,
    company_name: str | None = None,
    allow_closed_signup: bool = False,
) -> User:
    """Create an account.

    `allow_closed_signup` is how the seeding script and the back-office create
    accounts on a deployment whose public form is shut. It is a parameter
    rather than a second function because the validation either way is the
    same, and two copies of it is how one of them drifts.
    """
    settings = get_settings()
    if not settings.allow_public_signup and not allow_closed_signup:
        raise SignupClosedError(
            "This deployment is invite-only. Ask for an account instead of creating one."
        )

    email = normalise_email(email)
    if find_by_email(session, email) is not None:
        raise EmailTakenError("An account already exists for that address.")

    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=(full_name or "").strip() or None,
        company_name=(company_name or "").strip() or None,
        role=UserRole.OWNER,
        status=UserStatus.ACTIVE,
        plan=UserPlan.FREE,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def authenticate(session: Session, *, email: str, password: str) -> User:
    user = find_by_email(session, email)
    # Hash even when there is no such account, so the response time does not
    # answer "does this address have an account here" on its own.
    reference = user.password_hash if user else "$2b$12$" + "." * 53
    ok = verify_password(password, reference)
    if user is None or not ok:
        raise AuthError("Wrong email or password.")
    if user.status == UserStatus.SUSPENDED:
        raise AccountSuspendedError(
            user.suspended_reason or "This account has been suspended. Contact support."
        )
    return user


def issue_tokens(
    session: Session,
    user: User,
    *,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> IssuedTokens:
    access_token, expires_in = create_access_token(
        user.id, user.email, str(user.role), str(user.plan)
    )
    raw_refresh, token_hash = new_refresh_token()
    session.add(
        UserSession(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=refresh_expiry(),
            user_agent=(user_agent or "")[:512] or None,
            ip_address=ip_address,
        )
    )
    user.last_login_at = datetime.now(UTC)
    session.add(user)
    session.commit()
    session.refresh(user)
    return IssuedTokens(access_token, expires_in, raw_refresh, user)


def _live_session(session: Session, raw_refresh: str) -> UserSession | None:
    record = session.exec(
        select(UserSession).where(col(UserSession.token_hash) == hash_refresh_token(raw_refresh))
    ).first()
    if record is None or record.revoked_at is not None:
        return None
    expires_at = record.expires_at
    if expires_at.tzinfo is None:  # SQLite hands back naive datetimes.
        expires_at = expires_at.replace(tzinfo=UTC)
    return None if expires_at < datetime.now(UTC) else record


def refresh(
    session: Session,
    raw_refresh: str,
    *,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> IssuedTokens:
    record = _live_session(session, raw_refresh)
    if record is None:
        raise AuthError("Session expired. Sign in again.")

    user = session.get(User, record.user_id)
    if user is None:
        raise AuthError("Session expired. Sign in again.")
    if user.status == UserStatus.SUSPENDED:
        raise AccountSuspendedError(
            user.suspended_reason or "This account has been suspended. Contact support."
        )

    now = datetime.now(UTC)
    record.revoked_at = now
    record.last_used_at = now
    session.add(record)
    return issue_tokens(session, user, user_agent=user_agent, ip_address=ip_address)


def revoke(session: Session, raw_refresh: str) -> None:
    """Sign out one session. Silent on an unknown token - there is nothing to
    tell the caller that is not also an answer to "is this token real"."""
    record = _live_session(session, raw_refresh)
    if record is None:
        return
    record.revoked_at = datetime.now(UTC)
    session.add(record)
    session.commit()


def revoke_all(session: Session, user_id, *, reason: str | None = None) -> int:
    """End every session for one account. Returns how many were live.

    Used by "sign out everywhere", by a password change (an attacker who has
    the old password should not keep a session), and by the back-office when
    an operator suspends somebody.
    """
    del reason  # Recorded by the caller's audit entry, not on the session row.
    now = datetime.now(UTC)
    records = list(
        session.exec(
            select(UserSession).where(
                col(UserSession.user_id) == user_id,
                col(UserSession.revoked_at).is_(None),
            )
        )
    )
    for record in records:
        record.revoked_at = now
        session.add(record)
    session.commit()
    return len(records)


def change_password(session: Session, user: User, *, current: str, new: str) -> None:
    if not verify_password(current, user.password_hash):
        raise AuthError("Current password is wrong.")
    user.password_hash = hash_password(new)
    user.updated_at = datetime.now(UTC)
    session.add(user)
    session.commit()
    revoke_all(session, user.id)
