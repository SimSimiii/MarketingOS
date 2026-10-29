"""One live extraction, preserving the proposal before reference verification."""
import asyncio
import json
from dataclasses import asdict
from pathlib import Path
from uuid import UUID
import sys

sys.path.insert(0, str(Path.cwd()))  # invoke from backend/, like all backend commands

from sqlmodel import Session
from app.ai.factory import get_ai_provider
from app.core.database import engine
from app.market.rivals import RivalLead, RivalScout
from app.services.market_service import MarketService, _session_for

OUT = Path(__file__).parent

async def main():
    with Session(engine) as db:
        service = MarketService(db)
        brand = UUID(json.loads((OUT / 'case.json').read_text(encoding='utf-8'))['brand_id'])
        artifacts = service.artifacts_for(brand)
        snapshot = service.snapshot(brand)
        rival = next(r for r in snapshot.rivals if r.name == 'Fathom Analytics')
    session = _session_for(get_ai_provider(), brand)
    original = session.structured
    async def capture(**kwargs):
        answer = await original(**kwargs)
        (OUT / 'functional-rationale-proposal.json').write_text(
            json.dumps({'proposal': answer.model_dump(mode='json'),
                        'our_context': kwargs['variables']['our_context'],
                        'usage': asdict(session.usage)}, ensure_ascii=False, indent=2), encoding='utf-8')
        return answer
    session.structured = capture
    profile = await RivalScout(session).profile(
        RivalLead(name=rival.name, url=rival.url, why=rival.discovery_reason), artifacts=artifacts)
    (OUT / 'functional-rationale-diagnostic.json').write_text(
        json.dumps({'profile': profile.model_dump(mode='json'), 'usage': asdict(session.usage)},
                   ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'status': profile.rationale_status, 'why': profile.why, 'calls': len(session.usage.calls)}))

asyncio.run(main())
