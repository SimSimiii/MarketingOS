"""The engine a Lambda gets must let Aurora Serverless pause.

Aurora v2 scales to zero only once no connection is open, and a pool held by a
frozen Lambda container keeps one open for as long as AWS keeps the container.
"""

from sqlalchemy.pool import NullPool

from app.core import database


def _captured(monkeypatch, url: str, *, on_lambda: bool) -> dict:
    seen: dict = {}

    def fake_create_engine(target, **kwargs):
        seen.update(url=target, **kwargs)
        return object()

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
    assert seen["connect_args"]["connect_timeout"] >= 15


def test_a_long_running_process_keeps_its_pool(monkeypatch):
    seen = _captured(monkeypatch, "postgresql+psycopg://u:p@db:5432/m", on_lambda=False)

    assert "poolclass" not in seen


def test_sqlite_is_untouched_by_the_lambda_rule(monkeypatch):
    monkeypatch.setenv("AWS_LAMBDA_FUNCTION_NAME", "marketingos-api-test")

    engine = database.create_app_engine("sqlite://")

    assert not isinstance(engine.pool, NullPool)
