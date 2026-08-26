"""Where a fact gets filed, and what it is worth.

Both answers are computed in code, which is the point of the module: they run
over artifact sets compiled months ago, on every page load, for free, and two
identical facts score identically forever.
"""

import pytest

from app.knowledge.ledger import Evidence, EvidenceKind, EvidenceStrength, category_of, value_of
from app.knowledge.taxonomy import (
    CATEGORY_ORDER,
    SHELVES,
    FactCategory,
    ValueBand,
    assess_value,
    classify,
)


def test_every_category_has_a_shelf():
    """A category with no shelf renders as a blank section with no heading and
    no explanation of what belongs in it."""
    assert set(SHELVES) == set(FactCategory)
    assert set(CATEGORY_ORDER) == set(FactCategory)


@pytest.mark.parametrize(
    ("kind", "text", "expected"),
    [
        ("price", "Team is $29/month", FactCategory.COMMERCIAL),
        ("testimonial", "It replaced a job nobody wanted", FactCategory.PROOF),
        ("customer", "Foldwork uses it daily", FactCategory.PROOF),
        ("certification", "SOC 2 Type II", FactCategory.TRUST),
        ("award", "Product of the year", FactCategory.TRUST),
    ],
)
def test_an_unambiguous_kind_settles_the_shelf(kind: str, text: str, expected: FactCategory):
    """A price is a commercial fact wherever the words around it point. Letting
    a lexicon overrule these costs accuracy on the entries that matter most."""
    assert classify(text, kind) is expected


def test_a_price_stays_commercial_even_when_the_words_are_technical():
    assert (
        classify("The API tier is $99/month for 1M webhook deliveries", "price")
        is FactCategory.COMMERCIAL
    )


def test_the_catch_all_kind_is_decided_by_what_the_fact_says():
    """Two thirds of a real ledger arrives labelled `feature`. Filing all of it
    under "product" would tell the user nothing they did not already know."""
    assert (
        classify("SOC 2 Type II certified, audited annually, and we never train on your data",
                 "feature")
        is FactCategory.TRUST
    )
    assert (
        classify("Connects to Slack, GitHub and Salesforce over a REST API", "feature")
        is FactCategory.TECHNICAL
    )
    assert (
        classify("Migration takes an afternoon and support answers within an hour", "feature")
        is FactCategory.OPERATIONS
    )
    assert classify("A drag-and-drop editor with reusable templates", "feature") is (
        FactCategory.PRODUCT
    )


def test_a_performance_metric_is_technical_not_proof():
    """`metric` leans towards proof, and leans lightly enough that two technical
    terms win. "99.99% uptime, sub-50ms latency" is not social proof."""
    assert (
        classify("99.99% uptime with sub-50ms API latency", "metric") is FactCategory.TECHNICAL
    )


def test_a_customer_result_stays_proof():
    assert classify("Cut review time by 40% for their support team", "metric") is (
        FactCategory.PROOF
    )


def test_a_fact_with_no_kind_and_no_keywords_lands_somewhere_sensible():
    assert classify("It does the thing") is FactCategory.PRODUCT


def test_a_bare_number_with_nothing_around_it_is_not_proof():
    """A `metric` whose text gives no signal must not reach the proof shelf by
    walkover. "Default temperature setting is 0.7" is a config default, and a
    user opens that shelf to find out whether anybody uses this."""
    assert classify("Default temperature setting is 0.7", "metric") is FactCategory.PRODUCT
    assert classify("Default max tokens is 1024", "metric") is FactCategory.TECHNICAL


def test_plan_quotas_are_commercial_facts_not_proof():
    """Most of a real ledger's `metric` entries are plan limits. Filed as proof
    they crowd out the entries that answer "has this worked for anyone"."""
    assert classify("Pro plan includes 30-day analytics history", "metric") is (
        FactCategory.COMMERCIAL
    )
    assert classify("Free tier allows 100 executions per month", "metric") is (
        FactCategory.COMMERCIAL
    )


def test_the_word_customer_alone_is_not_proof():
    """"customer data" and "customer support" are not somebody vouching. A
    proof shelf that fills up with them stops answering its own question."""
    assert (
        classify("Customer data is encrypted end-to-end and never used to train a model")
        is not FactCategory.PROOF
    )
    assert classify("Trusted by teams at Foldwork and Basecamp") is FactCategory.PROOF


# ------------------------------------------------------------------- scoring


def score(statement: str, **kwargs) -> int:
    kwargs.setdefault("category", classify(statement))
    kwargs.setdefault("verbatim", statement)
    return assess_value(statement=statement, **kwargs).score


def test_a_named_attributed_outcome_beats_an_adjective():
    attributed = score(
        "Foldwork cut their release notes from 40 minutes to 9 seconds",
        category=FactCategory.PROOF,
        strength="strong",
    )
    vague = score(
        "A powerful, intuitive dashboard that streamlines your workflow",
        category=FactCategory.PRODUCT,
        strength="weak",
    )
    assert attributed > vague
    assert attributed >= 70
    assert vague < 42


def test_adjectives_with_nothing_checkable_behind_them_are_penalised():
    with_number = score("Seamless setup in 4 minutes", category=FactCategory.OPERATIONS)
    without = score("Seamless, effortless setup", category=FactCategory.OPERATIONS)
    assert with_number > without


def test_a_fact_with_no_quote_behind_it_scores_lower_than_the_same_fact_with_one():
    quoted = score("Team is $29/month", category=FactCategory.COMMERCIAL, verbatim="Team is $29 a month, billed monthly, cancel any time.")
    bare = score("Team is $29/month", category=FactCategory.COMMERCIAL, verbatim="")
    assert quoted > bare


def test_the_score_is_explained_in_sentences():
    """A ranking nobody can interrogate is a ranking nobody believes."""
    value = assess_value(
        category=FactCategory.PROOF,
        statement="Foldwork cut review time by 40%",
        verbatim="Foldwork cut review time by 40% in their first month.",
        strength="strong",
    )
    assert value.reasons
    assert all(isinstance(reason, str) and reason for reason in value.reasons)
    assert len(value.reasons) <= 4


def test_bands_follow_the_score():
    assert assess_value(category=FactCategory.COMPANY, statement="Founded in 2019").band is (
        ValueBand.BACKGROUND
    )
    assert (
        assess_value(
            category=FactCategory.PROOF,
            statement="Foldwork cut review time by 40%",
            verbatim="Foldwork cut review time by 40% in their first month of using it.",
            strength="strong",
        ).band
        is ValueBand.HEADLINE
    )


def test_the_score_stays_inside_its_range():
    absurd = assess_value(
        category=FactCategory.PROOF,
        statement="Foldwork, Basecamp and Linear cut 40% and 3x and $29,000 in 12 minutes",
        verbatim="x" * 500,
        strength="strong",
        user_attested=True,
    )
    assert 0 <= absurd.score <= 100


# ------------------------------------------------------- reading the ledger


def test_an_entry_compiled_before_the_taxonomy_existed_is_still_shelved():
    """Old artifact payloads have no `category`. Deriving it at read time is
    what lets this ship without a migration or a paid recompile."""
    legacy = Evidence(
        id="E1",
        kind=EvidenceKind.FEATURE,
        claim="ISO 27001 certified since 2022",
        verbatim="We have been ISO 27001 certified since 2022.",
    )
    assert legacy.category is None
    assert category_of(legacy) is FactCategory.TRUST


def test_a_stored_category_wins_over_the_lexicon():
    """The compiler saw the whole page; the classifier sees one sentence."""
    entry = Evidence(
        id="E1",
        kind=EvidenceKind.FEATURE,
        claim="Nothing you upload is used to train a model",
        verbatim="Nothing you upload is used to train a model.",
        category=FactCategory.TRUST,
    )
    assert category_of(entry) is FactCategory.TRUST


def test_value_of_reads_everything_off_the_entry():
    entry = Evidence(
        id="E1",
        kind=EvidenceKind.TESTIMONIAL,
        claim="Foldwork cut review time by 40%",
        verbatim="\"It cut our review time by 40%,\" says Dana Ellis at Foldwork.",
        strength=EvidenceStrength.STRONG,
    )
    assert value_of(entry).band is ValueBand.HEADLINE
