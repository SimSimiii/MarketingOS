"""The count in a request is arithmetic, so it is parsed, not interpreted."""

import pytest

from app.marketing.contract import (
    DEFAULT_SEQUENCE_LENGTH,
    DeliverableKind,
    check_contract,
    parse_contract,
)


@pytest.mark.parametrize(
    ("request_text", "count"),
    [
        ("Write me 3 emails that make people buy my app", 3),
        ("Create a five-email onboarding campaign for my SaaS", 5),
        ("I need a 7 email sequence", 7),
        ("build a sequence of four emails", 4),
        ("Write two e-mails for the launch", 2),
        ("give me a 5 part email series", 5),
        # The number still binds when the emails are described before they are
        # named. This used to fall through to the default length, so a user
        # who asked for five onboarding emails was handed three and nothing
        # anywhere recorded that as a broken promise.
        ("Write me 3 onboarding emails for people who started a trial", 3),
        ("Write me 4 short sales emails", 4),
        ("give me three cold outreach emails", 3),
        ("I want 5 re-engagement emails", 5),
    ],
)
def test_an_explicit_count_is_read_out_of_the_request(request_text: str, count: int):
    contract = parse_contract(request_text)
    assert contract.count == count
    assert contract.count_is_explicit


@pytest.mark.parametrize(
    "request_text",
    [
        "Give me 3 ideas for an email about our pricing change",
        "Write 2 versions of an email for the launch",
        "Share 5 tips about email marketing",
        "Give me 3 reasons to send an email now",
    ],
)
def test_a_number_separated_from_the_emails_by_a_pivot_counts_something_else(
    request_text: str,
):
    """Describing words may sit between the number and the noun ("3 onboarding
    emails"), but a preposition means the number stopped counting emails
    several words ago."""
    contract = parse_contract(request_text)
    assert contract.count == 1
    assert contract.kind is DeliverableKind.SINGLE_EMAIL


def test_one_email_is_its_own_shape():
    contract = parse_contract("Write me an email announcing the new pricing")
    assert contract.count == 1
    assert contract.kind is DeliverableKind.SINGLE_EMAIL


def test_an_unspecified_count_is_a_working_assumption_not_a_promise():
    contract = parse_contract("Write an onboarding email campaign for my SaaS")
    assert contract.count == DEFAULT_SEQUENCE_LENGTH
    assert not contract.count_is_explicit
    assert "did not name a number" in contract.render()


def test_a_number_that_is_not_counting_emails_is_not_the_email_count():
    """"3 ideas for an email" is one email and three ideas - a count only
    binds when it sits next to the word it counts."""
    contract = parse_contract("Give me 3 ideas for an email about our pricing change")
    assert contract.count == 1
    assert contract.kind is DeliverableKind.SINGLE_EMAIL


def test_an_article_before_a_sequence_word_is_not_a_count_of_one():
    """"an email campaign" is a campaign, not one email."""
    contract = parse_contract("Write an email campaign for our launch")
    assert not contract.count_is_explicit
    assert contract.count == DEFAULT_SEQUENCE_LENGTH


def test_a_digit_still_counts_even_before_a_sequence_word():
    contract = parse_contract("Write a 5 email campaign for our launch")
    assert contract.count == 5
    assert contract.count_is_explicit


def test_an_absurd_count_falls_back_rather_than_running_forty_emails():
    contract = parse_contract("Write me 40 emails")
    assert not contract.count_is_explicit
    assert contract.count == DEFAULT_SEQUENCE_LENGTH


def test_delivering_the_promised_number_is_a_clean_contract():
    assert check_contract(parse_contract("Write me 3 emails"), delivered=3) == []


def test_delivering_fewer_than_promised_is_a_violation():
    violations = check_contract(parse_contract("Write me 3 emails"), delivered=2)
    assert len(violations) == 1
    assert "3 email(s) and the run produced 2" in violations[0].detail


def test_an_unstated_count_is_satisfied_by_anything_delivered():
    """The user never named a number, so the strategist's judgment stands."""
    assert check_contract(parse_contract("Write an email campaign"), delivered=4) == []
    assert check_contract(parse_contract("Write an email campaign"), delivered=0)
