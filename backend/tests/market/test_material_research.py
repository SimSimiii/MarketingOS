from datetime import UTC, datetime

from app.knowledge.corpus import SourceCorpus
from app.knowledge.ledger import Evidence, EvidenceKind, EvidenceStrength
from app.market.audience_research import FetchedSource, SourceTier
from app.market.material_research import (
    MaterialClaim,
    MaterialRecovery,
    _MaterialDraft,
    apply_recovery,
    existing_recovery,
    verify_material,
)
from tests.marketing.conftest import artifacts_fixture


def fetched_page(content: str) -> FetchedSource:
    return FetchedSource(
        requested_url="https://docs.example.com/integration",
        final_url="https://docs.example.com/integration",
        title="Official integration",
        tier=SourceTier.INTERPRETATION,
        venue="Example",
        fetched_at=datetime.now(UTC),
        content_hash="a" * 64,
        content=content,
    )


def test_only_a_quote_present_on_the_fetched_official_page_becomes_evidence():
    source = fetched_page(
        "The native integration creates an API key and fills the SMTP settings automatically."
    )
    draft = _MaterialDraft(
        claims=[
            MaterialClaim(
                source_id="S1",
                claim="the integration fills the SMTP settings",
                verbatim="fills the SMTP settings automatically",
            ),
            MaterialClaim(
                source_id="S1",
                claim="migration takes five minutes",
                verbatim="Migration takes five minutes.",
            ),
        ]
    )

    recovery = verify_material(
        gap="Explain the exact SMTP connection path.",
        draft=draft,
        fetched=[source],
        existing_ids={"E1", "R1"},
    )

    assert [entry.id for entry in recovery.evidence] == ["R2"]
    assert recovery.evidence[0].source == source.final_url
    assert recovery.dropped_claims == 1


def test_verified_material_extends_both_the_ledger_and_the_gate_corpus():
    artifacts = artifacts_fixture()
    source = fetched_page(
        "The native integration creates an API key and fills the SMTP settings automatically."
    )
    recovery = verify_material(
        gap="Explain the exact SMTP connection path.",
        draft=_MaterialDraft(
            claims=[
                MaterialClaim(
                    source_id="S1",
                    claim="the integration fills the SMTP settings",
                    verbatim="fills the SMTP settings automatically",
                )
            ]
        ),
        fetched=[source],
        existing_ids=artifacts.evidence.ids,
    )

    enriched, corpus = apply_recovery(artifacts, SourceCorpus(), recovery)

    assert enriched.evidence.get("R1") is not None
    assert "fills the SMTP settings automatically" in corpus.text
    assert any(item.startswith("auto:") for item in enriched.source_document_ids)


def test_a_recovered_duplicate_uses_the_retained_id_in_the_next_brief():
    artifacts = artifacts_fixture()
    known = artifacts.evidence.entries[0]
    duplicate = known.model_copy(update={"id": "R1"})
    fresh = Evidence(
        id="R2", kind=EvidenceKind.GUARANTEE,
        claim="Replacement shipping depends on the region.",
        verbatim="Replacement shipping depends on the region.",
        source="https://docs.example.com/guarantee",
        strength=EvidenceStrength.STRONG,
    )
    recovery = MaterialRecovery(gap="Price and replacement terms", evidence=[duplicate, fresh])
    before = artifacts.evidence.ids.copy()

    enriched, _ = apply_recovery(artifacts, SourceCorpus(), recovery)

    assert artifacts.evidence.ids == before
    assert enriched.evidence.ids == before | {"R2"}
    assert [entry.id for entry in recovery.evidence] == [known.id, "R2"]
    assert all(enriched.evidence.get(entry.id) is not None for entry in recovery.evidence)
    assert "(1 new)" in enriched.notes[-1]


def test_a_matching_verified_recovery_is_reused_before_new_research():
    artifacts = artifacts_fixture()
    artifacts.evidence.entries.extend(
        [
            Evidence(
                id="R1",
                kind=EvidenceKind.INTEGRATION,
                claim="Supabase custom SMTP is configured in Authentication settings.",
                verbatim="Configure custom SMTP on the Authentication settings page.",
                source="https://supabase.com/docs/guides/auth/auth-smtp",
                strength=EvidenceStrength.STRONG,
            ),
            Evidence(
                id="R2",
                kind=EvidenceKind.FEATURE,
                claim="Test addresses simulate delivered and bounced events.",
                verbatim="Use these test addresses to simulate each event type.",
                source="https://resend.com/changelog/test-addresses",
                strength=EvidenceStrength.STRONG,
            ),
        ]
    )

    recovery = existing_recovery(
        gap="The Supabase-specific SMTP destination is missing.",
        artifacts=artifacts,
    )

    assert recovery is not None
    assert [entry.id for entry in recovery.evidence] == ["R1"]
    assert recovery.sources == []
    assert recovery.recovered


def test_one_matching_word_does_not_hide_a_different_material_gap():
    artifacts = artifacts_fixture()
    artifacts.evidence.entries.append(
        Evidence(
            id="R1",
            kind=EvidenceKind.FEATURE,
            claim="The provider offers SMTP test addresses.",
            verbatim="Test addresses simulate delivery events.",
            source="https://docs.example.com/smtp/test-addresses",
            strength=EvidenceStrength.STRONG,
        )
    )

    assert existing_recovery(
        gap="Explain the SMTP pricing and monthly overage policy.",
        artifacts=artifacts,
    ) is None


def test_prerequisites_do_not_replace_a_requested_sample():
    artifacts = artifacts_fixture()
    artifacts.evidence.entries.append(
        Evidence(
            id="R1",
            kind=EvidenceKind.INTEGRATION,
            claim="A verified domain and API key are needed before webhook setup.",
            verbatim="Create an API key and verify a domain before webhook setup.",
            source="https://docs.example.com/webhooks/setup",
            strength=EvidenceStrength.STRONG,
        )
    )

    assert existing_recovery(
        gap="Show a sample webhook event before domain and API key setup.",
        artifacts=artifacts,
    ) is None
