"""Exercise migration creation, rollback and metadata parity on a disposable SQLite file."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="marketingos-migrations-") as folder:
        env = {**os.environ, "APP_ENV": "test",
               "DATABASE_URL": f"sqlite:///{Path(folder).as_posix()}/migration.db"}
        for args in (("upgrade", "head"), ("check",), ("downgrade", "b1d7c9f4a20e"),
                     ("upgrade", "head"), ("check",)):
            subprocess.run([sys.executable, "-m", "alembic", *args], cwd=root,
                           env=env, check=True, timeout=120)
    print("Disposable SQLite migrations and metadata parity passed.")


if __name__ == "__main__":
    main()
