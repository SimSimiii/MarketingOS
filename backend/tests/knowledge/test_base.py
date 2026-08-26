"""The knowledge base: six artifacts flattened onto one set of shelves.

Two audiences read the same index. A user browsing what we found out about
their business, and a strategist deciding what a campaign can argue from. The
tests below are mostly about the difference that matters between them: only
the evidence ledger is citable in copy, and everything else is context.
"""

from app.knowledge.artifacts import (
    AudienceModel,
    BusinessProfile,
    CallToAction,
    Fact,
    Gap,
    GapReport,
    Grounding,
    KnowledgeArtifacts,
    Objection,
    OfferSheet,
    Plan,
    Provenance,
    Segment,
    VoiceProfile,
)
from app.knowledge.base import EntryOrigin, build_knowledge_base
from app.knowledge.ledger import Evidence, EvidenceKind, EvidenceLedger, EvidenceStrength
from app.knowledge.taxonomy import FactCategory, ValueBand


def artifacts() -> KnowledgeArtifacts:
    return KnowledgeArtifacts(
        business=BusinessProfile(
            company_name="Notewright",
            what_it_does="drafts a release note from your commits",
            category="developer tooling",
            business_model="subscription",
            vocabulary=["release note", "credits"],
            facts=[
                Fact(
                    statement="Built by two former release engineers",
                    grounding=Grounding.GROUNDED,
                    provenance=Provenance(source="https://x.com/about", quote="We are two "
                                          "former release engineers."),
                )
            ],
        ),
        offer=OfferSheet(
            plans=[Plan(name="Team", price="$29/month", includes=["unlimited notes"])],
            free_entry="1,500 free credits, no card",
            guarantees=["Cancel any time"],
            calls_to_action=[CallToAction(label="Start the trial", intent="self-serve")],
            purchase_motion="self-serve",
        ),
        evidence=EvidenceLedger(
            entries=[
                Evidence(
                    id="E1",
                    kind=EvidenceKind.TESTIMONIAL,
                    claim="Foldwork cut release notes from 40 minutes to 9 seconds",
                    verbatim='"It replaced a job nobody on my team wanted," says Dana Ellis.',
                    strength=EvidenceStrength.STRONG,
                    category=FactCategory.PROOF,
                ),
                Evidence(
                    id="E2",
                    kind=EvidenceKind.FEATURE,
                    claim="Connects to GitHub and GitLab over the API",
                    verbatim="Notewright connects to GitHub and GitLab over the API.",
                ),
                Evidence(
                    id="E3",
                    kind=EvidenceKind.PRICE,
                    claim="Team is $29/month",
                    verbatim="Team is $29/month.",
                ),
            ]
        ),
        voice=VoiceProfile(
            learned=True,
            tone="plain and direct",
            exemplars=["We shipped this because we hated doing it by hand."],
        ),
        audience=AudienceModel(
            segments=[
                Segment(
                    name="Release engineer at a 30-person startup",
                    situation="ships twice a week and writes the notes on Friday afternoon",
                    job_to_be_done="stop losing Friday to changelog archaeology",
                )
            ],
            objections=[
                Objection(
                    objection="our commit messages are too messy for this",
                    answer="it reads the diff, not the message",
                    evidence_ids=["E2"],
                )
            ],
        ),
        gaps=GapReport(
            gaps=[Gap(id="G-proof", missing="No case studies", impact="cannot prove adoption")]
        ),
    )


def test_every_compiled_artifact_reaches_a_shelf():
    """The whole point: a user should not have to know which of six artifacts
    holds the fact they are looking for."""
    base = build_knowledge_base(artifacts())
    origins = {entry.origin for entry in base.entries}
    assert origins == {
        EntryOrigin.EVIDENCE,
        EntryOrigin.PROFILE,
        EntryOrigin.OFFER,
        EntryOrigin.AUDIENCE,
        EntryOrigin.VOICE,
    }


def test_only_the_evidence_ledger_is_citable_in_copy():
    """A segment description is true, useful and not licensed to appear in an
    email as a claim - the evidence gate has never heard of it."""
    base = build_knowledge_base(artifacts())
    citable = {entry.id for entry in base.entries if entry.citable}
    assert citable == {"E1", "E2", "E3"}
    assert base.citable_total == 3


def test_facts_are_shelved_by_the_question_they_answer():
    base = build_knowledge_base(artifacts())
    shelved = {entry.id: entry.category for entry in base.entries}
    assert shelved["E1"] is FactCategory.PROOF
    assert shelved["E2"] is FactCategory.TECHNICAL
    assert shelved["E3"] is FactCategory.COMMERCIAL
    assert shelved["O-plan1"] is FactCategory.COMMERCIAL
    assert shelved["A-segment1"] is FactCategory.MARKET
    assert shelved["V-exemplar1"] is FactCategory.BRAND


def test_the_base_is_ordered_by_what_a_fact_is_worth():
    base = build_knowledge_base(artifacts())
    values = [entry.value for entry in base.entries]
    assert values == sorted(values, reverse=True)
    assert base.entries[0].band is ValueBand.HEADLINE


def test_a_shelf_carries_what_its_being_empty_costs():
    """The empty shelf is the most useful thing on the page: it is a sentence
    telling the user which page to upload next."""
    base = build_knowledge_base(KnowledgeArtifacts())
    assert all(shelf.when_empty for shelf in base.shelves)
    # Everything a campaign argues from is empty. Brand is not: a bundle
    # compiled from nothing still describes the voice the system falls back to.
    assert {shelf.category for shelf in base.empty_shelves} == set(FactCategory) - {
        FactCategory.BRAND
    }


def test_a_bundle_compiled_from_nothing_does_not_claim_to_know_three_things():
    """The house-default voice is a real artifact and not a fact about this
    business. Counting it would report knowledge nobody supplied."""
    assert build_knowledge_base(KnowledgeArtifacts()).has_material is False
    assert build_knowledge_base(artifacts()).has_material is True


def test_an_empty_shelf_is_named_in_the_map_the_strategist_reads():
    thin = KnowledgeArtifacts(
        business=BusinessProfile(company_name="Notewright", what_it_does="drafts release notes")
    )
    rendered = build_knowledge_base(thin).render_map()
    assert "Trust & compliance" in rendered
    assert "nothing here" in rendered


def test_the_map_counts_what_can_be_cited_and_what_can_lead():
    rendered = build_knowledge_base(artifacts()).render_map()
    assert "citable in copy" in rendered
    assert "strong enough to lead an email" in rendered


def test_nothing_compiled_says_so_rather_than_rendering_an_empty_map():
    assert "Nothing has been compiled" in build_knowledge_base(KnowledgeArtifacts()).render_map()


def test_search_matches_on_words_not_substrings():
    base = build_knowledge_base(artifacts())
    hits = base.search("github integration")
    assert hits
    assert hits[0].id == "E2"


def test_search_narrows_by_shelf():
    base = build_knowledge_base(artifacts())
    commercial = base.search(category=FactCategory.COMMERCIAL)
    assert {entry.id for entry in commercial} >= {"E3", "O-plan1", "O-free"}
    assert all(entry.category is FactCategory.COMMERCIAL for entry in commercial)


def test_search_narrows_by_band():
    base = build_knowledge_base(artifacts())
    headline = base.search(band=ValueBand.HEADLINE)
    assert all(entry.band is ValueBand.HEADLINE for entry in headline)


def test_a_fact_the_compiler_wrote_down_twice_appears_once():
    """The profile pass and the evidence pass read the same pages, so a
    business's one memorable number often lands in both."""
    doubled = artifacts()
    doubled.business.facts.append(
        Fact(statement="Team is $29/month", grounding=Grounding.GROUNDED)
    )
    base = build_knowledge_base(doubled)
    matching = [entry for entry in base.entries if entry.statement == "Team is $29/month"]
    assert len(matching) == 1
    # Evidence wins the collision, because it is the copy a writer may cite.
    assert matching[0].citable


def test_unanswered_gaps_travel_with_the_base():
    base = build_knowledge_base(artifacts())
    assert any("No case studies" in question for question in base.open_questions)


def test_every_entry_explains_its_own_score():
    base = build_knowledge_base(artifacts())
    assert all(entry.why for entry in base.entries)
