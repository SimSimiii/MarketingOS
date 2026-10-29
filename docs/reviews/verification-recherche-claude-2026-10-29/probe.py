"""Read-only probes of production functions; run with backend's venv Python."""
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "backend"
os.chdir(BACKEND)
sys.path.insert(0, str(BACKEND))
runpy.run_path(str(BACKEND / "tests/conftest.py"))

from app.knowledge.artifacts import BusinessProfile, OfferSheet
from app.knowledge.ledger import EvidenceIndex, EvidenceLedger, extract_claims
from app.marketing.contract import parse_contract
from app.marketing.email_copy import Email
from app.marketing.gates import clarity_gate, run_all, spam_gate


def email(body):
    return Email(position=1, language="fr", subject="Une proposition de relecture",
                 preview_text="Un exemple pour examiner le fonctionnement.",
                 greeting="Bonjour,", body=body, call_to_action="Voir le fonctionnement",
                 sign_off="L'équipe")


result = {"scope": "Production pure functions only; no server, database session or model calls.",
          "brands": [], "claims": [], "acronyms": [], "contracts": []}
empty = EvidenceIndex(EvidenceLedger())
for name in ["Elan", "Élan", "Café Crème"]:
    draft = email(f"{name} est un outil de relecture de documents.")
    profile = BusinessProfile(company_name=name, category="outil")
    direct = clarity_gate(draft, profile)
    combined, _ = run_all(draft, evidence=empty, offer=OfferSheet(), business=profile)
    result["brands"].append({"name": name, "clarity_blocking": bool(direct.blocking),
                            "run_all_clarity": [x.model_dump(mode="json") for x in combined.issues if x.gate == "clarity"],
                            "note": "Other structural issues in deliberately short probe are not assessed."})
for text in ["29 € par mois", "9 € par mois", "29,90 € par mois", "en 3 jours", "en 3 minutes",
             "« Cette solution a changé notre façon de travailler ensemble. »",
             '"Cette solution a changé notre façon de travailler ensemble."']:
    result["claims"].append({"text": text,
        "extracted": [x.model_dump(mode="json") for x in extract_claims(text)],
        "unsupported_empty": [x.model_dump(mode="json") for x in empty.unsupported(text)]})
for source, text in [("29 modèles disponibles", "29 € par mois"), ("29,90 euros par mois", "2990 euros par mois")]:
    index = EvidenceIndex(EvidenceLedger(), source_text=source)
    result["claims"].append({"source": source, "text": text,
                            "unsupported": [x.model_dump(mode="json") for x in index.unsupported(text)]})
for acronym in ["RGPD", "CNIL", "SIRET", "HTTP"]:
    report = spam_gate(email(f"Les informations relatives à {acronym} sont disponibles."))
    result["acronyms"].append({"text": acronym, "issues": [x.model_dump(mode="json") for x in report.issues]})
for request in ["Écris cinq emails", "Écris 5 emails", "Write five emails"]:
    result["contracts"].append({"request": request, "result": parse_contract(request).model_dump(mode="json")})
result["source_sha256"] = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in [
    "backend/app/knowledge/ledger.py", "backend/app/marketing/gates.py", "backend/app/marketing/contract.py"]}
print(json.dumps(result, ensure_ascii=False, indent=2))
