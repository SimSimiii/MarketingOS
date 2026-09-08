"""Run `alembic upgrade head` inside the VPC.

RDS is not reachable from a laptop when it is configured the way it should be,
so migrations run where the API runs. This is its own function rather than
something the API does at cold start: concurrent containers would race each
other through the same revisions, and a schema change would land whenever
traffic happened to arrive rather than when somebody decided it should.

Invoke it by hand after any deploy that carries a migration:

    aws lambda invoke --function-name marketingos-migrate-prod out.json

The payload may carry `{"revision": "..."}` to stop at a specific revision, or
`{"command": "downgrade", "revision": "-1"}` to step back one.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from alembic import command
from alembic.config import Config

logger = logging.getLogger("marketingos.migrate")
logger.setLevel(logging.INFO)

_HERE = Path(__file__).resolve().parent


def _config() -> Config:
    config = Config(str(_HERE / "alembic.ini"))
    # The ini's script_location is relative to the working directory, which on
    # Lambda is /var/task rather than wherever the deploy was run from.
    config.set_main_option("script_location", str(_HERE / "alembic"))
    config.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])
    return config


def handler(event: dict | None = None, context: object = None) -> dict:
    event = event or {}
    action = event.get("command", "upgrade")
    revision = event.get("revision") or ("head" if action == "upgrade" else "-1")

    if action not in ("upgrade", "downgrade", "stamp"):
        return {"ok": False, "error": f"Unknown command '{action}'."}

    logger.info("alembic %s %s", action, revision)
    try:
        getattr(command, action)(_config(), revision)
    except Exception as exc:  # noqa: BLE001 - the caller is a CLI invoke.
        logger.exception("migration failed")
        return {"ok": False, "command": action, "revision": revision, "error": str(exc)}
    return {"ok": True, "command": action, "revision": revision}


if __name__ == "__main__":
    print(handler())
