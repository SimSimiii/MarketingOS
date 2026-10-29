from app.marketing.pipeline import _reader_recommendation
from app.marketing.report import EmailReportLine, ReaderVerdict


def test_a_satisfied_reader_does_not_create_a_missing_material_request():
    line = EmailReportLine(position=1,landed=True,pull=8,reader_verdicts=[ReaderVerdict(
        biggest_doubt="Nothing material stops me inspecting it",
        to_click_it_would_have_to="Tell me no signup is required — which it did.")])
    assert _reader_recommendation([line]) == ""


def test_an_unresolved_copy_finding_still_surfaces_the_readers_obstacle():
    line = EmailReportLine(position=1,landed=True,pull=8,unresolved=["Review access requirements"],
        reader_verdicts=[ReaderVerdict(to_click_it_would_have_to="Explain whether signup is needed")])
    assert "Explain whether signup is needed" in _reader_recommendation([line])
    line.landed=False
    line.unresolved=[]
    assert "Explain whether signup is needed" in _reader_recommendation([line])


def test_an_explicit_audience_mismatch_is_not_hidden_by_a_landed_flag():
    line = EmailReportLine(position=1,landed=True,pull=8,reader_verdicts=[ReaderVerdict(
        situation_matches=False,relevance_feedback="The recipient does not run a website")])
    assert "does not run a website" in _reader_recommendation([line])
