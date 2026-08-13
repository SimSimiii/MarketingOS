from app.ingestion.chunkers.base import Chunker
from app.ingestion.documents import Chunk, KnowledgeDocument


class FixedSizeChunker(Chunker):
    """Splits content into fixed-size character windows with overlap."""

    def __init__(self, chunk_size: int = 1000, overlap: int = 100) -> None:
        if overlap >= chunk_size:
            raise ValueError("overlap must be smaller than chunk_size")
        self._chunk_size = chunk_size
        self._overlap = overlap

    def chunk(self, document: KnowledgeDocument) -> list[Chunk]:
        content = document.content
        if not content:
            return []

        step = self._chunk_size - self._overlap
        chunks: list[Chunk] = []
        index = 0
        start = 0
        while start < len(content):
            piece = content[start : start + self._chunk_size].strip()
            if piece:
                chunks.append(
                    Chunk(
                        document_id=document.id,
                        index=index,
                        content=piece,
                        metadata={**document.metadata, "chunk_index": index},
                    )
                )
                index += 1
            start += step

        return chunks
