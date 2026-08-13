import re

from app.ingestion.cleaners.base import Cleaner

_TRAILING_SPACE_RE = re.compile(r"[ \t]+\n")
_BLANK_LINES_RE = re.compile(r"\n{3,}")


class WhitespaceCleaner(Cleaner):
    """Strips trailing spaces and collapses 3+ blank lines down to one."""

    def clean(self, text: str) -> str:
        text = _TRAILING_SPACE_RE.sub("\n", text)
        text = _BLANK_LINES_RE.sub("\n\n", text)
        return text.strip()
