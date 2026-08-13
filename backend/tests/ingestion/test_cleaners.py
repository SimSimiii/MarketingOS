from app.ingestion.cleaners.base import CleanerPipeline
from app.ingestion.cleaners.duplicate_cleaner import DuplicateCleaner
from app.ingestion.cleaners.empty_section_cleaner import EmptySectionCleaner
from app.ingestion.cleaners.html_cleaner import HtmlCleaner
from app.ingestion.cleaners.markdown_cleaner import MarkdownCleaner
from app.ingestion.cleaners.whitespace_cleaner import WhitespaceCleaner


def test_whitespace_cleaner_collapses_blank_lines_and_trailing_spaces():
    text = "line one   \n\n\n\n\nline two"
    result = WhitespaceCleaner().clean(text)
    assert result == "line one\n\nline two"


def test_html_cleaner_strips_residual_tags():
    result = HtmlCleaner().clean("<p>hello <b>world</b></p>")
    assert result == "hello world"


def test_html_cleaner_is_noop_on_plain_text():
    assert HtmlCleaner().clean("plain markdown text") == "plain markdown text"


def test_markdown_cleaner_normalizes_heading_spacing():
    result = MarkdownCleaner().clean("##   Heading with extra spaces   ")
    assert result == "## Heading with extra spaces"


def test_duplicate_cleaner_drops_consecutive_duplicate_lines():
    text = "Home\nHome\nHome\nAbout content"
    result = DuplicateCleaner().clean(text)
    assert result == "Home\nAbout content"


def test_empty_section_cleaner_drops_heading_with_no_content():
    text = "# Real Section\nSome content\n\n# Empty Section\n\n# Another Real Section\nMore content"
    result = EmptySectionCleaner().clean(text)
    assert "# Empty Section" not in result
    assert "# Real Section" in result
    assert "# Another Real Section" in result


def test_cleaner_pipeline_applies_in_order():
    pipeline = CleanerPipeline([HtmlCleaner(), WhitespaceCleaner()])
    result = pipeline.apply("<p>hello</p>   \n\n\n\nworld")
    assert result == "hello\n\nworld"
