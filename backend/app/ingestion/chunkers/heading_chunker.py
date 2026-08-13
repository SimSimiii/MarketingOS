import re

from app.ingestion.chunkers.base import Chunker
from app.ingestion.documents import Chunk, KnowledgeDocument

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")


class HeadingChunker(Chunker):
    """Splits Markdown content at heading boundaries - one chunk per section.
    Content before the first heading (if any) becomes its own chunk. Sections
    are not recursively re-split by size in this MVP."""

    def chunk(self, document: KnowledgeDocument) -> list[Chunk]:
        lines = document.content.split("\n")
        sections: list[tuple[str | None, list[str]]] = []
        current_heading: str | None = None
        current_lines: list[str] = []

        for line in lines:
            match = _HEADING_RE.match(line.strip())
            if match:
                if current_lines:
                    sections.append((current_heading, current_lines))
                current_heading = match.group(2).strip()
                current_lines = [line]
            else:
                current_lines.append(line)
        if current_lines:
            sections.append((current_heading, current_lines))

        chunks: list[Chunk] = []
        index = 0
        for heading, section_lines in sections:
            content = "\n".join(section_lines).strip()
            if not content:
                continue
            metadata = {**document.metadata, "chunk_index": index}
            if heading:
                metadata["heading"] = heading
            chunks.append(Chunk(document_id=document.id, index=index, content=content, metadata=metadata))
            index += 1

        return chunks
