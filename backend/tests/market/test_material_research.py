from datetime import UTC, datetime

import pytest

from app.knowledge.corpus import Document, SourceCorpus
from app.knowledge.ledger import (
    Evidence,
    EvidenceContext,
    EvidenceKind,
    EvidenceStrength,
    unconfirmed_billing,
)
from app.market.audience_research import FetchedSource, FetchResult, SourceTier
from app.market.material_research import (
    MaterialClaim,
    MaterialRecovery,
    MaterialResearcher,
    OfficialSource,
    _MaterialDraft,
    _within_identity,
    apply_recovery,
    cited_recovery,
    existing_recovery,
    verify_material,
)
from tests.marketing.conftest import RoleScriptedProvider, artifacts_fixture, make_session


def test_structured_replan_reuses_canonical_strong_allowed_facts_only():
    artifacts = artifacts_fixture()
    facts = [Evidence(
        id=f"known_{index}", kind=EvidenceKind.FEATURE,
        claim=f"Documented operation {index}", verbatim=f"Documented operation {index}.",
        source="https://docs.example.com/operations", strength=EvidenceStrength.STRONG,
    ) for index in range(8)]
    artifacts.evidence.entries.extend(facts)
    artifacts.evidence.entries.append(Evidence(
        id="weak", kind=EvidenceKind.FEATURE, claim="Unknown operation", verbatim="Unknown",
        source="https://docs.example.com/operations", strength=EvidenceStrength.WEAK,
    ))
    view = artifacts.for_claim_boundary({fact.id for fact in facts[1:]} | {"weak"})
    recovery = cited_recovery(
        gap="Use the documented output operation rather than an unrelated input feature.",
        artifacts=view,
        evidence_ids=["known_0", "unknown", "weak", "known_1", "known_1", "known_2"],
    )

    assert [entry.id for entry in recovery.evidence] == ["known_1", "known_2"]
    assert recovery.evidence[0] is facts[1]
    assert not recovery.sources
    bounded = cited_recovery(gap="A real argument gap", artifacts=artifacts,
                             evidence_ids=[fact.id for fact in facts])
    assert len(bounded.evidence) == 6


def test_identity_domains_reject_homonyms_and_suffix_spoofing():
    hosts = {"ledgerloop.example"}
    assert _within_identity("https://docs.ledgerloop.example/start", hosts)
    assert not _within_identity("https://ledgerloop.co.za/services", hosts)
    assert not _within_identity("https://ledgerloop.example.evil.com", hosts)


@pytest.mark.asyncio
async def test_reserved_fixture_domain_never_searches_for_a_real_homonym():
    artifacts = artifacts_fixture()
    for entry in artifacts.evidence.entries:
        entry.source = "https://ledgerloop.example/offer"
    provider = RoleScriptedProvider()
    recovery = await MaterialResearcher(make_session(provider)).recover(
        gap="Service packages", artifacts=artifacts, reader="Business owner", request="Introduce the service")
    assert not recovery.recovered
    assert not provider.calls_by_role


@pytest.mark.asyncio
async def test_redirect_outside_supplied_identity_is_rejected_before_synthesis():
    class Fetcher:
        async def fetch(self, sources):
            from app.market.audience_research import FetchResult
            return FetchResult(sources=[fetched_page("A similarly named firm's service promises.")])

    researcher = MaterialResearcher(make_session(RoleScriptedProvider()), Fetcher())

    async def locate(**kwargs):
        return [OfficialSource(url="https://known-company.com/services", official_for="Known company")]

    researcher.locate = locate
    recovery = await researcher.recover(gap="Service details", artifacts=artifacts_fixture(),
        reader="Owner", request="Introduce", identity_url="https://known-company.com")
    assert not recovery.recovered


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


@pytest.mark.asyncio
@pytest.mark.parametrize("follow", ["listed", "unlisted", "redirect"])
async def test_required_question_can_follow_one_captured_official_link(follow):
    page = "https://docs.example.com/integration"
    corpus = SourceCorpus.from_documents([Document(
        id="brand", title="Import files", source="https://example.com/import",
        content=f"Read the [CSV import eligibility guide]({page}) for account requirements.",
    )])
    quote = "CSV import is available in trial workspaces."
    source = fetched_page(quote)
    if follow == "redirect":
        source.final_url = "https://unrelated.example.net/integration"
    calls = []

    class Fetcher:
        async def fetch(self, sources):
            calls.extend(item.url for item in sources)
            return FetchResult(sources=[source])

    provider = RoleScriptedProvider()
    provider.push(
        "material_research_synthesis",
        _MaterialDraft(followup_url=f"{page}-unlisted" if follow == "unlisted" else page).model_dump_json(),
        _MaterialDraft(claims=[MaterialClaim(source_id="S1", claim=quote, verbatim=quote)]).model_dump_json(),
    )
    recovery = await MaterialResearcher(make_session(provider), Fetcher()).verify_required_fact(
        question="Is CSV import available in trial workspaces?", source_url="",
        artifacts=artifacts_fixture(), corpus=corpus, identity_url="https://example.com",
    )
    assert recovery.recovered is (follow == "listed")
    assert calls == ([] if follow == "unlisted" else [page])
    assert len(provider.requests) == (2 if follow == "listed" else 1)
    if recovery.recovered:
        assert recovery.evidence[0].verbatim == quote
        assert recovery.evidence[0].source == page


@pytest.mark.asyncio
async def test_recovery_locates_from_captured_brand_mechanism_before_adjacent_web_results(monkeypatch):
    url = "https://buttondown.com/features/api"
    text = "Manage subscribers and [send emails](/docs/send) from your own code."
    corpus = SourceCorpus.from_documents([
        Document(id="brand", title="API operations", source=url, content=text),
        Document(id="other", title="API", source="https://other.example/api", content=text),
    ])
    source = fetched_page(text).model_copy(update={"requested_url": url, "final_url": url})
    calls = []

    class Fetcher:
        async def fetch(self, sources):
            from app.market.audience_research import FetchResult
            assert [item.url for item in sources] == [url]
            return FetchResult(sources=[source])

    researcher = MaterialResearcher(make_session(RoleScriptedProvider()), Fetcher())

    async def locate(**kwargs):
        calls.append("locate")
        assert url in kwargs["existing_material"]
        assert "send emails" in kwargs["existing_material"]
        assert "other.example" not in kwargs["existing_material"]
        return [OfficialSource(url=url, official_for="Buttondown")]

    async def synthesise(**kwargs):
        calls.append("synthesise")
        assert kwargs["sources"] == [source]
        return _MaterialDraft(claims=[MaterialClaim(
            source_id="S1", kind=EvidenceKind.FEATURE,
            claim="Send emails from your own code", verbatim="Manage subscribers and send emails from your own code.",
        )])

    monkeypatch.setattr(researcher, "locate", locate)
    monkeypatch.setattr(researcher, "synthesise", synthesise)
    recovery = await researcher.recover(
        gap="Send emails using the API", artifacts=artifacts_fixture(), reader="Developer",
        request="Verify API operations", identity_url="https://buttondown.com/", corpus=corpus,
    )
    assert calls == ["locate", "synthesise"]
    assert recovery.recovered
    assert recovery.evidence[0].source == url


def test_recovered_facts_keep_the_reviewed_subject_and_source_scope():
    quote = "Model A loses contrast when viewed from a wide angle."
    recovered = verify_material(gap="Viewing angles", draft=_MaterialDraft(claims=[MaterialClaim(
        source_id="S1", kind=EvidenceKind.FEATURE, claim=quote, verbatim=quote,
        context=EvidenceContext(subject="Model A", source_kind="third_party", claim_scope="capability",
                                conditions="Wide viewing angle"),
    )]), fetched=[fetched_page(quote)])
    context = recovered.evidence[0].context
    assert context.subject == "Model A" and context.source_kind == "third_party"
    assert context.conditions == "Wide viewing angle" and context.verification == "quote_verified_in_material"


def test_material_recovery_accepts_visible_link_text_without_blessing_an_invented_url():
    quote = "Manage subscribers and send emails from your code."
    source = fetched_page("[Manage subscribers](/subscribers) and [send emails](/emails) from your code.")
    recovered = verify_material(gap="API sending", fetched=[source], draft=_MaterialDraft(claims=[
        MaterialClaim(source_id="S1", claim=quote, verbatim=quote),
        MaterialClaim(source_id="S1", claim="Send emails", verbatim="[send emails](https://invented.example/send)"),
    ]))
    assert [entry.verbatim for entry in recovered.evidence] == [quote]
    assert recovered.dropped_claims == 1


def test_recovered_price_cannot_guess_which_captured_billing_control_is_selected():
    quote = "Pro €20 per month"
    recovered = verify_material(gap="Plan price", fetched=[fetched_page("Pay monthlyPay yearly\n" + quote)],
        draft=_MaterialDraft(claims=[MaterialClaim(source_id="S1", kind=EvidenceKind.PRICE,
            claim=quote, verbatim=quote, context=EvidenceContext(conditions="monthly payment shown"))]))
    assert recovered.recovered
    assert unconfirmed_billing(recovered.evidence[0])
    for stated in ["Pro €25 per month, billed monthly", "Pro €20 per month, billed annually"]:
        confirmed = verify_material(gap="Plan price", fetched=[fetched_page("Pay monthlyPay yearly\n" + stated)],
            draft=_MaterialDraft(claims=[MaterialClaim(source_id="S1", kind=EvidenceKind.PRICE,
                claim=stated, verbatim=stated)]))
        assert not unconfirmed_billing(confirmed.evidence[0])


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


@pytest.mark.parametrize("reverse", [False, True])
def test_cited_pricing_row_survives_an_identical_quote_in_another_section(reverse):
    artifacts = artifacts_fixture()
    funnel = Evidence(
        id="E138", kind=EvidenceKind.PRICE,
        claim="Sales-funnel transaction fees are 0% on all four plans.",
        verbatim="Frais de transaction 0% 0% 0% 0%",
        source="https://systeme.io/fr/pricing", strength=EvidenceStrength.STRONG,
        context=EvidenceContext(subject="Sales funnels", claim_scope="offer",
                                conditions="Row in the sales-funnel section"),
    )
    bio = funnel.model_copy(update={
        "id": "E156", "claim": "Bio-link transaction fees are 0% on all four plans.",
        "context": EvidenceContext(subject="Bio links", claim_scope="offer",
                                   conditions="Row in the bio-link section"),
    })
    artifacts.evidence.entries.extend([bio, funnel] if reverse else [funnel, bio])
    before = artifacts.model_dump_json()
    recovery = cited_recovery(gap="Use funnel fees for the book checkout.",
                              artifacts=artifacts, evidence_ids=[funnel.id])

    enriched, _ = apply_recovery(artifacts, SourceCorpus(), recovery)

    assert [entry.id for entry in recovery.evidence] == ["E138"]
    assert recovery.evidence[0].context.subject == "Sales funnels"
    assert enriched.evidence.ids == artifacts.evidence.ids
    assert artifacts.model_dump_json() == before


@pytest.mark.parametrize("field,changed", [
    ("subject", "Different product"),
    ("conditions", "Only on the paid plan"),
    ("temporal_scope", "Expired offer"),
    ("limitations", "Not for production"),
    ("source_kind", "third_party"),
    ("claim_scope", "comparison"),
    ("verification", "unknown"),
])
def test_equal_quotes_with_different_scope_are_not_recovery_duplicates(field, changed):
    artifacts = artifacts_fixture()
    known = artifacts.evidence.entries[0]
    known.context = EvidenceContext(subject="Original product", source_kind="official_documentation",
                                    claim_scope="offer", verification="quote_verified_in_material")
    recovered = known.model_copy(update={
        "id": "R1", "context": known.context.model_copy(update={field: changed}),
    })
    recovery = MaterialRecovery(gap="Resolve the scoped offer", evidence=[recovered])

    enriched, _ = apply_recovery(artifacts, SourceCorpus(), recovery)

    assert [entry.id for entry in recovery.evidence] == ["R1"]
    assert enriched.evidence.get(known.id).context == known.context
    assert getattr(enriched.evidence.get("R1").context, field) == changed


def test_verification_keeps_distinct_scoped_rows_but_removes_true_duplicates():
    quote = "Transaction fees 0% 0% 0% 0%"
    funnel = MaterialClaim(source_id="S1", kind=EvidenceKind.PRICE,
        claim="Sales-funnel transaction fees are zero.", verbatim=quote,
        context=EvidenceContext(subject="Sales funnels", conditions="Sales-funnel section"))
    bio = funnel.model_copy(update={"claim": "Bio-link transaction fees are zero.",
        "context": EvidenceContext(subject="Bio links", conditions="Bio-link section")})

    recovery = verify_material(gap="Transaction fees", fetched=[fetched_page(
        f"Sales funnels: {quote}. Bio links: {quote}."
    )], draft=_MaterialDraft(claims=[funnel, bio, funnel]))

    assert [entry.id for entry in recovery.evidence] == ["R1", "R2"]
    assert [entry.context.subject for entry in recovery.evidence] == ["Sales funnels", "Bio links"]


def test_recovery_does_not_overwrite_a_retained_id_with_different_content():
    artifacts = artifacts_fixture()
    known = artifacts.evidence.entries[0]
    changed = known.model_copy(update={"claim": "Different claim", "verbatim": "Different evidence"})
    recovery = MaterialRecovery(gap="New evidence", evidence=[changed])

    enriched, _ = apply_recovery(artifacts, SourceCorpus(), recovery)

    assert enriched.evidence.get(known.id) == known
    assert recovery.evidence[0].id != known.id
    assert enriched.evidence.get(recovery.evidence[0].id).verbatim == "Different evidence"
    assert len(enriched.evidence.ids) == len(enriched.evidence.entries)


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
