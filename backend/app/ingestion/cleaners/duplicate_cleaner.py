from app.ingestion.cleaners.base import Cleaner


class DuplicateCleaner(Cleaner):
    """Drops consecutive duplicate lines (common leftover from stripped
    navigation menus repeating the same links line after line)."""

    def clean(self, text: str) -> str:
        lines = text.split("\n")
        deduped: list[str] = []
        previous: str | None = None
        for line in lines:
            stripped = line.strip()
            if stripped and stripped == previous:
                continue
            deduped.append(line)
            previous = stripped
        return "\n".join(deduped)
