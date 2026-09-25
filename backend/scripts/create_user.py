#!/usr/bin/env python
"""Create a platform account by hand.

The public signup form is off by default (see
`Settings.allow_public_signup`), because the first deployments are invited
testers and an open form on a product that spends model quota per run is a
bill rather than a funnel. This is how those testers get in.

Run from `backend/`, against whichever database DATABASE_URL points at:

    .venv/Scripts/python.exe -m scripts.create_user --email you@example.com

The password is read from a prompt, never from an argument - a password on the
command line ends up in shell history and in the process list.
"""

from __future__ import annotations

import argparse
import getpass
import sys

from sqlmodel import Session

from app.auth import service
from app.auth.passwords import hash_password
from app.core.database import engine
from app.models.enums import UserPlan, UserStatus
from app.schemas.auth import MIN_PASSWORD_LENGTH


def _read_password() -> str | None:
    password = getpass.getpass(f"Password (min {MIN_PASSWORD_LENGTH} characters): ")
    if len(password) < MIN_PASSWORD_LENGTH:
        print(f"ERROR: password must be at least {MIN_PASSWORD_LENGTH} characters.", file=sys.stderr)
        return None
    if password != getpass.getpass("Confirm password: "):
        print("ERROR: passwords do not match.", file=sys.stderr)
        return None
    return password


def main() -> int:
    parser = argparse.ArgumentParser(description="Create or reset a MarketingOS account.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", default=None)
    parser.add_argument("--company", default=None)
    parser.add_argument(
        "--plan", default=UserPlan.FREE, choices=[plan.value for plan in UserPlan]
    )
    parser.add_argument(
        "--quota",
        type=int,
        default=0,
        help="Runs allowed per period. 0 means unlimited.",
    )
    parser.add_argument(
        "--reset-password",
        action="store_true",
        help="If the address already has an account, set a new password instead of failing.",
    )
    args = parser.parse_args()

    password = _read_password()
    if password is None:
        return 1

    with Session(engine) as session:
        existing = service.find_by_email(session, args.email)
        if existing is not None:
            if not args.reset_password:
                print(
                    f"ERROR: '{args.email}' already has an account. Use --reset-password.",
                    file=sys.stderr,
                )
                return 1
            existing.password_hash = hash_password(password)
            # A password reset that leaves the old sessions alive resets
            # nothing an attacker cares about.
            service.revoke_all(session, existing.id)
            existing.status = UserStatus.ACTIVE
            existing.suspended_reason = None
            session.add(existing)
            session.commit()
            print(f"Password reset for {existing.email}; every session was signed out.")
            return 0

        user = service.register(
            session,
            email=args.email,
            password=password,
            full_name=args.name,
            company_name=args.company,
            # This script *is* the invite on a closed deployment.
            allow_closed_signup=True,
        )
        user.plan = UserPlan(args.plan)
        user.monthly_run_quota = args.quota
        session.add(user)
        session.commit()
        print(f"Created {user.email} ({user.plan}, id {user.id}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
