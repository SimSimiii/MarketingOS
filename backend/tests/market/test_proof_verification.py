"""Synthetic web findings; no real network, model or subscription calls."""

import httpx
import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.knowledge.artifacts import BusinessProfile
from app.knowledge.ledger import EvidenceContext
from app.market.audience_research import FixedURLFetcher
from app.market.proof import ProofCandidate, ProofHunter, ProofVerification
from app.market.store import MarketStore
from app.models.brand import Brand
from app.models.market import ProofCandidateRow

QUOTE = "Our studio uses this tool to export the selected invoices as a CSV file."


async def public_resolver(_host):
    return ["93.184.216.34"]


@pytest.mark.asyncio
async def test_snippet_or_model_verification_never_certifies_a_missing_quote(provider, session):
    provider.push("proof_hunt", {"candidates": [{
        "claim": "A studio uses the CSV export", "verbatim": QUOTE,
        "url": "https://synthetic.example/review", "confidence": 1,
        "verification_status": "quote_verified",
        "context": {"verification": "independently verified"},
    }]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _request: httpx.Response(
        200, text="This fetched page talks about an unrelated product. " * 4,
        headers={"content-type": "text/plain"},
    ))) as client:
        result = await ProofHunter(session, FixedURLFetcher(client, resolver=public_resolver)).hunt(
            BusinessProfile(company_name="Synthetic studio tool")
        )
    found = result.candidates[0]
    assert found.verification_status is ProofVerification.QUOTE_NOT_FOUND
    assert found.context.verification == "quote_not_found"
    assert provider.calls["proof_hunt"] == 1
    assert found.as_evidence("P1").strength == "weak"


@pytest.mark.asyncio
@pytest.mark.parametrize("status,content,expected", [
    (200, QUOTE + " This was our experience during a two week pilot.", "quote_verified"),
    (503, "Service unavailable", "page_unavailable"),
])
async def test_proof_reports_observed_source_status(provider, session, status, content, expected):
    provider.push("proof_hunt", {"candidates": [{
        "claim": "A studio uses exports", "verbatim": QUOTE,
        "url": "https://synthetic.example/review", "confidence": 0.1,
    }]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _request: httpx.Response(
        status, text=content, headers={"content-type": "text/plain"},
    ))) as client:
        result = await ProofHunter(session, FixedURLFetcher(client, resolver=public_resolver)).hunt(
            BusinessProfile(company_name="Synthetic studio tool")
        )
    assert result.candidates[0].verification_status == expected
    assert len(provider.requests) == 1


def test_persisted_proof_context_survives_approval_and_legacy_is_not_verified(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'proof.db'}")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        brand = Brand(name="Synthetic studio tool")
        session.add(brand)
        session.commit()
        store = MarketStore(session)
        candidate = ProofCandidate(
            claim="A studio uses exports", verbatim=QUOTE,
            url="https://synthetic.example/review", attributed_to="Studio",
            verification_status="quote_verified",
            context=EvidenceContext(subject="Studio", conditions="two week pilot"),
        )
        row = store.record_candidates(brand.id, [candidate])[0]
        store.decide(row, True)
        evidence = store.approved_evidence(brand.id)[0]
        assert evidence.context.conditions == "two week pilot"
        assert "quote_verified" in evidence.context.verification
        legacy = ProofCandidateRow(
            brand_id=brand.id, claim="Legacy quote", verbatim=QUOTE,
            status="approved", evidence_id="P2", url="https://legacy.example/review",
        )
        session.add(legacy)
        session.commit()
        old = next(item for item in store.approved_evidence(brand.id) if item.id == "P2")
        assert "not_checked" in old.context.verification
        assert old.strength == "weak"
