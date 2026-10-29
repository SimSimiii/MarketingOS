"""Free behavioral checks of the installed skill's local command queue."""
import contextlib
import importlib.util
import io
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

script = Path("C:/Users/oussa/.codex/skills/marketingos-brand-audit/scripts/audit_session.py")
spec = importlib.util.spec_from_file_location("audit_session_skill", script)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    case = root / "case.json"
    case.write_text("{}", encoding="utf-8")
    with module.lock(root / "exclusive.lock"):
        try:
            with module.lock(root / "exclusive.lock"):
                raise AssertionError("A second owner acquired the same lock.")
        except OSError:
            pass
    # No API/model calls: advancing monotonic time just stops the submitter's wait.
    with patch.object(sys, "argv", [str(script), "audit", "capture", "--case", str(case)]):
        with patch.object(module.time, "monotonic", side_effect=[0, 100]):
            with contextlib.redirect_stdout(io.StringIO()):
                module.main()
    queue = module.pending(root / ".audit-session")
    assert len(queue) == 1
    assert json.loads(queue[0].read_text())["action"] == "capture"
    with patch.object(sys, "argv", [str(script), "audit", "create", "--case", str(case)]):
        try:
            module.main()
            raise AssertionError("A duplicate mutation was enqueued while pending.")
        except SystemExit as exc:
            assert "already pending" in str(exc)
    assert len(list((root / ".audit-session/commands").glob("*.json"))) == 1
    module.save(root / ".audit-session/responses" / queue[0].name, {"ok": True})
    assert not module.pending(root / ".audit-session")
print("Passed: exclusive ownership, pending command preservation, duplicate rejection and response completion.")
