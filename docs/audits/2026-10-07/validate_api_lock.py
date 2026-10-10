"""Install the API hash lock in a disposable venv, without calling providers."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "backend"


def run(args, env):
    result = subprocess.run(args, cwd=BACKEND, env=env, text=True, capture_output=True, timeout=300)
    if result.returncode:
        raise RuntimeError((result.stdout + result.stderr)[-4000:])
    return result.stdout.strip()


def validate():
    env = {
        **os.environ, "APP_ENV": "test", "DATABASE_URL": "sqlite://", "AI_BILLING": "api",
        "AUTH_REQUIRED": "true", "CREDIT_BILLING_ENABLED": "false",
        "OPENAI_API_KEY": "test-unused-openai-key", "ANTHROPIC_API_KEY": "test-unused-anthropic-key",
        "STRIPE_SECRET_KEY": "sk_test_unused", "STRIPE_WEBHOOK_SECRET": "whsec_unused",
    }
    with tempfile.TemporaryDirectory(prefix="marketingos-api-lock-") as directory:
        folder = Path(directory).resolve()
        assert folder.is_relative_to(Path(tempfile.gettempdir()).resolve())
        run([sys.executable, "-m", "venv", str(folder)], env)
        python = folder / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        run([str(python), "-m", "pip", "install", "--require-hashes", "-r", "requirements.txt"], env)
        run([str(python), "-m", "pip", "install", "--no-deps", "-e", "."], env)
        print(run([str(python), "-m", "pip", "check"], env))
        code = (
            "from app.main import app; "
            "from app.ai.factory import get_ai_provider; "
            "print('API imports and provider construction:', type(get_ai_provider()).__name__)"
        )
        for prepaid in ("false", "true"):
            print(f"prepaid={prepaid}: " + run(
                [str(python), "-c", code], {**env, "CREDIT_BILLING_ENABLED": prepaid},
            ))
    print("Disposable API installation passed; no server lifespan or provider request executed.")


if __name__ == "__main__":
    validate()
