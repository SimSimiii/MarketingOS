"""One authorized real draft through the normal campaign service, without an HTTP server.

Run from backend/. Persists the execution id before awaiting its normal background
task. Collect afterwards with optimize_campaign.py resume against the read API.
No application lifespan, schema initialization, orphan reaping or server mutation.
"""
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path.cwd()))

from sqlmodel import Session, select
from app.ai.factory import get_ai_provider
from app.core.database import engine
from app.models.campaign_execution import CampaignExecution
from app.models.enums import ExecutionStatus
from app.orchestration.execution_registry import registry
from app.services.campaign_service import CampaignService

ROOT = Path(__file__).parent
REVISION = "buffer-homepage-first-audience"

async def main():
    state_file = ROOT / "state.json"
    state = json.loads(state_file.read_text(encoding="utf-8"))
    case = json.loads((ROOT / "case.json").read_text(encoding="utf-8"))
    if any(not run.get("result_dir") for run in state.get("runs", [])):
        raise RuntimeError("Collect the existing execution before launching another.")
    if any(run.get("code_revision") == REVISION for run in state.get("runs", [])):
        raise RuntimeError("This revision already launched; resume it, do not buy a duplicate.")
    with Session(engine) as db:
        if db.exec(select(CampaignExecution).where(CampaignExecution.status == ExecutionStatus.RUNNING)).first():
            raise RuntimeError("An execution is already running.")
        service = CampaignService(db, get_ai_provider())
        campaign = service.get_campaign(UUID(case["campaign_id"]))
        if campaign is None:
            raise RuntimeError("Campaign not found.")
        advice = service.generation_advice(campaign)
        if not advice.can_generate or advice.override_required:
            raise RuntimeError("Readiness changed; inspect it before any launch.")
        execution = await service.start_execution(campaign)
        handle = registry.get(execution.id)
        if handle is None:
            raise RuntimeError("Background handle absent; inspect persisted execution, do not retry.")
        entry = {"execution_id": str(execution.id), "campaign_id": str(campaign.id), "status": "running",
                 "launched_at": datetime.now(UTC).isoformat(), "code_revision": REVISION,
                 "launch_method": "Normal CampaignService.start_execution in a standalone worker; no HTTP server."}
        state.setdefault("runs", []).append(entry)
        state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(entry), flush=True)
    await handle.task
    with Session(engine) as db:
        finished = db.get(CampaignExecution, execution.id)
        print(json.dumps({"execution_id": str(execution.id), "status": str(finished.status),
                          "outcome_status": finished.outcome_status, "needs_review": finished.needs_review}), flush=True)

asyncio.run(main())
