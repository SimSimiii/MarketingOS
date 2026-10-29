import pytest

from app.market.claims import Claim, ClaimAxis, comparable_claim, compare_claims


@pytest.mark.parametrize("left,right", [
    ("Real-time website analytics dashboard", "Realtime website analytics dashboard"),
    ("Live visitor dashboard", "Real time visitor dashboard"),
    ("One-page dashboard shows website visits", "Single-page dashboard shows website visits"),
])
def test_literal_dashboard_paraphrases_are_compared(left,right):
    assert comparable_claim(Claim(text=left,axis=ClaimAxis.SPEED),Claim(text=right,axis=ClaimAxis.SPEED))


def test_real_time_does_not_make_unrelated_objects_comparable():
    assert not comparable_claim(Claim(text="Real-time parcel delivery tracking",axis=ClaimAxis.SPEED),
                                Claim(text="Live visitor analytics dashboard",axis=ClaimAxis.SPEED))


def test_refresh_interval_is_related_but_not_equivalent_to_an_unquantified_dashboard():
    first = Claim(text="The dashboard shows real-time data", axis=ClaimAxis.SPEED)
    second = Claim(text="Our real-time dashboard refreshes every 30 seconds", axis=ClaimAxis.SPEED)
    assert comparable_claim(first, second)
    assert compare_claims(first, second)[0] == "potential_difference"


def test_a_clickable_public_live_demo_does_not_mean_realtime_updates():
    assert not comparable_claim(Claim(text="A clickable live dashboard demo",axis=ClaimAxis.SPEED),
                                Claim(text="A real-time dashboard updates every 30 seconds",axis=ClaimAxis.SPEED))
