from abc import ABC, abstractmethod
from typing import ClassVar

from app.ingestion.documents import RawDocument, SourceType


class Loader(ABC):
    """Turns a source (URL, file path, or raw text - documented per loader)
    into a RawDocument. Loaders never clean, normalize or summarize - they
    only extract content and whatever incidental metadata is cheap to grab
    along the way (e.g. an HTML <title>).

    `is_path` is the caller vouching that `source` is a local path the server
    itself created - today, only the temporary file an upload is written to.
    It defaults to False, and the default is the security-relevant half: these
    loaders used to decide by asking the filesystem whether `source` happened
    to name a file, which makes any text a user can paste into the ingestion
    form a request to read that path off the server. A string that reached us
    from outside is content, whatever it looks like.
    """

    source_type: ClassVar[SourceType]

    @abstractmethod
    async def load(self, source: str, *, is_path: bool = False) -> RawDocument:
        raise NotImplementedError
