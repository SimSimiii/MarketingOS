"""Opt-in job routing preserves capabilities and does not mutate global defaults."""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.ai.model_router import ModelRouter, ModelTier
from app.ai.roles import InvalidOverrideError
from app.schemas.market import (
    MapAudienceRequest,
    RelevanceDossierRequest,
    ResearchAudienceRequest,
    ScanRequest,
)
from app.services.knowledge_compilation import CompilationRequest
from app.services.market_service import _session_for
from tests.runtime.conftest import FakeAIProvider


@pytest.mark.parametrize("schema", [
    ResearchAudienceRequest, RelevanceDossierRequest, ScanRequest,
    MapAudienceRequest, CompilationRequest,
])
def test_research_and_closed_world_dossier_accept_explicit_gpt_without_changing_defaults(schema):
    assert schema(segment="Creators", model=" gpt-5.6-sol ").model == "gpt-5.6-sol"
    assert schema(segment="Creators").model is None
    assert schema(segment="Creators", model="").model is None
    with pytest.raises(ValidationError, match="not a tier"):
        schema(segment="Creators", model="deep")


def test_credit_billing_cannot_select_a_more_expensive_job_model(monkeypatch):
    monkeypatch.setattr("app.schemas.market.get_settings", lambda: SimpleNamespace(credit_billing_enabled=True))
    with pytest.raises(ValidationError, match="credit billing"):
        ResearchAudienceRequest(segment="Creators", model="opus")


@pytest.mark.parametrize("schema,module", [
    (ScanRequest, "app.schemas.market"),
    (MapAudienceRequest, "app.schemas.market"),
    (CompilationRequest, "app.services.knowledge_compilation"),
])
def test_new_job_model_choices_preserve_credit_billing_guard(monkeypatch, schema, module):
    monkeypatch.setattr(module + ".get_settings", lambda: SimpleNamespace(credit_billing_enabled=True))
    with pytest.raises(ValidationError, match="credit billing"):
        schema(model="gpt-5.6-sol")


@pytest.mark.asyncio
async def test_only_the_requested_role_in_this_session_uses_the_selected_model():
    provider = FakeAIProvider()
    session = _session_for(provider, uuid4(), overrides={"audience_researcher": "gpt-5.6-sol"})
    await session.text(role="audience_researcher", tier=ModelTier.BALANCED,
                       system_prompt="Extract source URLs", task="Find sources")
    await session.text(role="strategist", tier=ModelTier.DEEP,
                       system_prompt="Plan", task="Plan")
    assert provider.calls[0].model == "gpt-5.6-sol"
    assert provider.calls[1].model == ModelRouter().resolve("strategist", ModelTier.DEEP)
    assert ModelRouter().resolve("audience_researcher", ModelTier.BALANCED) != "gpt-5.6-sol"


def test_fetch_dependent_roles_still_refuse_gpt_models():
    with pytest.raises(InvalidOverrideError, match="web_fetch"):
        _session_for(FakeAIProvider(), uuid4(), overrides={"proof_hunter": "gpt-5.6-sol"})
