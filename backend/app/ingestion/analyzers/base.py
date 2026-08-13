from abc import ABC, abstractmethod
from typing import ClassVar

from pydantic import BaseModel

from app.ingestion.assets.base import Asset
from app.ingestion.documents import KnowledgeDocument, SourceType


class BaseAnalyzer(ABC):
    """Turns an Asset (plus its raw bytes, provided for this single call
    only) into one or more KnowledgeDocuments. Every dependency an analyzer
    needs (VisionProvider, OCRProvider, ...) is constructor-injected - an
    analyzer never instantiates its own providers."""

    supported_asset_types: ClassVar[set[SourceType]]
    output_schema: ClassVar[type[BaseModel]]

    @abstractmethod
    async def analyze(self, asset: Asset, content: bytes) -> list[KnowledgeDocument]:
        raise NotImplementedError
