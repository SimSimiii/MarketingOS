"""The role catalog is presentation metadata for ids that live elsewhere.

Nothing at runtime forces the two to agree - `ModelRouter` looks up whatever
string it is handed - so the drift these tests catch is silent by nature: a
role renamed in its own module keeps working, and only its row in the picker
stops doing anything.
"""

import pytest

from app.ai.base import ResearchTool
from app.ai.models import MODEL_CATALOG, ModelVendor, tools_for, vendor_of
from app.ai.roles import (
    ROLE_CATALOG,
    WILDCARD_ROLE,
    InvalidOverrideError,
    validate_overrides,
)


def _implemented_role_ids() -> set[str]:
    """Every role id the system actually calls a model with.

    Imported here rather than at module scope: these modules import `app.ai`,
    so the catalog cannot import them back without closing a cycle. A test is
    allowed to reach in the direction production code is not.
    """
    from app.knowledge import compiler
    from app.market import demand, proof, rivals
    from app.marketing import (
        critic,
        reader,
        sequence,
        strategist,
        subject_lines,
        tournament,
        writer,
    )

    return {
        compiler.ROLE_ID,
        proof.ROLE_ID,
        rivals.SCOUT_ROLE_ID,
        rivals.PROFILER_ROLE_ID,
        demand.CARTOGRAPHER_ROLE_ID,
        demand.PROSPECTOR_ROLE_ID,
        demand.READER_ROLE_ID,
        critic.ROLE_ID,
        reader.ROLE_ID,
        sequence.ROLE_ID,
        strategist.ROLE_ID,
        subject_lines.WRITER_ROLE_ID,
        subject_lines.SCANNER_ROLE_ID,
        tournament.ROLE_ID,
        writer.ROLE_ID,
    }


def test_the_catalog_lists_exactly_the_roles_that_exist():
    assert set(ROLE_CATALOG) == _implemented_role_ids()


def test_every_model_the_catalog_offers_agrees_with_its_provider():
    """The catalog's `tools` field is a mirror, and mirrors go stale.

    At runtime the provider is authoritative (`available_tools`); the catalog
    copy exists so the picker can grey out a model without opening a
    subprocess to ask. If they disagree, the UI offers a choice the session
    then refuses - which reads as a bug in the run, not in the dropdown.
    """
    for model, spec in MODEL_CATALOG.items():
        assert spec.tools == tools_for(model), model
        assert vendor_of(model) is spec.vendor, model


def test_a_gpt_model_cannot_be_pinned_to_a_role_that_reads_the_web():
    with pytest.raises(InvalidOverrideError, match="web_fetch"):
        validate_overrides({"rival_scout": "gpt-5.6-sol"})


def test_a_claude_model_can_run_any_role():
    web_roles = [role for role, spec in ROLE_CATALOG.items() if spec.tools]
    assert web_roles, "the point of this test is the roles that use the web"
    assert validate_overrides({role: "opus" for role in web_roles})


def test_an_unknown_role_is_refused_rather_than_ignored():
    with pytest.raises(InvalidOverrideError, match="not an agent"):
        validate_overrides({"emial_writer": "opus"})


def test_an_unknown_model_slug_is_allowed_through():
    """The vendors ship faster than this repository does. A slug nobody here
    has heard of is routed by prefix and fails at the vendor if it is wrong,
    which beats being unable to try a model released this morning."""
    assert validate_overrides({"email_writer": "gpt-6-something"}) == {
        "email_writer": "gpt-6-something"
    }


def test_an_unknown_gpt_slug_still_cannot_take_a_web_role():
    """Unknown does not mean unconstrained: the prefix says OpenAI, and no
    OpenAI model has a fetch tool."""
    with pytest.raises(InvalidOverrideError):
        validate_overrides({"proof_hunter": "gpt-6-something"})


def test_the_wildcard_is_accepted_for_any_model():
    """Campaign runs never reach the web-reading roles - market intelligence
    routes itself - so a blanket 'run everything on GPT' is legitimate."""
    assert validate_overrides({WILDCARD_ROLE: "gpt-5.6-sol"}) == {
        WILDCARD_ROLE: "gpt-5.6-sol"
    }


def test_a_blank_choice_clears_the_pin_instead_of_storing_it():
    assert validate_overrides({"email_writer": "  ", "strategist": "opus"}) == {
        "strategist": "opus"
    }


def test_the_catalog_offers_both_vendors():
    """The whole point of the picker: a run can mix them."""
    vendors = {spec.vendor for spec in MODEL_CATALOG.values()}
    assert vendors == {ModelVendor.ANTHROPIC, ModelVendor.OPENAI}


def test_only_claude_offers_the_fetch_tool_today():
    """Not a preference - Codex has live search and no fetch-one-URL tool.
    Written down so that if OpenAI ships one, this test is what says the
    catalog may now open that door."""
    fetchers = {
        spec.vendor for spec in MODEL_CATALOG.values() if ResearchTool.WEB_FETCH in spec.tools
    }
    assert fetchers == {ModelVendor.ANTHROPIC}
