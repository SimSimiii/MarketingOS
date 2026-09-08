#!/usr/bin/env python
"""Give the rows that predate accounts to an account.

A database built before `owner_id` existed has brands and campaigns with no
owner. The migration deliberately leaves them that way - there was no user to
attribute them to, and picking one would have handed somebody's work to an
account they never created.

Single-user mode still sees those rows, so a laptop needs nothing. A
deployment that turns AUTH_REQUIRED on does: until they are claimed, unowned
rows are invisible to everyone.

Run from `backend/`:

    .venv/Scripts/python.exe -m scripts.claim_workspace --email you@example.com
    .venv/Scripts/python.exe -m scripts.claim_workspace --email you@example.com --dry-run
"""

from __future__ import annotations

import argparse
import sys

from sqlmodel import Session, col, select

from app.auth import service
from app.core.database import engine
from app.models.brand import Brand
from app.models.campaign import Campaign
from app.models.user_settings import UserSettings


def main() -> int:
    parser = argparse.ArgumentParser(description="Adopt unowned brands and campaigns.")
    parser.add_argument("--email", required=True, help="The account that should own them.")
    parser.add_argument(
        "--dry-run", action="store_true", help="Report what would be claimed and change nothing."
    )
    args = parser.parse_args()

    with Session(engine) as session:
        user = service.find_by_email(session, args.email)
        if user is None:
            print(f"ERROR: no account for '{args.email}'. Create it first.", file=sys.stderr)
            return 1

        brands = list(session.exec(select(Brand).where(col(Brand.owner_id).is_(None))))
        campaigns = list(session.exec(select(Campaign).where(col(Campaign.owner_id).is_(None))))
        # At most one: single-user mode kept exactly one settings row.
        orphan_settings = list(
            session.exec(select(UserSettings).where(col(UserSettings.user_id).is_(None)))
        )

        print(f"Unowned: {len(brands)} brand(s), {len(campaigns)} campaign(s).")
        for brand in brands:
            print(f"  brand    {brand.id}  {brand.name}")
        for campaign in campaigns:
            print(f"  campaign {campaign.id}  {campaign.name}")

        if args.dry_run:
            print("Dry run - nothing changed.")
            return 0
        if not brands and not campaigns and not orphan_settings:
            print("Nothing to claim.")
            return 0

        for row in (*brands, *campaigns):
            row.owner_id = user.id
            session.add(row)

        # The settings row moves only if this account has none of its own -
        # otherwise the account would end up with two, and the unique index on
        # `user_id` would refuse the second.
        already = session.exec(
            select(UserSettings).where(col(UserSettings.user_id) == user.id)
        ).first()
        if orphan_settings and already is None:
            orphan_settings[0].user_id = user.id
            session.add(orphan_settings[0])
            print("  settings row adopted")
        elif orphan_settings:
            print("  settings row left alone - this account already has its own")

        session.commit()
        print(f"Claimed for {user.email}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
