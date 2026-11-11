"""A late subject change cannot inherit permission to add unrelated defects."""

from types import SimpleNamespace

import pytest

from app.marketing.briefs import EmailBrief
from app.marketing.craft import CraftLoop
from app.marketing.email_copy import Email
from app.marketing.gates import GateIssue, GateReport
from app.marketing.substantiation import Substantiation
from tests.marketing.conftest import artifacts_fixture


@pytest.mark.asyncio
async def test_subject_polish_preserves_existing_blocks_but_refuses_new_ones():
    email = Email(position=1, subject="The original", preview_text="The original preview",
                  greeting="Hi", body="A concrete product description.",
                  call_to_action="See the example", sign_off="The team")
    original = GateIssue(gate="clarity", detail="missing product")
    added = GateIssue(gate="evidence", detail="invented price")
    best = SimpleNamespace(email=email, idea="", gates=GateReport(issues=[original]))

    class Subjects:
        async def improve(self, **kwargs):
            screen = kwargs["screen"]
            assert screen(email)
            assert not screen(email.model_copy(update={"subject": "An invented price"}))
            return email.model_copy(update={"preview_text": "An improved preview"}), "updated preview"

    loop = SimpleNamespace(
        _subjects=Subjects(), _subject_variants=2, _artifacts=artifacts_fixture(),
        _personas=["a developer"],
        _observer=SimpleNamespace(on_role_started=lambda *a: None, on_role_finished=lambda *a: None),
        _check=lambda candidate, *a: (
            GateReport(issues=[original, added] if candidate.subject == "An invented price" else [original]),
            Substantiation(),
        ),
    )
    await CraftLoop._polish_subject(
        loop, SimpleNamespace(best=best), EmailBrief(), [],
        SimpleNamespace(reader_segment="", reader="a developer"),
    )
    assert best.email.subject == email.subject
    assert best.email.preview_text == "The original preview"
