"""Test-suite bootstrap.

This module runs before any test module is imported, which matters: both
`app.core.database` and `app.main` resolve settings at *import* time, so the
only way to stop the suite binding to the developer's real database is to fix
the environment first.

Without this, `TestClient(app)` runs the app's lifespan against
`marketingos.db` - including `reap_orphaned_executions()`, which marks every
RUNNING execution as failed. Running the tests while a campaign was in flight
would quietly kill it.
"""

import os

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite://"

from app.core.config import get_settings

# Settings are lru_cached; drop anything a previous import may have captured.
get_settings.cache_clear()
