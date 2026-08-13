from pathlib import Path

from app.ingestion.documents import SourceType
from app.ingestion.exceptions import LoaderNotFoundError
from app.ingestion.loaders.base import Loader
from app.ingestion.loaders.docx_loader import DocxLoader
from app.ingestion.loaders.json_loader import JsonLoader
from app.ingestion.loaders.markdown_loader import MarkdownLoader
from app.ingestion.loaders.pdf_loader import PdfLoader
from app.ingestion.loaders.text_loader import PlainTextLoader
from app.ingestion.loaders.website_loader import WebsiteLoader

_EXTENSION_MAP: dict[str, SourceType] = {
    ".md": SourceType.MARKDOWN,
    ".markdown": SourceType.MARKDOWN,
    ".pdf": SourceType.PDF,
    ".docx": SourceType.DOCX,
    ".json": SourceType.JSON,
    ".txt": SourceType.PLAIN_TEXT,
    ".png": SourceType.IMAGE,
    ".jpg": SourceType.IMAGE,
    ".jpeg": SourceType.IMAGE,
    ".gif": SourceType.IMAGE,
    ".webp": SourceType.IMAGE,
    ".mp4": SourceType.VIDEO,
    ".mov": SourceType.VIDEO,
    ".avi": SourceType.VIDEO,
    ".mp3": SourceType.AUDIO,
    ".wav": SourceType.AUDIO,
    ".m4a": SourceType.AUDIO,
}


def detect_source_type(source: str) -> SourceType:
    """Infers a SourceType from a URL scheme or file extension. Falls back to
    plain text for anything unrecognized (e.g. a raw string with no path)."""
    if source.startswith(("http://", "https://")):
        return SourceType.WEBSITE

    suffix = Path(source).suffix.lower()
    return _EXTENSION_MAP.get(suffix, SourceType.PLAIN_TEXT)


class LoaderRegistry:
    """Single source of truth for available loaders."""

    def __init__(self) -> None:
        self._loaders: dict[SourceType, Loader] = {}

    def register(self, loader: Loader) -> None:
        self._loaders[loader.source_type] = loader

    def get(self, source_type: SourceType) -> Loader:
        try:
            return self._loaders[source_type]
        except KeyError as exc:
            raise LoaderNotFoundError(
                f"No loader registered for source type '{source_type}'", source_type=source_type
            ) from exc


def default_registry() -> LoaderRegistry:
    """Wires up every MVP loader. Adding a new source means implementing a
    Loader and registering it here - nothing else changes."""
    registry = LoaderRegistry()
    registry.register(WebsiteLoader())
    registry.register(MarkdownLoader())
    registry.register(PlainTextLoader())
    registry.register(PdfLoader())
    registry.register(DocxLoader())
    registry.register(JsonLoader())
    return registry
