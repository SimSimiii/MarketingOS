from abc import ABC, abstractmethod
from typing import ClassVar

from app.ingestion.documents import RawDocument, SourceType


class Loader(ABC):
    """Turns a source (URL, file path, or raw text - documented per loader)
    into a RawDocument. Loaders never clean, normalize or summarize - they
    only extract content and whatever incidental metadata is cheap to grab
    along the way (e.g. an HTML <title>)."""

    source_type: ClassVar[SourceType]

    @abstractmethod
    async def load(self, source: str) -> RawDocument:
        raise NotImplementedError
