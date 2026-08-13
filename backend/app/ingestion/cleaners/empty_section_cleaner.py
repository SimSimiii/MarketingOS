import re

from app.ingestion.cleaners.base import Cleaner

_HEADING_LINE_RE = re.compile(r"^#{1,6}\s+.+$")


class EmptySectionCleaner(Cleaner):
    """Drops a Markdown heading that has no content before the next heading
    (or the end of the document) - a section stub left over from stripping."""

    def clean(self, text: str) -> str:
        lines = text.split("\n")
        keep = [True] * len(lines)

        for i, line in enumerate(lines):
            if not _HEADING_LINE_RE.match(line.strip()):
                continue
            has_content = False
            for j in range(i + 1, len(lines)):
                next_line = lines[j].strip()
                if _HEADING_LINE_RE.match(next_line):
                    break
                if next_line:
                    has_content = True
                    break
            if not has_content:
                keep[i] = False

        return "\n".join(line for line, keep_it in zip(lines, keep, strict=True) if keep_it)
