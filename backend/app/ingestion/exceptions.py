from typing import Any


class IngestionError(Exception):
    """Base for every error the ingestion engine raises. Carries structured
    debugging context, same convention as app.runtime.exceptions."""

    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(message)
        self.message = message
        self.details = details

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.message!r}, details={self.details!r})"


class LoaderNotFoundError(IngestionError):
    """Raised when no loader is registered for a requested source type."""


class LoaderError(IngestionError):
    """Raised when a loader fails to fetch or parse its source."""


class DuplicateDocumentError(IngestionError):
    """Raised by a KnowledgeStore when a document with the same content hash
    already exists. `details['existing_id']` carries the stored document's id."""


class DocumentNotFoundError(IngestionError):
    """Raised when a requested document id doesn't exist in the store."""


class AssetNotFoundError(IngestionError):
    """Raised when a requested asset id doesn't exist in the asset store."""


class AnalyzerNotFoundError(IngestionError):
    """Raised when no Analyzer is registered for a requested source type -
    e.g. video/audio, which are architecture-only in this phase."""


class AnalysisError(IngestionError):
    """Raised when an Analyzer or the providers it depends on (Vision/OCR)
    fail to produce a result."""
