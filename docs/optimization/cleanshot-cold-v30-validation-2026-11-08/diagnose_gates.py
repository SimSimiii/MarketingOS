import json
from pathlib import Path
from app.knowledge.ledger import EvidenceIndex, EvidenceLedger, _price_supports, ClaimKind
from app.marketing.email_copy import Email, render_review
from app.marketing.gates import spam_gate, evidence_gate
case = Path(__file__).resolve().parent
knowledge = json.loads((case / 'knowledge-final.json').read_text(encoding='utf-8'))
ledger = EvidenceLedger.model_validate(knowledge['artifacts']['evidence'])
docs = json.loads((case / 'documents-full.json').read_text(encoding='utf-8'))
corpus = '\n\n'.join(d['content'] for d in docs)
index = EvidenceIndex(ledger, corpus)
drafts = json.loads((case / 'rejected-drafts.json').read_text(encoding='utf-8'))
checks = []
for draft in drafts:
    email = Email.model_validate(draft)
    checks.append({'attempt': draft['attempt'], 'spam': spam_gate(email, company_name='CleanShot').model_dump(mode='json'), 'evidence': evidence_gate(render_review(email), index).model_dump(mode='json')})
output = {'purpose':'Read-only deterministic reproduction on unchanged rejected drafts; no model, app mutation, repaired draft, or campaign launch.', 'checks':checks,'price_aliases':index._price_aliases, 'ten_dollar_sources':[s.model_dump(mode='json') if hasattr(s,'model_dump') else vars(s) for s in index._price_support.get('10',[])]}
(case / 'gate-replay.json').write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding='utf-8')
print(json.dumps({'checks':checks,'aliases':index._price_aliases}, ensure_ascii=False))
