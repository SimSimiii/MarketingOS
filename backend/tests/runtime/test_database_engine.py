"""The engine a Lambda gets must let Aurora Serverless pause.

Aurora v2 scales to zero only once no connection is open, and a pool held by a
frozen Lambda container keeps one open for as long as AWS keeps the container.
"""

from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from app.core import database


def _captured(monkeypatch, url: str, *, on_lambda: bool) -> dict:
    seen: dict = {}

    def fake_create_engine(target, **kwargs):
        seen.update(url=target, **kwargs)
        # A real engine, so the resume listener has something to attach to.
        seen["engine"] = create_engine("sqlite://")
        return seen["engine"]

    monkeypatch.setattr(database, "create_engine", fake_create_engine)
    if on_lambda:
        monkeypatch.setenv("AWS_LAMBDA_FUNCTION_NAME", "marketingos-api-test")
    else:
        monkeypatch.delenv("AWS_LAMBDA_FUNCTION_NAME", raising=False)
    database.create_app_engine(url)
    return seen


def test_a_lambda_opens_a_connection_per_request_and_waits_out_a_resume(monkeypatch):
    seen = _captured(monkeypatch, "postgresql+psycopg://u:p@db:5432/m", on_lambda=True)

    assert seen["poolclass"] is NullPool
    assert seen["connect_args"]["connect_timeout"] > 0
    assert len(seen["engine"].dialect.dispatch.do_connect) == 1


def test_a_long_running_process_keeps_its_pool(monkeypatch):
    seen = _captured(monkeypatch, "postgresql+psycopg://u:p@db:5432/m", on_lambda=False)

    assert "poolclass" not in seen
    assert len(seen["engine"].dialect.dispatch.do_connect) == 0


def test_sqlite_is_untouched_by_the_lambda_rule(monkeypatch):
    monkeypatch.setenv("AWS_LAMBDA_FUNCTION_NAME", "marketingos-api-test")

    engine = database.create_app_engine("sqlite://")

    assert not isinstance(engine.pool, NullPool)


# A paused Aurora cluster closes the first connection rather than holding it
# until it has resumed, which takes about fifteen seconds.


class Resuming(Exception):
    pass


def test_a_connection_refused_while_the_database_resumes_is_tried_again():
    tries = []
    waits = []

    def connect():
        tries.append(1)
        if len(tries) < 3:
            raise Resuming()
        return "connection"

    assert database.connect_with_retry(connect, Resuming, sleep=waits.append) == "connection"
    assert len(tries) == 3
    assert len(waits) == 2


def test_a_database_that_never_comes_back_is_reported_rather_than_waited_on_forever():
    tries = []

    def connect():
        tries.append(1)
        raise Resuming()

    try:
        database.connect_with_retry(connect, Resuming, attempts=4, sleep=lambda _: None)
    except Resuming:
        pass
    else:
        raise AssertionError("expected the last failure to propagate")
    assert len(tries) == 4


def test_other_failures_are_not_retried():
    tries = []

    def connect():
        tries.append(1)
        raise ValueError("bad credentials")

    try:
        database.connect_with_retry(connect, Resuming, sleep=lambda _: None)
    except ValueError:
        pass
    assert len(tries) == 1


def test_the_retry_budget_fits_inside_the_gateway_timeout():
    """API Gateway gives up after thirty seconds; the waits alone must leave room."""
    assert (database.RESUME_ATTEMPTS - 1) * database.RESUME_WAIT_SECONDS < 25
