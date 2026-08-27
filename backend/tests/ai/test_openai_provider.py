"""OpenAIProvider drives the Codex CLI so a run bills the ChatGPT plan.

Two things here are worth a test and one is worth it above all others: that no
API credential survives into the subprocess environment. That single filter is
the difference between a run the operator's subscription covers and a run that
charges their API balance, and nothing downstream would notice the difference
until the invoice.
"""

import json
from pathlib import Path

import pytest

from app.ai.base import AIMessage, AIRequest, ResearchTool
from app.ai.openai_provider import (
    CodexNotInstalledError,
    OpenAIProvider,
    _clean_env,
    _read_stream,
    _usage_from,
)


def _request(**kwargs) -> AIRequest:
    return AIRequest(
        system_prompt=kwargs.pop("system_prompt", "You are terse."),
        messages=[AIMessage(role="user", content=kwargs.pop("task", "Say OK"))],
        model=kwargs.pop("model", "gpt-5.6-sol"),
        **kwargs,
    )


# ------------------------------------------------------------------- billing


@pytest.mark.parametrize("variable", ["OPENAI_API_KEY", "CODEX_API_KEY"])
def test_no_api_credential_reaches_the_subprocess(monkeypatch, variable):
    """The one line that decides who pays. With either of these visible, Codex
    silently switches to API-key billing and the run costs money the operator
    did not agree to spend."""
    monkeypatch.setenv(variable, "sk-should-never-be-passed-through")
    assert variable not in _clean_env()


def test_the_rest_of_the_environment_is_left_alone(monkeypatch):
    """Only the credentials are stripped. Codex needs PATH to find its own
    helpers and HOME/USERPROFILE to find the ChatGPT login that pays for the
    call - a blank environment would break the very thing this provider is
    for."""
    monkeypatch.setenv("PATH", "/somewhere")
    monkeypatch.setenv("MARKETINGOS_UNRELATED", "kept")
    env = _clean_env()
    assert env["PATH"] == "/somewhere"
    assert env["MARKETINGOS_UNRELATED"] == "kept"


# ------------------------------------------------------------------- command


def test_the_command_is_confined_and_reads_its_prompt_from_stdin(monkeypatch):
    monkeypatch.setattr("app.ai.openai_provider._codex_path", lambda: "/usr/bin/codex")
    command = OpenAIProvider()._command(_request())

    assert command[:3] == ["/usr/bin/codex", "exec", "--json"]
    assert "--sandbox" in command and command[command.index("--sandbox") + 1] == "read-only"
    assert command[command.index("-m") + 1] == "gpt-5.6-sol"
    # Windows caps a command line at 32,767 characters and a compiled-knowledge
    # prompt runs past it, so the prompt must never be an argument.
    assert command[-1] == "-"
    assert "--ephemeral" in command
    assert "--skip-git-repo-check" in command


def test_the_working_directory_is_never_the_project(monkeypatch, tmp_path):
    """Codex reads AGENTS.md from its cwd and treats a git repo as the thing it
    is there to work on. Pointed at this project it would pick up both."""
    monkeypatch.setattr("app.ai.openai_provider._codex_path", lambda: "/usr/bin/codex")
    provider = OpenAIProvider()
    command = provider._command(_request())
    workdir = command[command.index("-C") + 1]

    assert not list(Path(workdir).iterdir())
    assert "MarketingOS" not in workdir


def test_web_search_is_only_enabled_when_a_role_asked_for_it(monkeypatch):
    monkeypatch.setattr("app.ai.openai_provider._codex_path", lambda: "/usr/bin/codex")
    provider = OpenAIProvider()

    assert "--search" not in provider._command(_request())
    assert "--search" in provider._command(_request(tools=[ResearchTool.WEB_SEARCH]))


def test_a_missing_binary_says_what_to_install(monkeypatch):
    """`ModelSession` retries a provider three times. Three copies of a bare
    'not found' is a worse message than one that names the fix."""
    monkeypatch.setattr("app.ai.openai_provider._codex_path", lambda: None)
    with pytest.raises(CodexNotInstalledError, match="codex login"):
        OpenAIProvider()._command(_request())


def test_the_system_prompt_travels_inside_the_message():
    """Codex takes no system prompt - `codex exec` has one prompt and its
    standing instructions come from AGENTS.md files on disk."""
    prompt = OpenAIProvider._prompt(_request(system_prompt="RULES", task="DO IT"))
    assert prompt.startswith("RULES")
    assert prompt.endswith("DO IT")
    assert "--- TASK ---" in prompt


# --------------------------------------------------------------------- usage


def test_cached_input_is_moved_across_rather_than_added():
    """Codex reports `cached_input_tokens` as a subset of `input_tokens`.
    Copying both through would double-count the majority of every call after
    the first, and fire the campaign budget guard on runs that were fine."""
    usage = _usage_from({"input_tokens": 24763, "cached_input_tokens": 24448, "output_tokens": 122})

    assert usage.cache_read_input_tokens == 24448
    assert usage.input_tokens == 24763 - 24448
    assert usage.billable_input_tokens == 24763


def test_reasoning_tokens_are_counted_as_output():
    """They are billed as output and reported separately. Dropped, a reasoning
    model looks nearly free."""
    usage = _usage_from(
        {"input_tokens": 10, "output_tokens": 5, "reasoning_output_tokens": 900}
    )
    assert usage.output_tokens == 905


def test_no_cost_is_invented_when_codex_reports_none():
    """Unlike the Claude CLI, Codex reports tokens and never a price. A
    confident 0.0 here would read as 'this run was free'."""
    assert _usage_from({"input_tokens": 10, "output_tokens": 5}).reported_cost_usd is None


# -------------------------------------------------------------------- stream


def _stream(*events: dict) -> str:
    return "\n".join(json.dumps(event) for event in events)


def test_the_answer_and_the_usage_come_out_of_one_stream():
    text, usage, model, failure = _read_stream(
        _stream(
            {"type": "thread.started", "model": "gpt-5.6-sol"},
            {"type": "turn.started"},
            {"type": "item.completed", "item": {"type": "agent_message", "text": "the answer"}},
            {"type": "turn.completed", "usage": {"input_tokens": 100, "output_tokens": 20}},
        )
    )

    assert text == "the answer"
    assert usage.output_tokens == 20
    assert model == "gpt-5.6-sol"
    assert failure is None


def test_the_last_assistant_message_is_the_answer():
    """A turn that thought out loud ends on the message that answers the
    question, not on the one it started with."""
    text, _, _, _ = _read_stream(
        _stream(
            {"type": "item.completed", "item": {"type": "agent_message", "text": "thinking"}},
            {"type": "item.completed", "item": {"type": "agent_message", "text": "final"}},
        )
    )
    assert text == "final"


def test_non_message_items_are_not_mistaken_for_the_answer():
    text, _, _, _ = _read_stream(
        _stream(
            {"type": "item.completed", "item": {"type": "reasoning", "text": "hmm"}},
            {"type": "item.completed", "item": {"type": "agent_message", "text": "real"}},
        )
    )
    assert text == "real"


def test_a_failed_turn_is_reported_with_its_reason():
    """This is the shape a free-plan rate limit arrives in. The reason has to
    survive to the operator, or 'the run failed' is all they get."""
    _, _, _, failure = _read_stream(
        _stream({"type": "turn.failed", "error": {"message": "usage limit reached"}})
    )
    assert failure == "usage limit reached"


def test_unknown_and_unparseable_lines_cost_nothing():
    """The stream is a versioned feed from a tool that ships weekly. An event
    type added next month must cost at most the thing it carried."""
    text, _, _, failure = _read_stream(
        "\n".join(
            [
                "not json at all",
                json.dumps({"type": "item.something.new", "item": {"whatever": 1}}),
                json.dumps({"type": "notice", "text": "ignore me"}),
                json.dumps(
                    {"type": "item.completed", "item": {"type": "agent_message", "text": "ok"}}
                ),
            ]
        )
    )
    assert text == "ok"
    assert failure is None


def test_only_web_search_is_offered():
    assert OpenAIProvider().available_tools("gpt-5.6-sol") == frozenset(
        {ResearchTool.WEB_SEARCH}
    )
