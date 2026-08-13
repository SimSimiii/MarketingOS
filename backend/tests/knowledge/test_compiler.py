"""The compiler, and the check that keeps its output trustworthy.

A compiler that hallucinates a testimonial poisons every campaign written
afterwards, invisibly, because nothing further down ever sees the original
page. So the quotes are verified in code before an entry is kept.
"""

import json

import pytest

from app.knowledge.artifacts import (
    CallToAction,
    KnowledgeArtifacts,
    OfferSheet,
    Plan,
    VoiceProfile,
)
from app.knowledge.compiler import KnowledgeCompiler, find_gaps
from app.knowledge.corpus import Document, SourceCorpus
from app.knowledge.ledger import Evidence, EvidenceKind, EvidenceLedger
from tests.marketing.conftest import RoleScriptedProvider, make_session

PAGE = """# Notewright

Notewright drafts a release note in about nine seconds.

Team is $29/month. Every account starts with 1,500 free credits.

"It replaced a job nobody on my team wanted," says Dana Ellis at Foldwork.
"""


def corpus() -> SourceCorpus:
    return SourceCorpus.from_documents(
        [Document(id="d1", title="Home", content=PAGE, source="https://x.com")]
    )


def profile_answer() -> str:
    return json.dumps(
        {
            "business": {
                "company_name": "Notewright",
                "what_it_does": "drafts release notes from your commits",
                "category": "developer tooling",
                "vocabulary": ["release note", "credits"],
            },
            "offer": {
                "plans": [{"name": "Team", "price": "$29/month"}],
                "free_entry": "1,500 free credits",
                "calls_to_action": [{"label": "Start the trial", "intent": "self-serve"}],
                "purchase_motion": "self-serve",
            },
        }
    )


def evidence_answer(*entries: dict) -> str:
    return json.dumps({"entries": list(entries)})


def voice_answer(*exemplars: str) -> str:
    return json.dumps(
        {"voice": {"tone": "plain and technical", "exemplars": list(exemplars)}}
    )


AUDIENCE_ANSWER = json.dumps(
    {
        "audience": {
            "segments": [{"name": "a developer who ships weekly", "situation": "ships Fridays"}],
            "objections": [
                {"objection": "we have a script", "evidence_ids": ["E1", "E404"]}
            ],
        }
    }
)


def compiler_provider(*, evidence: str, voice: str) -> RoleScriptedProvider:
    provider = RoleScriptedProvider()
    provider.push("knowledge_compiler", profile_answer(), evidence, voice, AUDIENCE_ANSWER)
    return provider


@pytest.mark.asyncio
async def test_evidence_whose_quote_is_real_is_kept():
    provider = compiler_provider(
        evidence=evidence_answer(
            {
                "kind": "metric",
                "claim": "drafts a release note in about nine seconds",
                "verbatim": "Notewright drafts a release note in about nine seconds.",
                "document_id": "d1",
                "strength": "strong",
            }
        ),
        voice=voice_answer("Notewright drafts a release note in about nine seconds."),
    )
    artifacts = await KnowledgeCompiler(make_session(provider)).compile(corpus())

    assert [entry.claim for entry in artifacts.evidence.entries] == [
        "drafts a release note in about nine seconds"
    ]
    assert artifacts.evidence.entries[0].id == "E1"
    assert artifacts.evidence.entries[0].document_id == "d1"


@pytest.mark.asyncio
async def test_evidence_whose_quote_is_invented_is_dropped():
    provider = compiler_provider(
        evidence=evidence_answer(
            {
                "kind": "testimonial",
                "claim": "customers save ten hours a week",
                "verbatim": "Our customers save ten hours every single week, guaranteed.",
                "document_id": "d1",
                "strength": "strong",
            }
        ),
        voice=voice_answer(),
    )
    artifacts = await KnowledgeCompiler(make_session(provider)).compile(corpus())
    assert artifacts.evidence.entries == []


@pytest.mark.asyncio
async def test_reflowed_whitespace_does_not_make_a_real_quote_unverifiable():
    """Loaders reflow text, so an exact match would be too strict."""
    provider = compiler_provider(
        evidence=evidence_answer(
            {
                "kind": "price",
                "claim": "$29/month",
                "verbatim": "Team is  $29/month.\n Every account starts with 1,500 free credits.",
                "document_id": "d1",
                "strength": "strong",
            }
        ),
        voice=voice_answer(),
    )
    artifacts = await KnowledgeCompiler(make_session(provider)).compile(corpus())
    assert len(artifacts.evidence.entries) == 1


@pytest.mark.asyncio
async def test_a_voice_with_no_verifiable_exemplar_is_reported_as_the_house_default():
    """Inventing a house style and presenting it as theirs would be repeated
    in every email they send."""
    provider = compiler_provider(
        evidence=evidence_answer(),
        voice=voice_answer("We are passionate about empowering modern engineering teams."),
    )
    artifacts = await KnowledgeCompiler(make_session(provider)).compile(corpus())

    assert not artifacts.voice.learned
    assert artifacts.voice.exemplars == []
    assert any(gap.id == "G-voice" for gap in artifacts.gaps.gaps)


@pytest.mark.asyncio
async def test_an_objection_pointing_at_missing_evidence_loses_the_dead_id():
    provider = compiler_provider(
        evidence=evidence_answer(
            {
                "kind": "metric",
                "claim": "nine seconds",
                "verbatim": "Notewright drafts a release note in about nine seconds.",
                "document_id": "d1",
                "strength": "strong",
            }
        ),
        voice=voice_answer(),
    )
    artifacts = await KnowledgeCompiler(make_session(provider)).compile(corpus())
    assert artifacts.audience.objections[0].evidence_ids == ["E1"]


@pytest.mark.asyncio
async def test_no_material_costs_nothing_and_says_so():
    """A user who gave only a product description gets an honest empty
    profile, not an invented business."""
    provider = RoleScriptedProvider()
    artifacts = await KnowledgeCompiler(make_session(provider)).compile(SourceCorpus())

    assert provider.requests == []
    assert artifacts.gaps.blocking
    assert artifacts.is_empty


# --------------------------------------------------------------------- gaps


def test_a_gap_is_only_reported_when_it_changes_the_copy():
    artifacts = KnowledgeArtifacts(
        offer=OfferSheet(
            plans=[Plan(name="Team", price="$29")],
            calls_to_action=[CallToAction(label="Start the trial")],
        ),
        evidence=EvidenceLedger(
            entries=[
                Evidence(id="E1", kind=EvidenceKind.METRIC, claim="x", verbatim="x"),
                Evidence(id="E2", kind=EvidenceKind.TESTIMONIAL, claim="y", verbatim="y"),
            ]
        ),
        voice=VoiceProfile(learned=True),
    )
    artifacts.audience.segments.append(
        __import__("app.knowledge.artifacts", fromlist=["Segment"]).Segment(name="someone")
    )

    assert find_gaps(artifacts).gaps == []


def test_no_price_anywhere_is_a_gap_because_it_decides_what_an_email_can_say():
    report = find_gaps(KnowledgeArtifacts())
    assert {gap.id for gap in report.gaps} >= {"G-price", "G-cta", "G-proof", "G-audience"}
    assert any(gap.severity == "blocking" for gap in report.gaps)
