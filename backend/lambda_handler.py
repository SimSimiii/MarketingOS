"""API Gateway entry point for the platform API.

The same ASGI app that `uvicorn app.main:app` serves, wrapped by Mangum. There
is no second application object and no Lambda-specific branch inside the
routes - a request that behaves differently depending on how it arrived is a
bug waiting for a deployment to reveal it.

Two things are switched off here, and both are deliberate:

**`lifespan="off"`.** The app's lifespan runs `init_db()` (which would try to
`CREATE TABLE` on RDS from every cold start, racing itself across concurrent
containers) and `reap_orphaned_executions()` (which marks every RUNNING
execution as failed - correct for a process that owns the machine, catastrophic
for a function that scales to twenty of them). Schema is Alembic's job; see
`docs/deployment.md`.

**Campaign runs.** A run drives the `claude` / `codex` CLIs as subprocesses for
minutes at a time, streams over SSE, and keeps its registry in memory. None of
those survive a 15-minute, read-only, horizontally-scaled function. This
handler serves everything else - sign-in, brands, campaigns, knowledge, market
reads, results - and `POST /campaigns/{id}/start` needs the long-running
worker described in `docs/deployment.md`.
"""

from mangum import Mangum

from app.main import app

handler = Mangum(app, lifespan="off")
