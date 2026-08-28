"""What the funnel every live event goes through costs the run it narrates.

`ExecutionEventEmitter.emit` is called between model calls, hundreds of times
in one campaign, on the same database connection the live page is being served
from. What it does per call is therefore not an implementation detail.
"""

from uuid import uuid4

import pytest
from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine, select

# Imported from the package rather than the module: it is what registers
# every table, and ExecutionLog carries a foreign key to one of the others.
from app.models import ExecutionLog
from app.orchestration.event_emitter import ExecutionEventEmitter
from app.repositories.execution_log_repository import ExecutionLogRepository


@pytest.fixture
def engine(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'logs.db'}")
    SQLModel.metadata.create_all(engine)
    return engine


def test_a_run_narrates_itself_without_reading_any_of_it_back(engine):
    """Every line is written and none is read.

    The emitter broadcasts the payload and then persists the identical one,
    and it keeps neither row - so refreshing what was just inserted, which is
    what `BaseRepository.create` does for callers that want the stored
    object, is a round trip per event to re-read something nobody looks at.
    """
    execution_id = uuid4()
    statements: list[str] = []

    with Session(engine) as session:
        emitter = ExecutionEventEmitter(ExecutionLogRepository(session), execution_id)

        @event.listens_for(engine, "before_cursor_execute")
        def _record(conn, cursor, statement, parameters, context, executemany):
            statements.append(statement)

        try:
            for index in range(5):
                emitter.emit("phase", f"step {index}")
        finally:
            event.remove(engine, "before_cursor_execute", _record)

        assert len(session.exec(select(ExecutionLog)).all()) == 5

    reads = [item for item in statements if item.lstrip().upper().startswith("SELECT")]
    assert not reads, f"the emitter read {len(reads)} row(s) back: {reads}"
