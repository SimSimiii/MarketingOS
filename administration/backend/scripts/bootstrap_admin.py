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

On AWS the database is only reachable from inside the VPC, so the same logic is
also deployed as `marketingos-admin-bootstrap-<env>`, a function with no HTTP
route that only an IAM principal can invoke:

    aws lambda invoke --function-name marketingos-admin-bootstrap-prod       --cli-binary-format raw-in-base64-out       --payload '{"email": "you@example.com", "password": "..."}' out.json
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


def create_operator(
    email: str,
    password: str,
    *,
    name: str | None = None,
    role: str = "superadmin",
    reset_password: bool = False,
) -> tuple[bool, str]:
    """Create an operator, or reset one's password. Returns (ok, message)."""
    from app.core.database import engine
    from app.models.admin import AdminUser
    from app.models.enums import AdminRole
    from sqlmodel import Session, col, func, select

    from admin.auth import hash_password
    from admin.schemas import MIN_ADMIN_PASSWORD_LENGTH

    if len(password) < MIN_ADMIN_PASSWORD_LENGTH:
        return False, f"password must be at least {MIN_ADMIN_PASSWORD_LENGTH} characters."

    email = email.strip().lower()
    with Session(engine) as session:
        existing = session.exec(
            select(AdminUser).where(func.lower(col(AdminUser.email)) == email)
        ).first()
        if existing is not None:
            if not reset_password:
                return False, f"'{email}' is already an operator. Use --reset-password."
            existing.password_hash = hash_password(password)
            existing.is_active = True
            session.add(existing)
            session.commit()
            return True, f"Password reset for {email}."

        admin = AdminUser(
            email=email,
            password_hash=hash_password(password),
            full_name=name,
            role=AdminRole(role),
        )
        session.add(admin)
        session.commit()
        session.refresh(admin)
        return True, f"Created operator {admin.email} ({admin.role})."


def lambda_handler(event: dict | None, context: object = None) -> dict:
    """The same thing, for a database only reachable from inside the VPC.

    The password arrives in the invocation payload and is never logged or
    returned. The function has no HTTP route; invoking it takes IAM.
    """
    event = event or {}
    email = str(event.get("email") or "")
    password = str(event.get("password") or "")
    if not email or not password:
        return {"ok": False, "error": "The payload needs 'email' and 'password'."}
    role = str(event.get("role") or "superadmin")
    if role not in ("support", "admin", "superadmin"):
        return {"ok": False, "error": f"Unknown role '{role}'."}
    ok, message = create_operator(
        email,
        password,
        name=event.get("name"),
        role=role,
        reset_password=bool(event.get("reset_password")),
    )
    return {"ok": ok, "message" if ok else "error": message}


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

    ok, message = create_operator(
        args.email,
        password,
        name=args.name,
        role=args.role,
        reset_password=args.reset_password,
    )
    print(message if ok else f"ERROR: {message}", file=sys.stdout if ok else sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
