"""French copy must preserve factual meaning and explicit user instructions."""

import unicodedata

import pytest

from app.knowledge.artifacts import BusinessProfile
from app.knowledge.ledger import ClaimKind, EvidenceIndex, EvidenceLedger, extract_claims
from app.marketing.contract import parse_contract
from app.marketing.email_copy import Email
from app.marketing.gates import clarity_gate, spam_gate


def draft(body):
    return Email(position=1, language="fr", subject="Votre proposition", body=body,
                 preview_text="Le fonctionnement en pratique", greeting="Bonjour,",
                 call_to_action="Voir le fonctionnement", sign_off="L’équipe")


@pytest.mark.parametrize("amount", ["9 €", "29,90 €", "2 990 euros", "2\u202f990 €"])
def test_french_prices_are_typed_and_require_evidence(amount):
    claims = extract_claims(amount)
    assert len(claims) == 1
    assert claims[0].kind == ClaimKind.MONEY
    assert EvidenceIndex(EvidenceLedger()).unsupported(amount)


@pytest.mark.parametrize(("source", "copy"), [
    ("29 modèles disponibles", "29 € par mois"),
    ("29,90 euros par mois", "2990 euros par mois"),
    ("3 jours", "3 semaines"),
])
def test_unrelated_numbers_do_not_license_a_claim(source, copy):
    assert EvidenceIndex(EvidenceLedger(), source_text=source).unsupported(copy)


@pytest.mark.parametrize(("source", "copy"), [
    ("29,90 euros", "29.90 euros"),
    ("2\u202f990 euros", "2990 euros"),
    ("3 jours", "3 days"),
])
def test_equivalent_french_measurements_remain_licensed(source, copy):
    assert not EvidenceIndex(EvidenceLedger(), source_text=source).unsupported(copy)


def test_french_quotation_requires_a_real_source():
    quote = "Cette solution a changé notre façon de travailler ensemble."
    text = f"« {quote} »"
    assert EvidenceIndex(EvidenceLedger()).unsupported(text)
    assert not EvidenceIndex(EvidenceLedger(), source_text=quote).unsupported(text)


@pytest.mark.parametrize("name", ["Élan", "Café Crème", "Réuni"])
def test_accented_names_are_recognized_in_canonical_unicode_forms(name):
    business = BusinessProfile(company_name=name, category="outil")
    assert not clarity_gate(draft(unicodedata.normalize("NFD", name)), business).blocking
    assert clarity_gate(draft("Un outil sans nom."), business).blocking


@pytest.mark.parametrize("acronym", ["RGPD", "CNIL", "SIRET"])
def test_legitimate_french_acronyms_do_not_trigger_spam(acronym):
    assert not spam_gate(draft(f"Les informations relatives à {acronym} sont disponibles.")).blocking


@pytest.mark.parametrize(("instruction", "count"), [
    ("Écris cinq emails", 5), ("Écris douze emails", 12),
    ("Donne trois raisons pour un email", 1), ("Écris deux emails", 2),
])
def test_french_requested_count_is_respected(instruction, count):
    contract = parse_contract(instruction)
    assert contract.count == count
    assert contract.count_is_explicit


@pytest.mark.parametrize(("source", "copy"), [
    ("29,90 euros", "€29.90"), ("$29", "29 dollars"),
    ("£29", "29 GBP"), ("29 EUR", "29 €"),
])
def test_currency_spelling_and_position_are_equivalent(source, copy):
    assert not EvidenceIndex(EvidenceLedger(), source_text=source).unsupported(copy)


@pytest.mark.parametrize(("source", "copy"), [
    ("Pro est 29 € par mois.", "Basic est 29 € par mois."),
    ("Pro est 29 € par an.", "Pro est 29 € par mois."),
    ("Pro est 29 € par mois avec engagement annuel.", "Pro est 29 € par mois."),
    ("Pro est 29 € par mois hors TVA.", "Pro est 29 € par mois."),
])
def test_french_offer_scope_cannot_be_silently_changed(source, copy):
    assert EvidenceIndex(EvidenceLedger(), source_text=source).unsupported(copy)


def test_french_annual_commitment_is_allowed_when_preserved():
    source = "Pro est 29 € par mois avec engagement annuel."
    assert not EvidenceIndex(EvidenceLedger(), source_text=source).unsupported(source)

