"""The operator launches one run, with only user-specified total caps."""

import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture
def runner(tmp_path, monkeypatch):
    path = Path(__file__).resolve().parents[2] / "scripts/optimize_campaign.py"
    spec = importlib.util.spec_from_file_location("optimization_runner", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    case = tmp_path / "case.json"
    case.write_text(json.dumps({"brand_id": "brand", "campaign_id": "campaign"}))
    module.save(tmp_path / "state.json", {"runs": [
        {"execution_id": str(i), "result_dir": f"runs/{i}"} for i in range(4)
    ]})
    calls = []

    def api(base, path, token=None, method="GET", data=None):
        calls.append((method, path))
        if path == "/campaigns/campaign":
            return {"brand_id": "brand"}
        if path.endswith("/start"):
            return {"id": "new-run"}
        return {"status": "completed"}

    monkeypatch.setattr(module, "api", api)
    monkeypatch.setattr("sys.argv", [str(path), "run", "--case", str(case)])
    return module, calls, tmp_path


def test_default_allows_another_cycle_but_launches_only_one_run(runner):
    module, calls, directory = runner
    assert module.main() == 0
    assert sum(method == "POST" for method, _ in calls) == 1
    state = json.loads((directory / "state.json").read_text())
    assert len(state["runs"]) == 5
    assert state["runs"][-1]["result_dir"]


def test_explicit_user_cap_prevents_launch(runner, monkeypatch):
    import sys

    module, calls, _ = runner
    monkeypatch.setattr(sys, "argv", [*sys.argv, "--max-runs", "4"])
    with pytest.raises(RuntimeError, match="Generation limit reached"):
        module.main()
    assert not any(method == "POST" for method, _ in calls)


def test_pending_capture_prevents_duplicate_launch(runner):
    module, calls, directory = runner
    module.save(directory / "state.json", {"runs": [{"execution_id": "pending"}]})
    with pytest.raises(RuntimeError, match="use resume"):
        module.main()
    assert not any(method == "POST" for method, _ in calls)


def test_summary_reads_latest_snapshot_without_api_or_generation(runner, monkeypatch, capsys):
    import sys

    module, calls, directory = runner
    run_dir = directory / "runs" / "3"
    module.save(run_dir / "result.json", {
        "status": "completed", "estimated_cost_usd": 3.5,
        "agent_executions": [{"id": "a"}, {"id": "b"}],
        "assets": [{"title": "Email 1", "content": "Full email body"}],
        "result": {"report": {
            "delivered": 1, "promised": 1,
            "emails": [{"position": 1, "subject": "Subject", "pull": 7,
                        "evidence_spent": ["E1"],
                        "reader_verdicts": [{"biggest_doubt": "Setup effort is unclear."}]}],
        }},
    })
    module.save(run_dir / "logs.json", [
        {"level": "info", "message": "normal"},
        {"level": "error", "step": "writer", "message": "failed once"},
    ])
    monkeypatch.setattr(sys, "argv", [sys.argv[0], "summary", "--case", str(directory / "case.json")])

    assert module.main() == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["execution_id"] == "3"
    assert summary["agent_calls"] == 2
    assert summary["emails"][0]["reader_doubts"] == ["Setup effort is unclear."]
    assert summary["error_logs"] == [{"step": "writer", "message": "failed once"}]
    assert "Full email body" not in json.dumps(summary)
    assert calls == []
