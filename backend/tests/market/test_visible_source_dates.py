from datetime import date

import pytest

from app.market.source_dates import publication_date


@pytest.mark.parametrize("text,expected", [
    ("23 Sep 2018", date(2018, 9, 23)),
    ("23 September 2018", date(2018, 9, 23)),
    ("31 Feb 2018", None),
    ("23 Septic 2018", None),
    ("23 Sep 2029", None),
    ("Updated 23 Sep 2018", None),
    ("Our launch on 23 Sep 2018 was successful.", None),
])
def test_isolated_title_date_is_not_confused_with_prose_or_modification(text, expected):
    result, basis = publication_date(f"<h1>Switching analytics</h1><p>{text}</p>",
                                     "https://example.com/story", date(2026, 10, 25))
    assert result == expected
    assert basis == ("page_title_date" if expected else "unknown")


def test_footer_date_does_not_become_a_publication_date():
    assert publication_date("<h1>Story</h1><footer><p>23 Sep 2018</p></footer>",
                            "https://example.com/story", date(2026, 10, 25)) == (None, "unknown")
