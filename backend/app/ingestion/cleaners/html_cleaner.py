import re

from app.ingestion.cleaners.base import Cleaner

_TAG_RE = re.compile(r"<[^>]+>")


class HtmlCleaner(Cleaner):
    """Strips any residual raw HTML tags. Defensive - the website loader
    already converts to Markdown, but PDF/DOCX extraction can occasionally
    leak inline markup, and this is a no-op on tag-free text either way."""

    def clean(self, text: str) -> str:
        return _TAG_RE.sub("", text)
