import os
import subprocess
import sys
from pathlib import Path


def test_logout_immediately_revokes_admin_access(client, sign_in):
    headers = sign_in()
    assert client.post("/api/auth/logout", headers=headers).status_code == 204
    assert client.get("/api/auth/me", headers=headers).status_code == 401


def test_admin_production_import_needs_only_admin_secrets(tmp_path):
    root = Path(__file__).resolve().parents[3]
    env = {key: value for key, value in os.environ.items()
           if key not in {"JWT_SECRET", "PASSWORD_PEPPER", "PYTHONPATH"}}
    env.update(APP_ENV="production", ENVIRONMENT="production", DATABASE_URL="sqlite://",
               ADMIN_JWT_SECRET="isolated-test-admin-signing-secret-" * 2,
               ADMIN_PWD_PEPPER="isolated-test-admin-password-pepper-" * 2,
               PYTHONPATH=os.pathsep.join([str(root / "backend"), str(root / "administration/backend")]))
    result = subprocess.run([sys.executable, "-c", "from admin.main import app; assert app"],
                            cwd=tmp_path, env=env, capture_output=True, text=True, timeout=30, check=False)
    assert result.returncode == 0, result.stderr
