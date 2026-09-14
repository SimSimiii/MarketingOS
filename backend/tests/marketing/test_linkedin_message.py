"""What stands between a LinkedIn draft and the message box.

This channel has no cold reader, so there is no model in it whose job is to
say "nobody would answer that". Everything that catches a bad message is
either in the prompt or in this file's subject: the free checks that run after
the draft comes back.

They split two ways on purpose. A draft with an unlicensed number cannot ship
and must fail the run if the rewrite does not fix it. A draft that opens "no
pitch, genuinely asking" can ship - it is only bad - so it buys the second
turn the forecast already allows and never costs the user a failed run.
"""

import json

import pytest

from app.marketing.linkedin import write_message
from app.runtime.exceptions import OutputValidationError
from app.schemas.linkedin import MessageRequest
from tests.marketing.conftest import RoleScriptedProvider, make_session

ROLE = "linkedin_writer"


def draft(body: str) -> str:
    return json.dumps({"body": body})


def message_request(**overrides) -> MessageRequest:
    return MessageRequest(**{
        "recipient_name": "Alice",
        "recipient_url": "https://linkedin.com/in/alice",
        "confirmed_context": "She runs release notes by hand for a team of nine.",
        "objective": "Open a conversation about how they write release notes",
        "language": "English",
        **overrides,
    })


#: Would pass every check: it uses what the user confirmed, names nothing it
#: cannot, and is the length a message actually gets read at.
GOOD = "Hi Alice - nine people shipping and the release note still written by hand. Notewright turns merged commits into that note. How long does yours take on a Friday?"


async def write(provider: RoleScriptedProvider, artifacts, **overrides) -> dict:
    return await write_message(make_session(provider), message_request(**overrides), artifacts)


@pytest.mark.asyncio
async def test_a_clean_draft_ships_on_the_first_turn(provider, artifacts):
    provider.push(ROLE, draft(GOOD))
    result = await write(provider, artifacts)

    assert result["body"] == GOOD
    assert provider.calls_by_role[ROLE] == 1
    assert result["limit"] == 700


@pytest.mark.asyncio
async def test_a_draft_that_ignores_the_confirmed_context_is_rewritten(provider, artifacts):
    """The failure this channel actually has.

    Nothing here is false, and every free check that existed before passed it:
    no unlicensed number, no placeholder, inside the limit. It is just a
    description of the product with a name pasted on the front, and it would
    read exactly the same sent to anybody else.
    """
    generic = ("Hi Alice, I build Notewright, a developer tool. A merged commit gives you a "
               "diff and nothing else, so somebody writes the note afterwards.")
    provider.push(ROLE, draft(generic), draft(GOOD))

    result = await write(provider, artifacts)

    assert result["body"] == GOOD
    assert provider.calls_by_role[ROLE] == 2
    correction = provider.requests_for(ROLE)[1].messages[-1].content
    assert "uses nothing the user confirmed about Alice" in correction


@pytest.mark.asyncio
async def test_nothing_confirmed_means_nothing_to_check(provider, artifacts):
    """A message to somebody the user knows nothing about cannot be held to
    using what they know. The prompt asks for a shorter, plainer note; there
    is no text to compare it against here."""
    provider.push(ROLE, draft("Hi Alice - Notewright turns merged commits into a release note. "
                              "Is that written by hand where you are?"))
    result = await write(provider, artifacts, confirmed_context="")

    assert provider.calls_by_role[ROLE] == 1
    assert result["characters"] == len(result["body"])


@pytest.mark.asyncio
async def test_the_disclaimer_buys_a_rewrite(provider, artifacts):
    provider.push(ROLE, draft(GOOD + " No pitch, genuinely asking."), draft(GOOD))

    result = await write(provider, artifacts)

    assert result["body"] == GOOD
    correction = provider.requests_for(ROLE)[1].messages[-1].content
    assert "no pitch" in correction.lower()


@pytest.mark.asyncio
async def test_a_tell_that_survives_the_rewrite_still_ships(provider, artifacts):
    """Advisory means advisory. A second turn is worth buying on the chance
    the writer drops the phrase; failing the whole run because it did not
    would hand the user nothing instead of something slightly worse."""
    stubborn = GOOD + " Just curious."
    provider.push(ROLE, draft(stubborn), draft(stubborn))

    result = await write(provider, artifacts)

    assert result["body"] == stubborn
    assert provider.calls_by_role[ROLE] == 2


@pytest.mark.asyncio
async def test_a_draft_that_cannot_ship_fails_the_run(provider, artifacts):
    """An unlicensed number is the other kind of problem: it is not worse
    copy, it is a claim this business cannot stand behind."""
    invented = "Hi Alice - Notewright saves your nine-person team 14 hours a week on release notes."
    provider.push(ROLE, draft(invented), draft(invented))

    with pytest.raises(OutputValidationError) as failure:
        await write(provider, artifacts)

    assert "14 hours" in str(failure.value)


@pytest.mark.asyncio
async def test_a_connection_note_is_held_to_its_own_limit(provider, artifacts):
    long_one = "Hi Alice, " + "release notes by hand. " * 12
    provider.push(ROLE, draft(long_one), draft(GOOD[:190]))

    result = await write(provider, artifacts, kind="connection")

    assert result["limit"] == 200
    assert "between 1 and 200 characters" in provider.requests_for(ROLE)[1].messages[-1].content


@pytest.mark.asyncio
async def test_the_writer_is_shown_the_person_it_is_writing_to(provider, artifacts):
    """The prompt used to carry the business, the offer and the whole evidence
    ledger, and not one word about the reader. A writer with only that
    material writes the only thing it supports."""
    provider.push(ROLE, draft(GOOD))
    await write(provider, artifacts)

    prompt = provider.requests_for(ROLE)[0].system_prompt or ""
    segment = artifacts.audience.primary()
    assert segment is not None
    assert segment.situation in prompt
    # And how the business sounds, which decides whether it reads as a person.
    assert artifacts.voice.tone in prompt
    assert "300 to 500 characters" in prompt
