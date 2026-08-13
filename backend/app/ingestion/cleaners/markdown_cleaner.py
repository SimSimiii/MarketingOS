import re

from app.ingestion.cleaners.base import Cleaner

_HEADING_RE = re.compile(r"^(#{1,6})\s*(.+?)\s*$", re.MULTILINE)


class MarkdownCleaner(Cleaner):
    """Normalizes Markdown heading formatting: exactly one space after the
    '#' markers, no trailing whitespace on the heading line."""

    def clean(self, text: str) -> str:
        return _HEADING_RE.sub(lambda m: f"{m.group(1)} {m.group(2)}", text)
