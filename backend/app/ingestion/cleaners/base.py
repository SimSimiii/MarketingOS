from abc import ABC, abstractmethod

from app.ingestion.cleaners.code_regions import preserve_code


class Cleaner(ABC):
    """A single, chainable text transform. Cleaners never change meaning,
    only remove noise (whitespace, boilerplate, leftover markup)."""

    @abstractmethod
    def clean(self, text: str) -> str:
        raise NotImplementedError


class CleanerPipeline:
    """Applies an ordered list of Cleaners in sequence."""

    def __init__(self, cleaners: list[Cleaner]) -> None:
        self._cleaners = cleaners

    def apply(self, text: str) -> str:
        return preserve_code(text, self._clean_prose)

    def _clean_prose(self, text: str) -> str:
        for cleaner in self._cleaners:
            text = cleaner.clean(text)
        return text
