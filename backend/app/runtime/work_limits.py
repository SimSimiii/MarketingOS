"""Atomic monthly quota and concurrency admission for the single persistent worker."""
import asyncio
import inspect
import os
import threading
import time
from contextvars import ContextVar
from datetime import UTC, datetime
from functools import wraps
from uuid import UUID

from sqlalchemy import update
from sqlmodel import Session, col, or_

from app.core.config import get_settings
from app.models.brand import Brand
from app.models.enums import UserStatus
from app.models.user import User


class WorkLimitError(RuntimeError):
    def __init__(self, message: str, status_code: int = 429):
        super().__init__(message)
        self.status_code = status_code


_lock = threading.RLock()
_active: dict[UUID | None, int] = {}
current_work: ContextVar["Reservation | None"] = ContextVar("current_work", default=None)


def is_job_host() -> bool:
    """Whether this process may admit model work.

    Anything that is not Lambda may: a laptop and a container both own their
    own uptime and can finish what they start. A Lambda may only when it was
    deployed as a step of the campaign state machine, which says so by setting
    JOB_HOST - because such a function is invoked with exactly one email to
    write and finishes it well inside the 900-second ceiling.

    The API function does not set it, and must not. It is invoked by a user
    pressing a button, has 30 seconds of API Gateway timeout in front of it,
    and accepting a whole campaign there is how a run gets silently truncated
    with no record of where it stopped.
    """
    if not os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        return True
    return os.environ.get("JOB_HOST", "").lower() in {"1", "true", "yes"}


class Reservation:
    def __init__(self, engine, owner: UUID | None, *, resume: bool = False):
        """`resume` attaches to a job already admitted, without charging again.

        A stepped run is one campaign spread over several invocations, and the
        user bought one campaign. The plan step charges the quota; every craft
        step after it sets `resume` so a five-email run costs one run against
        the account rather than seven.
        """
        if not is_job_host():
            raise WorkLimitError("Model jobs require a persistent worker; this host cannot run them.", 503)
        settings = get_settings()
        self.engine, self.owner = engine, owner
        self.started = self.scheduled = self.closed = False
        self.calls = self.tokens = 0
        self.created = time.monotonic()
        self.period = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        with _lock:
            if sum(_active.values()) >= settings.max_concurrent_jobs:
                raise WorkLimitError("The server is busy. Wait for a running job to finish.")
            if _active.get(owner, 0) >= settings.max_jobs_per_account:
                raise WorkLimitError("Your account already has the maximum number of running jobs.")
            self.resumed = resume
            if owner is not None and not resume:
                with Session(engine) as db:
                    db.execute(update(User).where(User.id == owner, or_(
                        col(User.quota_reset_at).is_(None), User.quota_reset_at < self.period,
                    )).values(runs_used=0, quota_reset_at=self.period))
                    result = db.execute(update(User).where(
                        User.id == owner, User.status != UserStatus.SUSPENDED,
                        or_(User.monthly_run_quota == 0, User.runs_used < User.monthly_run_quota),
                    ).values(runs_used=User.runs_used + 1))
                    if result.rowcount != 1:
                        db.rollback()
                        raise WorkLimitError("Monthly job quota reached or account unavailable.")
                    db.commit()
            _active[owner] = _active.get(owner, 0) + 1

    def attempt(self):
        if self.calls >= 500 or self.tokens >= 4_000_000 or time.monotonic() - self.created > 3600:
            raise WorkLimitError("This job reached its server budget.")
        self.started = True
        self.calls += 1

    def finish(self):
        with _lock:
            if self.closed:
                return
            self.closed = True
            try:
                if not self.started and self.owner is not None and not self.resumed:
                    with Session(self.engine) as db:
                        db.execute(update(User).where(
                            User.id == self.owner, User.quota_reset_at == self.period, User.runs_used > 0,
                        ).values(runs_used=User.runs_used - 1))
                        db.commit()
            finally:
                _active[self.owner] = max(0, _active.get(self.owner, 1) - 1)
                if not _active[self.owner]:
                    _active.pop(self.owner, None)


def admitted_job(function):
    """Refund admission failures and cache hits that never schedule model work."""
    signature = inspect.signature(function)

    @wraps(function)
    def wrapped(*args, **kwargs):
        bound = signature.bind(*args, **kwargs).arguments
        engine = bound.get("engine") or bound["db"].get_bind()
        root = bound.get("brand") or bound.get("campaign")
        if root is None:
            with Session(engine) as db:
                root = db.get(Brand, bound["brand_id"])
        if root is None:
            raise WorkLimitError("The requested workspace no longer exists.", 404)
        permit = Reservation(engine, root.owner_id)
        token = current_work.set(permit)
        try:
            return function(*args, **kwargs)
        finally:
            current_work.reset(token)
            if not permit.scheduled:
                permit.finish()
    return wrapped


def create_job_task(coro):
    permit = current_work.get()
    task = asyncio.create_task(coro)
    if permit is not None:
        permit.scheduled = True
        task.add_done_callback(lambda _: permit.finish())
    return task
