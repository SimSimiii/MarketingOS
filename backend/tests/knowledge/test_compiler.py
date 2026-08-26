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
from tests.marketing.conftest import FAIL, RoleScriptedProvider, make_session

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
    """Answers keyed by template, not by call position.

    All four passes are the same role, so a positional script only worked
    while they ran strictly one after another. They do not: the three that
    read only the material are issued concurrently, and a positional script
    then hands the voice pass whatever the audience pass was owed. Keying by
    template is what `RoleScriptedProvider` was built for - see its
    `_keys` - and it says what each answer is *for* rather than when it lands.
    """
    provider = RoleScriptedProvider()
    provider.push("knowledge_profile", profile_answer())
    provider.push("knowledge_evidence", evidence)
    provider.push("knowledge_voice", voice)
    provider.push("knowledge_audience", AUDIENCE_ANSWER)
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


# ------------------------------------------------------- reading everything


LONG_PAGE = (
    "# Pricing\n\n"
    + "Every plan includes the same drafting engine and the same editor.\n\n" * 260
    + "\n\nEnterprise is $4,900 per year and includes a named support engineer.\n"
)


@pytest.mark.asyncio
async def test_a_document_longer_than_one_call_is_read_in_several_not_truncated():
    """The failure this replaces cost a business its pricing page.

    A document over the per-call budget used to be sliced with
    `content[:budget]` and the remainder was never read by this pass on any
    code path. Prices, case studies and limits live at the bottom of long
    pages, which is exactly the material a campaign has nothing to say
    without.
    """
    document = Document(id="d1", title="Pricing", content=LONG_PAGE, source="https://x.com/p")
    provider = RoleScriptedProvider()
    provider.set_default("knowledge_profile", profile_answer())
    provider.set_default("knowledge_voice", voice_answer())
    provider.set_default("knowledge_audience", AUDIENCE_ANSWER)
    provider.set_default("knowledge_evidence", evidence_answer())

    await KnowledgeCompiler(make_session(provider)).compile(
        SourceCorpus.from_documents([document])
    )

    read = "".join(
        request.system_prompt or "" for request in provider.requests_for("knowledge_compiler")
        if "knowledge_evidence" in (request.template or "")
    )
    assert len(provider.requests_for("knowledge_compiler")) > 4, "one long page is several reads"
    assert "$4,900 per year" in read, "the end of the page has to reach a model"


@pytest.mark.asyncio
async def test_the_passes_that_only_read_the_material_run_together():
    """Independent questions about the same pages, asked at once.

    Asked one at a time this is the longest serial stretch in a run, and the
    Strategist cannot start until all of it is done. Nothing about the answers
    changes - only how long the user waits for them.

    Counted rather than timed: `max_concurrent_by_role` is what the double
    keeps for exactly this, because a timing assertion is how a suite acquires
    a flake.
    """
    document = Document(id="d1", title="Pricing", content=LONG_PAGE, source="https://x.com/p")
    provider = RoleScriptedProvider()
    provider.set_default("knowledge_profile", profile_answer())
    provider.set_default("knowledge_voice", voice_answer())
    provider.set_default("knowledge_audience", AUDIENCE_ANSWER)
    provider.set_default("knowledge_evidence", evidence_answer())

    await KnowledgeCompiler(make_session(provider)).compile(
        SourceCorpus.from_documents([document])
    )

    assert provider.max_concurrent_by_role["knowledge_compiler"] >= 3


@pytest.mark.asyncio
async def test_the_audience_pass_still_waits_for_what_it_is_written_from():
    """The one pass with real inputs. It reads the profile and the ledger, so
    it cannot be issued with them - and a compile that ran it early would be
    describing buyers for a product it had not finished reading about."""
    provider = compiler_provider(evidence=evidence_answer(), voice=voice_answer())
    await KnowledgeCompiler(make_session(provider)).compile(corpus())

    templates = [request.template for request in provider.requests]
    assert templates[-1] == "knowledge_audience"
    assert set(templates[:-1]) == {
        "knowledge_profile",
        "knowledge_evidence",
        "knowledge_voice",
    }


@pytest.mark.asyncio
async def test_what_the_compile_threw_away_is_recorded_rather_than_only_logged():
    """A ledger is thin either because the business has little to say or
    because a third of what was found could not be verified, and those need
    different answers from the user. Only one of them used to be visible."""
    provider = compiler_provider(
        evidence=evidence_answer(
            {
                "kind": "metric",
                "claim": "drafts a release note in about nine seconds",
                "verbatim": "Notewright drafts a release note in about nine seconds.",
                "document_id": "d1",
                "strength": "strong",
            },
            {
                "kind": "testimonial",
                "claim": "customers save ten hours a week",
                "verbatim": "Our customers save ten hours every single week, guaranteed.",
                "document_id": "d1",
                "strength": "strong",
            },
        ),
        voice=voice_answer(),
    )
    artifacts = await KnowledgeCompiler(make_session(provider)).compile(corpus())

    assert len(artifacts.evidence.entries) == 1
    assert any("discarded" in note for note in artifacts.notes)
    assert any("1 of 2" in note for note in artifacts.notes)


@pytest.mark.asyncio
async def test_one_reading_that_never_comes_back_costs_its_pages_not_the_compile():
    """A compile is what every future campaign for this business is written
    from. Finishing with a smaller ledger and saying so beats failing."""
    provider = RoleScriptedProvider()
    provider.set_default("knowledge_profile", profile_answer())
    provider.set_default("knowledge_voice", voice_answer())
    provider.set_default("knowledge_audience", AUDIENCE_ANSWER)
    # The reading refuses every attempt the session makes, not one: a single
    # dropped connection is a blip `ModelSession` absorbs, and what is being
    # tested here is the floor underneath that.
    provider.set_default("knowledge_evidence", FAIL)

    artifacts = await KnowledgeCompiler(make_session(provider)).compile(corpus())

    assert any("did not come back" in note for note in artifacts.notes)
    assert artifacts.business.company_name == "Notewright", "the rest of the compile stands"
    assert artifacts.voice.tone, "and so does the voice it did read"
    assert any(gap.id == "G-proof" for gap in artifacts.gaps.gaps), (
        "an empty ledger is reported as gaps, so the run can still refuse to spend on it"
    )
