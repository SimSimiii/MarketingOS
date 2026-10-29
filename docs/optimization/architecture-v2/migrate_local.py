"""Reconcile this local SQLite schema on a copy first; --apply keeps a backup.

The observed database has future tables but lacks the eight durable-run columns.
Never stamp directly at head. First prove parity with d91c382aa410, then upgrade.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from contextlib import closing, contextmanager
from datetime import UTC, datetime
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "backend"
DATABASE = BACKEND / "marketingos.db"
HERE = Path(__file__).resolve().parent
MATCHING_REVISION = "d91c382aa410"
MISSING = {"request_snapshot", "context_snapshot", "cancel_requested", "model_calls", "model_tokens", "deadline_at", "inflight_step", "workflow_arn"}


@contextmanager
def connection(path, readonly=False):
    db = sqlite3.connect(path.as_uri() + ("?mode=ro" if readonly else "?mode=rw"), uri=True)
    try:
        yield db
    finally:
        db.close()


def copy_database(source, destination):
    with connection(source, True) as src, closing(sqlite3.connect(destination)) as dst:
        src.backup(dst)


def table_data(path, columns=None):
    with connection(path, True) as db:
        tables = [name for (name,) in db.execute("select name from sqlite_master where type='table' and name not like 'sqlite_%' and name!='alembic_version'")]
        result = {}
        for table in sorted(tables):
            if columns is not None and table not in columns:
                continue
            names = columns[table]["columns"] if columns is not None else [row[1] for row in db.execute(f'pragma table_info("{table}")')]
            rows = [list(row) for row in db.execute('select ' + ','.join('"'+name+'"' for name in names) + f' from "{table}"')]
            encoded = sorted(json.dumps(row, ensure_ascii=False, default=str) for row in rows)
            result[table] = {"columns": names, "rows": len(rows), "sha256": hashlib.sha256("\n".join(encoded).encode()).hexdigest()}
        return result


def schema(path):
    engine = create_engine("sqlite:///" + path.as_posix())
    try:
        probe = inspect(engine)
        result = {}
        for table in probe.get_table_names():
            if table == "alembic_version":
                continue
            result[table] = {
                "columns": {column["name"]: (str(column["type"]), column["nullable"], column.get("primary_key", 0)) for column in probe.get_columns(table)},
                "indexes": sorted((tuple(index["column_names"]), bool(index["unique"])) for index in probe.get_indexes(table)),
                "foreign_keys": sorted((tuple(key["constrained_columns"]), key["referred_table"], tuple(key["referred_columns"])) for key in probe.get_foreign_keys(table)),
            }
        return result
    finally:
        engine.dispose()


def alembic(path, *args):
    env = {**os.environ, "APP_ENV": "test", "DATABASE_URL": "sqlite:///" + path.as_posix()}
    command = [str(BACKEND / ".venv/Scripts/python.exe"), "-m", "alembic", *args]
    result = subprocess.run(command, cwd=BACKEND, env=env, capture_output=True, text=True, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)


def reconcile(path, reference):
    ours, expected = schema(path), schema(reference)
    if ours == expected:
        alembic(path, "stamp", MATCHING_REVISION)
        return []
    missing = set(expected.get("campaignrunstate", {}).get("columns", {})) - set(ours.get("campaignrunstate", {}).get("columns", {}))
    if missing != MISSING:
        raise RuntimeError("Unexpected schema; refusing automatic reconciliation")
    reduced = json.loads(json.dumps(expected))
    for name in MISSING:
        reduced["campaignrunstate"]["columns"].pop(name)
    # JSON conversion normalizes tuple/list representation on both sides.
    if json.loads(json.dumps(ours)) != reduced:
        raise RuntimeError("Differences exceed the eight identified columns; database left unchanged")
    spec = importlib.util.spec_from_file_location("durable_columns", BACKEND / "alembic/versions/c12a80e31b90_durable_campaign_runs.py")
    if not Path(spec.origin).exists():
        source = next((BACKEND / "alembic/versions").glob("c12a80e31b90*.py"))
        spec = importlib.util.spec_from_file_location("durable_columns", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    engine = create_engine("sqlite:///" + path.as_posix())
    try:
        with engine.begin() as db:
            with Operations.context(MigrationContext.configure(db)):
                module.upgrade()
    finally:
        engine.dispose()
    if schema(path) != expected:
        raise RuntimeError("Reconciled schema does not match the historical revision")
    alembic(path, "stamp", MATCHING_REVISION)
    return sorted(MISSING)


def check_idle(path):
    with connection(path, True) as db:
        if db.execute("select count(*) from campaignexecution where lower(status) in ('running','pending')").fetchone()[0]:
            raise RuntimeError("A campaign is active; local migration postponed")
        if db.execute("select count(*) from backgroundjob where active=1").fetchone()[0]:
            raise RuntimeError("A background job is active; local migration postponed")


def main(apply):
    check_idle(DATABASE)
    before = table_data(DATABASE)
    with tempfile.TemporaryDirectory(prefix="marketingos-local-migration-") as folder:
        reference, trial = Path(folder) / "reference.db", Path(folder) / "trial.db"
        alembic(reference, "upgrade", MATCHING_REVISION)
        copy_database(DATABASE, trial)
        added = reconcile(trial, reference)
        alembic(trial, "upgrade", "head")
        alembic(trial, "check")
        if table_data(trial, before) != before:
            raise RuntimeError("Trial migration changed existing rows")
        report = {"trial": "passed", "matching_revision": MATCHING_REVISION, "reconciled_columns": added,
                  "existing_rows_unchanged": True, "applied": False}
        if apply:
            check_idle(DATABASE)
            if table_data(DATABASE) != before:
                raise RuntimeError("Database changed during validation; refusing live migration")
            backup = BACKEND / "backups" / ("marketingos-before-architecture-v2-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + ".db")
            backup.parent.mkdir(exist_ok=True)
            copy_database(DATABASE, backup)
            if table_data(backup) != before:
                raise RuntimeError("Backup verification failed")
            reconcile(DATABASE, reference)
            alembic(DATABASE, "upgrade", "head")
            alembic(DATABASE, "check")
            if table_data(DATABASE, before) != before:
                raise RuntimeError("Existing row validation failed; preserve backup for recovery")
            report.update(applied=True, backup=str(backup), target_revision="c53a9f27d401")
        (HERE / "local-migration.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    main(parser.parse_args().apply)
