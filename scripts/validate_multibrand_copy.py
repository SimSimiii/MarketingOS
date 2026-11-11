"""Bounded real-copy evaluation on a SQLite backup; never sends email.

Run from backend with its Python: ../scripts/validate_multibrand_copy.py prepare|run NAME.
"""
import asyncio
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import time
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/optimization/multibrand-copy-2026-10-31'
DB = Path(tempfile.gettempdir()) / 'marketingos-multibrand-copy-2026-10-31.sqlite'
os.environ['DATABASE_URL'] = 'sqlite:///' + DB.as_posix()
sys.path.insert(0, str(ROOT / 'backend'))
SOURCES = {'cabaia': '12fa6da250644708bbafd26ec32b62a9',
           'papier': '1c67cc7615c246078b298260d0b6a00c',
           'fathom': '435cb5351efa44709cf4e1aa0d7e49f9',
           'systeme': 'dcf53216c3d141419cb948b1bea52524',
           'senja': 'a79f8375e5574861990e3a5fdf35ea2a'}


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding='utf-8')


def prepare():
    if not DB.exists():
        with sqlite3.connect(ROOT / 'backend/marketingos.db') as source, sqlite3.connect(DB) as target:
            source.backup(target)
    from alembic import command
    from alembic.config import Config
    command.upgrade(Config(str(ROOT / 'backend/alembic.ini')), 'head')
    from sqlmodel import Session
    from app.core.database import engine
    from app.ai.factory import get_ai_provider
    from app.models import Campaign
    from app.services.campaign_service import CampaignService
    from app.orchestration.campaign_orchestrator import _DbKnowledgeGateway
    for name, source_id in SOURCES.items():
        folder = OUT / name
        if (folder/'case.json').exists():
            print(name, 'already prepared', flush=True)
            continue
        with Session(engine) as db:
            source = db.get(Campaign, UUID(source_id))
            fields = source.model_dump(exclude={'id','created_at','updated_at','status','archived_at'})
            fields.update(name='Multi-brand validation: ' + name,
                          policy={'preset':'fast','strategy_mode':'planned',
                                  'max_duration_seconds':900,'max_total_tokens':400000},
                          model_overrides=None, steering=None)
            if name == 'fathom':
                fields['request'] = ('Write exactly 3 acquisition emails in English for the selected audience. '
                                     'Build a coherent sequence with distinct reasons to evaluate Fathom Analytics '
                                     'and documented next steps. Do not assume prior contact, opens or replies.')
                fields['policy'].update(sequence_pass=True, max_sequence_reworks=1)
                fields['steering'] = {'items':[], 'instructions':[
                    {'text':'Keep each email concise, under 150 words.','scope':'sequence'},
                    {'text':'End the body with the exact sentence: Would this fit your site?',
                     'scope':'email','position':2}]}
            campaign = Campaign(**fields)
            db.add(campaign); db.commit(); db.refresh(campaign)
            service = CampaignService(db, get_ai_provider())
            forecast = service.forecast_run(campaign)
            advice = service.generation_advice(campaign)
            gateway = _DbKnowledgeGateway(db, campaign)
            knowledge = gateway.load()
            save(folder/'case.json', {'brand_id':campaign.brand_id,'campaign_id':campaign.id,
                                    'source_campaign_id':source.id,'database':str(DB)})
            save(folder/'campaign.json', campaign.model_dump(mode='json'))
            save(folder/'forecast.json', forecast.model_dump(mode='json'))
            save(folder/'advice.json', advice.model_dump(mode='json'))
            save(folder/'knowledge.json', knowledge.artifacts.model_dump(mode='json'))
            save(folder/'state.json', {'status':'prepared','quality_history':[]})
            (folder/'journal.md').write_text('# Validation multi-marques\n\n'
                'Grille: faits25, audience/offre20, argument20, continuité15, finition10, '
                'absence de promesses indues/répétitions10. Jugement interne, pas une mesure de conversion.\n'
                'Preset fast; Fathom ajoute une revue de séquence et une consigne propre à email2. '
                'Connaissances et audience existantes; aucune aide factuelle manuelle.\n', encoding='utf-8')
            print(name, forecast.model_dump(), 'can_generate=', advice.can_generate,
                  'override=', advice.override_required, flush=True)


async def run(name):
    from sqlmodel import Session, select
    from app.core.database import engine
    from app.ai.factory import get_ai_provider
    from app.models import Campaign, GeneratedAsset, AgentExecution, ExecutionLog
    from app.orchestration.campaign_orchestrator import CampaignOrchestrator
    folder = OUT/name
    state = json.loads((folder/'state.json').read_text(encoding='utf-8'))
    if state['status'] != 'prepared':
        raise RuntimeError('Already launched; inspect saved execution before any retry.')
    case = json.loads((folder/'case.json').read_text(encoding='utf-8'))
    advice = json.loads((folder/'advice.json').read_text(encoding='utf-8'))
    forecast = json.loads((folder/'forecast.json').read_text(encoding='utf-8'))
    discovery = UUID(case['source_campaign_id']) == UUID(SOURCES['cabaia'])
    if not advice.get('can_generate', True) or (advice.get('override_required') and not discovery) or not forecast['knowledge_reused']:
        save(folder/'state.json', {'status':'blocked_preflight','advice':advice,'forecast':forecast})
        print(name, 'blocked_preflight', flush=True)
        return
    started = time.monotonic()
    with Session(engine) as db:
        campaign = db.get(Campaign, UUID(case['campaign_id']))
        orchestrator = CampaignOrchestrator(db, get_ai_provider())
        if discovery:
            with (folder/'journal.md').open('a', encoding='utf-8') as journal:
                journal.write('\nMode découverte explicitement évalué: preuve de capacité manquante. '
                              'Autorisation de génération malgré réserve, sans modifier le dossier ni ses faits. '
                              'Ne pas présenter ce cas comme prêt en génération normale.\n')
        execution = orchestrator.create_execution(campaign,
            recommendation_snapshot=advice.get('recommendation'),
            generated_despite_recommendation=discovery and advice.get('override_required', False))
        save(folder/'state.json', {'status':'running','execution_id':execution.id})
        print(name, 'started', execution.id, flush=True)
        try:
            execution = await orchestrator.execute(campaign, execution)
        finally:
            db.refresh(execution)
            save(folder/'execution.json', execution.model_dump(mode='json'))
            for model, filename in [(GeneratedAsset,'assets'),(AgentExecution,'calls'),(ExecutionLog,'logs')]:
                rows = db.exec(select(model).where(model.campaign_execution_id == execution.id)).all()
                save(folder/(filename+'.json'), [r.model_dump(mode='json') for r in rows])
                if model is GeneratedAsset:
                    for asset in rows:
                        (folder/f'email-{asset.position}.txt').write_text(asset.content, encoding='utf-8')
                        if asset.content_html:
                            (folder/f'email-{asset.position}.html').write_text(asset.content_html, encoding='utf-8')
            save(folder/'state.json', {'status':str(execution.status),'execution_id':execution.id,
                 'elapsed_seconds':round(time.monotonic()-started,1),'review':'pending'})
            print(name, execution.status, execution.error_message, flush=True)


async def revise(name, position=None):
    from sqlmodel import Session
    from app.core.database import engine
    from app.ai.factory import get_ai_provider
    from app.models import EmailRevision
    from app.services.revision_service import run_job
    folder = OUT/name
    if (folder/'revision.json').exists():
        raise RuntimeError('Revision already attempted; inspect before spending again.')
    assets = json.loads((folder/'assets.json').read_text(encoding='utf-8'))
    selected_position = position if position is not None else (2 if name.startswith('systeme') else 1)
    asset = next(a for a in assets if a['position'] == selected_position)
    instruction = ('Plus direct et plus court, conserve les faits, la transparence affiliation et les consignes propres à cet email.'
                   if name.startswith('systeme') else
                   'Make the opening more concrete and direct. Keep all claims supported and the same next step. Under 110 words in the body.')
    start = time.monotonic()
    with Session(engine) as db:
        row = EmailRevision(asset_id=UUID(asset['id']),
             campaign_execution_id=UUID(asset['campaign_execution_id']), instruction=instruction)
        db.add(row); db.commit(); db.refresh(row)
        revision_id = row.id
        save(folder/'revision.json', {'status':'running','id':revision_id,'instruction':instruction})
    await run_job(engine, revision_id, get_ai_provider())
    with Session(engine) as db:
        row = db.get(EmailRevision, revision_id)
        save(folder/'revision.json', {**row.model_dump(mode='json'), 'elapsed_seconds':time.monotonic()-start})
        (folder/'revision.txt').write_text(row.content, encoding='utf-8')
        if row.content_html:
            (folder/'revision.html').write_text(row.content_html, encoding='utf-8')
        print(name, row.state, row.calls, row.error, flush=True)


if __name__ == '__main__':
    if sys.argv[1] == 'prepare':
        prepare()
    elif sys.argv[1] == 'revise':
        asyncio.run(revise(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else None))
    else:
        asyncio.run(run(sys.argv[2]))
