#!/usr/bin/env python
"""Create the first back-office operator.

There is no signup form here and there never will be. This script is run once,
by hand, against the target database; after that a superadmin creates the rest
from the console.

From `administration/backend/`, with the product package importable:

    PYTHONPATH=../../backend python -m scripts.bootstrap_admin --email you@example.com

It needs the same DATABASE_URL the platform uses, and the same
ADMIN_PWD_PEPPER the back-office Lambda will run with - a hash made with a
different pepper is a password that will never verify.
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path

# Local-dev convenience: make the product package importable without asking
# anyone to remember PYTHONPATH. In the Lambda bundle `app` is vendored beside
# this file and already resolves, so this is a no-op there.
_BACKEND = Path(__file__).resolve().parents[3] / "backend"
if (_BACKEND / "app").is_dir():
    sys.path.insert(0, str(_BACKEND))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> int:
    parser = argparse.ArgumentParser(description="Create or reset a back-office operator.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", default=None)
    parser.add_argument(
        "--role", default="superadmin", choices=["support", "admin", "superadmin"]
    )
    parser.add_argument(
        "--reset-password",
        action="store_true",
        help="If the address is already an operator, set a new password instead of failing.",
    )
    args = parser.parse_args()

    from app.core.database import engine
    from app.models.admin import AdminUser
    from app.models.enums import AdminRole
    from sqlmodel import Session, col, func, select

    from admin.auth import hash_password
    from admin.config import DEV_ADMIN_PEPPER, get_admin_settings
    from admin.schemas import MIN_ADMIN_PASSWORD_LENGTH

    # Loud rather than silent: a hash written with the development pepper will
    # not verify against a Lambda running with the real one, and the symptom
    # would be "the password I just set does not work".
    if get_admin_settings().admin_pwd_pepper == DEV_ADMIN_PEPPER and os.getenv("ENVIRONMENT"):
        print(
            "WARNING: ADMIN_PWD_PEPPER is still the development value. The hash this "
            "writes will not verify against a deployment using a real pepper.",
            file=sys.stderr,
        )

    password = getpass.getpass(f"Password (min {MIN_ADMIN_PASSWORD_LENGTH} characters): ")
    if len(password) < MIN_ADMIN_PASSWORD_LENGTH:
        print(
            f"ERROR: password must be at least {MIN_ADMIN_PASSWORD_LENGTH} characters.",
            file=sys.stderr,
        )
        return 1
    if password != getpass.getpass("Confirm password: "):
        print("ERROR: passwords do not match.", file=sys.stderr)
        return 1

    email = args.email.lower()
    with Session(engine) as session:
        existing = session.exec(
            select(AdminUser).where(func.lower(col(AdminUser.email)) == email)
        ).first()
        if existing is not None:
            if not args.reset_password:
                print(
                    f"ERROR: '{email}' is already an operator. Use --reset-password.",
                    file=sys.stderr,
                )
                return 1
            existing.password_hash = hash_password(password)
            existing.is_active = True
            session.add(existing)
            session.commit()
            print(f"Password reset for {email}.")
            return 0

        admin = AdminUser(
            email=email,
            password_hash=hash_password(password),
            full_name=args.name,
            role=AdminRole(args.role),
        )
        session.add(admin)
        session.commit()
        session.refresh(admin)
        print(f"Created operator {admin.email} ({admin.role}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
