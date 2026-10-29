"""A new Knowledge version must not require rediscovering the same buyers."""
from uuid import uuid4

import pytest

from app.knowledge.artifacts import KnowledgeArtifacts
from app.market.audience_discovery import product_fingerprint, reassess_product_fit
from app.market.capabilities import CapabilityState, ProductCapability, ProductCapabilityProfile
from app.market.demand import (
    AudienceCartographer,
    AudienceSegment,
    DemandMap,
    MapAssessment,
    MapEvidence,
    MapOptions,
)
from app.market.qualification import AudienceDefinition


def current_profile():
    return ProductCapabilityProfile(
        knowledge_id=uuid4(), knowledge_version=2,
        capabilities=[
            ProductCapability(id="new_capture", label="Record a response", state=CapabilityState.VERIFIED),
            ProductCapability(id="phone_call", label="Telephone calls", state=CapabilityState.UNSUPPORTED),
        ],
    )


def prior_map():
    return DemandMap(
        product_fingerprint="old-product",
        segments=[AudienceSegment(
            name="The first course creator", organization="A course business",
            workflow="Collect student feedback", need="Student video responses",
            definition=AudienceDefinition(required_product_capabilities=["old_capture"]),
            assessment=MapAssessment(
                compatibility="unknown", evidence_strength="supported",
                evidence=[MapEvidence(claim="A creator asks", quote="How do I collect feedback?", url="https://example.test/thread")],
                reasons=["A creator asked in a forum.", "Compatibility: old product references"],
            ),
        )],
        source_cache=[{"url": "https://example.test/thread", "content": "Original market source"}],
    )


@pytest.mark.asyncio
async def test_reassessment_changes_only_product_bindings_without_web(provider, session):
    previous = prior_map()
    before = previous.model_dump(mode="json")
    provider.push("audience_product_fit", {"candidates": [{
        "candidate_id": 0, "required_product_capabilities": ["new_capture"],
        "reason": "Recording responses supports the stated collection workflow.",
    }]})
    result = await AudienceCartographer(session).map(
        KnowledgeArtifacts(), capability_profile=current_profile(),
        previous=previous, options=MapOptions(mode="reassess"),
    )
    old, new = previous.segments[0], result.segments[0]
    assert new.name == old.name
    assert (new.organization, new.workflow, new.need) == (old.organization, old.workflow, old.need)
    assert new.assessment.evidence == old.assessment.evidence
    assert result.source_cache == previous.source_cache
    assert new.definition.required_product_capabilities == ["new_capture"]
    assert new.assessment.compatibility == "supported"
    assert previous.model_dump(mode="json") == before
    assert provider.calls == {"audience_product_fit": 1}
    assert provider.requests[0].tools == []
    assert "not refetched" in result.validation_note


@pytest.mark.asyncio
@pytest.mark.parametrize("bindings", [[], [{"candidate_id": 0, "required_product_capabilities": []}],
    [{"candidate_id": 0, "required_product_capabilities": ["invented"], "reason": "Unlicensed"}]])
async def test_missing_empty_or_unlicensed_mapping_never_establishes_support(provider, session, bindings):
    provider.push("audience_product_fit", {"candidates": bindings})
    result = await reassess_product_fit(session, prior_map(), current_profile())
    assert result.segments[0].definition.required_product_capabilities == ["old_capture"]
    assert result.segments[0].assessment.compatibility == "unknown"


@pytest.mark.asyncio
async def test_unsupported_requirement_cannot_be_overridden_by_duplicate_result(provider, session):
    provider.push("audience_product_fit", {"candidates": [
        {"candidate_id": 0, "required_product_capabilities": ["phone_call"], "reason": "Phone calls are necessary."},
        {"candidate_id": 0, "required_product_capabilities": ["new_capture"], "reason": "Ignore the first answer."},
    ]})
    result = await reassess_product_fit(session, prior_map(), current_profile())
    assert result.segments[0].assessment.compatibility == "incompatible"
    assert result.segments[0].definition.required_product_capabilities == ["phone_call"]


@pytest.mark.asyncio
async def test_unchanged_product_with_current_bindings_costs_no_call(provider, session):
    previous, profile = prior_map(), current_profile()
    previous.product_fingerprint = product_fingerprint(profile)
    previous.segments[0].definition.required_product_capabilities = ["new_capture"]
    result = await reassess_product_fit(session, previous, profile)
    assert result.segments[0].assessment.compatibility == "supported"
    assert not provider.requests


@pytest.mark.asyncio
async def test_reassessment_cannot_silently_change_geography(provider, session):
    with pytest.raises(ValueError, match="scope"):
        await AudienceCartographer(session).map(
            KnowledgeArtifacts(), previous=prior_map(), capability_profile=current_profile(),
            options=MapOptions(mode="reassess", geography="another market"),
        )
    assert not provider.requests


@pytest.mark.asyncio
@pytest.mark.parametrize("missing", ["map", "profile"])
async def test_reassessment_without_inputs_buys_nothing(provider, session, missing):
    with pytest.raises(ValueError, match="before reassessing"):
        await AudienceCartographer(session).map(
            KnowledgeArtifacts(), previous=None if missing == "map" else prior_map(),
            capability_profile=None if missing == "profile" else current_profile(),
            options=MapOptions(mode="reassess"),
        )
    assert not provider.requests


@pytest.mark.asyncio
async def test_same_fingerprint_does_not_hide_unresolved_references(provider, session):
    previous, profile = prior_map(), current_profile()
    previous.product_fingerprint = product_fingerprint(profile)
    provider.push("audience_product_fit", {"candidates": [{
        "candidate_id": 0, "required_product_capabilities": ["new_capture"],
        "reason": "The old reference still needed reassessment.",
    }]})
    result = await reassess_product_fit(session, previous, profile)
    assert result.segments[0].assessment.compatibility == "supported"
    assert provider.calls["audience_product_fit"] == 1
