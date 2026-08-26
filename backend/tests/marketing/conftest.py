"""Test doubles for the campaign pipeline.

The provider here answers by ROLE rather than by call position. A positional
script breaks every time a phase gains a call - which, in a system whose whole
point is that quality comes from extra passes, is constantly - and the
resulting failures say nothing about what actually regressed. Answering by
role means a test states "the cold reader hated this draft" and stays true
however many other calls the run makes around it.
"""

import asyncio
import json
from collections import defaultdict, deque
from collections.abc import AsyncIterator, Callable
from typing import Any

import pytest

from app.ai.base import AIProvider, AIRequest, AIResponse, AIUsage
from app.ai.model_router import ModelRouter
from app.core.config import PROMPTS_DIR
from app.knowledge.artifacts import (
    AudienceModel,
    BusinessProfile,
    CallToAction,
    KnowledgeArtifacts,
    OfferSheet,
    Plan,
    Segment,
    VoiceProfile,
)
from app.knowledge.compiler import find_gaps
from app.knowledge.corpus import Document, SourceCorpus
from app.knowledge.ledger import Evidence, EvidenceKind, EvidenceLedger
from app.knowledge.store import StoredArtifacts
from app.marketing.pipeline import KnowledgeGateway
from app.marketing.reader import _PULL_BY_CLICKS
from app.marketing.request import CampaignRequest
from app.runtime.events import EventBus
from app.runtime.model_session import ModelSession
from app.runtime.prompt_engine import PromptEngine

#: Queue this instead of a response to simulate a provider failure (the CLI
#: refusing to start, a dropped connection) for that role's next call.
FAIL = "<<provider-failure>>"

#: A role's fallback answer: fixed text, or a function of the call number.
type Default = str | Callable[[int], str]


class RoleScriptedProvider(AIProvider):
    """Answers each role from its own queue, falling back to a default.

    A role with a queued response consumes it; a role that runs out falls back
    to its default answer, so a test only has to script the calls it is
    actually about.
    """

    def __init__(
        self, defaults: dict[str, Default] | None = None, tokens_per_call: int = 15
    ) -> None:
        self.defaults: dict[str, Default] = dict(defaults or {})
        self.queues: dict[str, deque[str]] = defaultdict(deque)
        self.requests: list[AIRequest] = []
        self.calls_by_role: dict[str, int] = defaultdict(int)
        #: Split two-thirds input, one-third output. Only the total matters to
        #: the budget guard, but a test reading either field should see
        #: something plausible.
        self.tokens_per_call = tokens_per_call
        #: Highest number of that role's calls in flight at once. Concurrency
        #: is a property a test can otherwise only assert by timing, which is
        #: how a suite acquires a flake - this counts it instead.
        self.max_concurrent_by_role: dict[str, int] = defaultdict(int)
        self._in_flight: dict[str, int] = defaultdict(int)

    def push(self, key: str, *responses: str) -> "RoleScriptedProvider":
        self.queues[key].extend(responses)
        return self

    def set_default(self, key: str, response: Default) -> "RoleScriptedProvider":
        self.defaults[key] = response
        return self

    def requests_for(self, role: str) -> list[AIRequest]:
        return [request for request in self.requests if request.role == role]

    @staticmethod
    def _keys(request: AIRequest) -> tuple[str, ...]:
        """Most specific first. One role can make several differently-shaped
        calls - the compiler reads for a profile, then for evidence, then for
        voice - and those are only tellable apart by template."""
        return tuple(key for key in (request.template, request.role) if key)

    async def generate(self, request: AIRequest) -> AIResponse:
        self.requests.append(request)
        self.calls_by_role[request.role] += 1
        # Taken here, before this call can suspend. Callers now issue several
        # of a role's calls concurrently (three openings in the bake-off, a
        # whole reader panel), so a default that read the shared counter after
        # awaiting would see whatever the other in-flight calls had left it
        # at - and `varied_draft` would hand all three candidates the same
        # email, which the overlap gate then correctly rejects. The failure
        # looks like a pipeline bug and is entirely this double's.
        call_number = self.calls_by_role[request.role]
        self._in_flight[request.role] += 1
        self.max_concurrent_by_role[request.role] = max(
            self.max_concurrent_by_role[request.role], self._in_flight[request.role]
        )
        try:
            return await self._answer(request, call_number)
        finally:
            self._in_flight[request.role] -= 1

    async def _answer(self, request: AIRequest, call_number: int) -> AIResponse:
        # A real provider always suspends here - it is waiting on a subprocess
        # or a socket. Without a suspension point this double runs each call
        # start-to-finish before the next one begins, so concurrent code and
        # sequential code are indistinguishable and `max_concurrent_by_role`
        # would read 1 forever.
        await asyncio.sleep(0)
        keys = self._keys(request)

        content: str | None = None
        for key in keys:
            if self.queues.get(key):
                content = self.queues[key].popleft()
                break
        if content is None:
            for key in keys:
                if key in self.defaults:
                    default = self.defaults[key]
                    # A default may vary with the call number - the writer's
                    # has to, or three emails come back identical and the
                    # overlap gate fires on the fixture rather than on
                    # anything the test is about.
                    content = default(call_number) if callable(default) else default
                    break
        if content is None:
            raise AssertionError(
                f"No scripted response for {' / '.join(keys) or 'an unnamed call'} "
                f"(call {call_number} of that role)"
            )

        if content == FAIL:
            raise ConnectionError("scripted provider failure")
        return AIResponse(
            content=content,
            model=request.model or "scripted-model",
            usage=AIUsage(
                input_tokens=self.tokens_per_call * 2 // 3,
                output_tokens=self.tokens_per_call // 3,
            ),
        )

    async def stream(self, request: AIRequest) -> AsyncIterator[str]:
        response = await self.generate(request)
        yield response.content

    def count_tokens(self, text: str) -> int:
        return len(text.split())


# --------------------------------------------------------------- canned answers


#: Three bodies with no shared six-word run and no shared opening move, so the
#: overlap gate stays quiet on the fixture itself. Numbers are spelled out:
#: the evidence gate is real, and a fixture that trips it teaches nothing.
#:
#: Every one of them spends the fact the fixture brief assigns (E1, the nine
#: seconds), and that is not decoration. A real writer is handed the evidence
#: its email is built on and told to keep it through every rewrite, so a
#: fixture whose second draft quietly drops it is not a rewrite of the first -
#: it is a different email. The loop now notices that difference (see
#: app.marketing.substantiation), so a test about the rewrite mechanism whose
#: fixture moved the evidence underneath it would be measuring two things at
#: once. A test that wants a draft arguing from nothing writes one.
_BODIES = (
    (
        "You wrote the same release note three times last month.\n\n"
        "Every one of them started as a changelog nobody read, and ended as a paragraph you\n"
        "rewrote twice before shipping it.\n\n"
        "This turns commits you already pushed into that paragraph, in about nine seconds.\n"
        "You edit it or you send it.\n\n"
        "Most people ask whether it sounds like them. It reads your older notes first, so it does."
    ),
    (
        "Friday afternoon is where your shipping week goes to die.\n\n"
        "The work was done on Tuesday. What is left is describing it, and describing it is the\n"
        "part nobody scheduled time for.\n\n"
        "Point it at the branch and nine seconds later there is a note to argue with.\n\n"
        "Teams tell us the draft is close enough that arguing with it is faster than starting."
    ),
    (
        "Your changelog has a tone, and it is not the one you would use out loud.\n\n"
        "That happens when writing gets squeezed into whatever minutes are left before a\n"
        "deploy window closes on you.\n\n"
        "Give it the twenty entries you already published and it writes like those did, in\n"
        "nine seconds.\n\n"
        "Nothing to configure. Paste a branch name, read a paragraph, decide whether to keep it."
    ),
)

_SUBJECTS = (
    "Release notes, written before you sit down",
    "The Friday afternoon nobody scheduled",
    "It already knows how you write",
)


def email_draft(
    subject: str = "Release notes, written before you sit down",
    cta: str = "Start the trial",
    body: str | None = None,
    preview: str = "what changes on Monday if you try it",
) -> str:
    """One email exactly as the writer emits it: the labelled-field envelope
    parsed by app.marketing.email_copy, not JSON."""
    return (
        f"ROLE: hook\n"
        f"SUBJECT: {subject}\n"
        f"PREVIEW: {preview}\n"
        f"GREETING: Hi there,\n"
        f"CTA: {cta}\n"
        f"SIGNOFF: - The team\n"
        f"PS: The free tier stays free after the trial ends.\n"
        f"BODY:\n{body or _BODIES[0]}\n"
    )


def varied_draft(call: int) -> str:
    """A different email on every writer turn."""
    index = (call - 1) % len(_BODIES)
    return email_draft(
        subject=_SUBJECTS[index],
        body=_BODIES[index],
        preview=f"what changes on Monday, part {['one', 'two', 'three'][index]}",
    )


def blind_read(pull: int = 8, would_act: bool = True, **overrides: Any) -> str:
    """One cold reader's report, written the way the real one answers.

    `pull` is stated as the score the test means and turned back into the click
    frequency that produces it, because that frequency is what the reader
    actually reports now and what `BlindRead` derives the score from - see
    `app.marketing.reader.pull_from_clicks`. A fixture that sets `pull`
    directly would be testing a field the validator overwrites.
    """
    payload = {
        "opened": True,
        "stopped_at": "",
        "what_it_sells": "a faster way to write my release notes",
        "biggest_doubt": "whether my team would switch",
        "would_act": would_act,
        "opens_in_100": 30,
        "clicks_in_100": clicks_for(pull),
        "to_click_it_would_have_to": "tell me what it costs once the credits run out",
        "fixes": [],
    }
    payload.update(overrides)
    return json.dumps(payload)


def clicks_for(pull: int) -> int:
    """The smallest click frequency that scores `pull`."""
    return next(
        (floor for floor, score in _PULL_BY_CLICKS if score <= pull),
        0,
    )


READ_PASS = blind_read()
READ_FAIL = blind_read(
    pull=3,
    would_act=False,
    stopped_at="Most teams still burn months on the boring parts.",
    what_it_sells="honestly, I could not tell",
    fixes=["cut the second paragraph"],
)

#: Whichever draft was shown second. Positional rather than semantic on
#: purpose: the judge alternates the label order across a ballot, so a default
#: that always says "A" would hand every duel to whoever happened to be first
#: and no test could tell a real preference from that.
VOTE_B = json.dumps({"winner": "B", "why": "it told me what it costs", "margin": "clear"})
VOTE_A = json.dumps({"winner": "A", "why": "it got to the point", "margin": "clear"})


def votes_for_the_challenger(count: int = 4) -> list[str]:
    """A ballot every reader answers in favour of the newer draft.

    The judge shows the challenger as A on even ballot lines and as B on odd
    ones, so "the challenger wins every vote" is an alternating list of
    letters rather than one letter repeated. Pushed onto the role's queue in
    that order, which is the order the votes are issued in.
    """
    return [VOTE_A if index % 2 == 0 else VOTE_B for index in range(count)]


def votes_for_the_champion(count: int = 4) -> list[str]:
    return [VOTE_B if index % 2 == 0 else VOTE_A for index in range(count)]


def subject_options(count: int = 4) -> str:
    return json.dumps(
        {
            "options": [
                {
                    "subject": f"Release notes, option {index}",
                    "preview": f"a different bet, number {index}",
                    "approach": f"approach {index}",
                }
                for index in range(1, count + 1)
            ]
        }
    )


def inbox_verdict(*opens: int) -> str:
    """How many of a hundred would tap each listed line, in order. The first
    number is always the incumbent - see SubjectBakeOff.improve."""
    return json.dumps(
        {
            "scores": [
                {"option": index, "opens_in_100": value, "why": "specific"}
                for index, value in enumerate(opens, start=1)
            ]
        }
    )

CRITIQUE_SHIP = json.dumps({"verdict": "ship", "edits": [], "summary": "Ready to send."})
CRITIQUE_REVISE = json.dumps(
    {
        "verdict": "revise",
        "brief_drift": "argues speed, but the brief assigned the switching-cost objection",
        "unspent_evidence": ["E1"],
        "edits": [
            {
                "line": "Most people ask whether it sounds like them.",
                "problem": "answers a doubt the reader did not have",
                "fix": "answer the switching cost instead",
                "severity": "major",
            }
        ],
        "summary": "Right voice, wrong argument.",
    }
)
SEQUENCE_PASS = json.dumps(
    {
        "escalates": True,
        "promise_is_consistent": True,
        "each_stands_alone": True,
        "notes": [],
        "summary": "Escalates cleanly from hook to deadline.",
    }
)


def campaign_brief(
    count: int = 3, alternatives: list[str] | None = None, **overrides: Any
) -> str:
    """A strategist's answer. `alternatives` are the other claims each slot
    could argue - what the bake-off varies and what a stalled email pivots to.
    Empty by default, which is the brief that gives the loop one bet."""
    payload: dict[str, Any] = {
        "interpretation": "A conversion sequence for people who have not bought yet.",
        "reader": "a developer who ships weekly and writes release notes by hand",
        "promise": "release notes stop being a Friday afternoon job",
        "arc": "hook, then proof, then the objection",
        "sequence_rationale": "Each email spends a different proof.",
        "voice_notes": "",
        "emails": [
            {
                "position": position,
                "job": f"job {position}",
                "single_idea": f"idea number {position} that nothing else argues",
                "alternative_ideas": list(alternatives or []),
                "evidence_ids": ["E1"] if position == 1 else [],
                "objection": "we already have a script for this",
                "tone": "matter-of-fact",
                "call_to_action": "Start the trial",
                "subject_strategy": "concrete, names the outcome",
                "must_not_reuse": [],
            }
            for position in range(1, count + 1)
        ],
    }
    payload.update(overrides)
    return json.dumps(payload)


# ------------------------------------------------------------------- fixtures


def artifacts_fixture() -> KnowledgeArtifacts:
    """Compiled knowledge for a small, believable business.

    Gaps are computed rather than hand-written, so the fixture carries the same
    honest holes a real compile would - there are no testimonials here, and
    everything downstream should know it.
    """
    artifacts = KnowledgeArtifacts(
        business=BusinessProfile(
            company_name="Notewright",
            what_it_does="turns your merged commits into a release note",
            category="developer tooling",
            vocabulary=["release note", "changelog", "ship"],
        ),
        offer=OfferSheet(
            plans=[Plan(name="Team", price="$29/month")],
            free_entry="1,500 free credits, no card",
            calls_to_action=[CallToAction(label="Start the trial", intent="self-serve signup")],
            purchase_motion="self-serve",
        ),
        evidence=EvidenceLedger(
            entries=[
                Evidence(
                    id="E1",
                    kind=EvidenceKind.METRIC,
                    claim="writes a release note in about nine seconds",
                    verbatim="Notewright drafts a release note in about nine seconds.",
                    source="https://example.com",
                ),
                Evidence(
                    id="E2",
                    kind=EvidenceKind.PRICE,
                    claim="$29/month for the Team plan, 1,500 free credits to start",
                    verbatim="Team is $29/month. Every account starts with 1,500 free credits.",
                    source="https://example.com/pricing",
                ),
            ]
        ),
        voice=VoiceProfile(
            learned=True,
            tone="plain, technical, no superlatives",
            exemplars=["We shipped it on a Tuesday and told nobody."],
        ),
        audience=AudienceModel(
            segments=[
                Segment(
                    name="a developer who ships weekly and writes release notes by hand",
                    situation="ships every Friday, writes the note on Friday afternoon",
                )
            ]
        ),
    )
    artifacts.gaps = find_gaps(artifacts)
    return artifacts


class FakeKnowledgeGateway(KnowledgeGateway):
    """Knowledge without a database. `compiled` pre-loads artifacts so a test
    about writing does not have to script a compiler run."""

    def __init__(
        self,
        documents: list[Document] | None = None,
        compiled: KnowledgeArtifacts | None = None,
        learnings: str = "",
    ) -> None:
        self._corpus = SourceCorpus.from_documents(documents or [])
        self.stored = (
            StoredArtifacts(artifacts=compiled, version=1, fingerprint="fixed")
            if compiled is not None
            else None
        )
        self.saves: list[KnowledgeArtifacts] = []
        self._learnings = learnings

    def corpus(self) -> SourceCorpus:
        return self._corpus

    def fingerprint(self) -> str:
        return "fixed"

    def load(self) -> StoredArtifacts | None:
        return self.stored

    def save(self, artifacts: KnowledgeArtifacts, fingerprint: str) -> StoredArtifacts:
        self.saves.append(artifacts)
        self.stored = StoredArtifacts(artifacts=artifacts, version=1, fingerprint=fingerprint)
        return self.stored

    def prior_learnings(self) -> str:
        return self._learnings


def make_session(
    provider: AIProvider, overrides: dict[str, str] | None = None
) -> ModelSession:
    """A session wired to the REAL prompt templates in backend/prompts, so
    tests also prove every template renders with real inputs."""
    return ModelSession(
        provider=provider,
        prompt_engine=PromptEngine(PROMPTS_DIR),
        events=EventBus(),
        model_router=ModelRouter(overrides),
        execution_id="test-execution",
    )


@pytest.fixture
def artifacts() -> KnowledgeArtifacts:
    return artifacts_fixture()


@pytest.fixture
def request_fixture() -> CampaignRequest:
    return CampaignRequest(
        name="Launch",
        request="Write me 3 emails that make people buy my note-taking app",
        product_description="A note-taking app for developers",
        product_url="https://example.com",
        target_market="developers",
        goals="Drive signups",
    )


#: Compiler answers keyed by template, because one role makes all four calls.
COMPILER_DEFAULTS: dict[str, Default] = {
    "knowledge_profile": json.dumps(
        {
            "business": {
                "company_name": "Notewright",
                "what_it_does": "turns merged commits into a release note",
                "category": "developer tooling",
            },
            "offer": {
                "plans": [{"name": "Team", "price": "$29/month"}],
                "calls_to_action": [{"label": "Start the trial", "intent": "self-serve"}],
            },
        }
    ),
    # Two entries rather than none. A compile that finds nothing checkable is
    # a real case and it has its own tests - but it is not the *default* case,
    # and using it as the fixture meant every run in the suite went through the
    # preflight stop for a business with nothing to argue from. A fixture
    # should be the ordinary path.
    "knowledge_evidence": json.dumps(
        {
            "entries": [
                {
                    "id": "E1",
                    "kind": "metric",
                    "claim": "writes a release note in about nine seconds",
                    "verbatim": "Notewright drafts a release note in about nine seconds.",
                },
                {
                    "id": "E2",
                    "kind": "price",
                    "claim": "1,500 free credits to start, no card",
                    "verbatim": "Every account starts with 1,500 free credits and no card.",
                },
            ]
        }
    ),
    "knowledge_voice": json.dumps({"voice": {"tone": "plain and technical", "exemplars": []}}),
    "knowledge_audience": json.dumps(
        {
            "audience": {
                "segments": [
                    {"name": "a developer who ships weekly", "situation": "ships Fridays"}
                ],
                "objections": [{"objection": "we already have a script"}],
            }
        }
    ),
}


def default_answers() -> dict[str, Default]:
    """Enough for a whole run to finish without any scripting."""
    return {
        **COMPILER_DEFAULTS,
        "strategist": campaign_brief(3),
        "email_writer": varied_draft,
        "blind_reader": READ_PASS,
        "conversion_critic": CRITIQUE_SHIP,
        "sequence_reviewer": SEQUENCE_PASS,
        # A constant vote is a guaranteed tie, and a tie leaves the version
        # that already worked standing. That is the property worth having as
        # the default: the ballot alternates which draft wears which label, so
        # every reader picking the same *letter* means half of them picked the
        # challenger. A test that wants a winner scripts one - see
        # `votes_for_the_challenger`.
        "preference_judge": VOTE_A,
        "subject_lines": subject_options(),
        # The line the email already had, first and highest - so the default
        # run keeps its own subject and no test has to think about a swap it
        # did not ask for.
        "inbox_scanner": inbox_verdict(40, 20, 20, 20, 20),
    }


@pytest.fixture
def provider() -> RoleScriptedProvider:
    return RoleScriptedProvider(default_answers())
