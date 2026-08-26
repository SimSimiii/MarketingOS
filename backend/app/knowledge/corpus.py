"""Everything the user handed over, in a shape you can actually ask questions of.

What this replaces: a loop that took documents newest-first, cut each at four
thousand characters, stopped at twenty-four thousand overall, and pasted the
result into every prompt in the run. Under that scheme a pricing table in the
second half of a long page was not merely deprioritized - it could not reach a
model on any code path, ever, no matter what the campaign needed.

Retrieval replaces truncation. Documents are split into sections small enough
to be individually relevant, and a caller asks for what it needs. The scorer
is lexical on purpose: one business's material is tens of documents, not
millions, and the failure mode of a keyword search over that (missing a
synonym) is corrected by the compiler reading a broad digest first. Embeddings
plug in behind `search` when the corpus outgrows this - the callers do not
change.
"""

import math
import re
from collections import Counter
from dataclasses import dataclass, field

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
_PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n")
_WORD_RE = re.compile(r"[a-z0-9][a-z0-9'\-]+")
_WHITESPACE_RE = re.compile(r"\s+")

#: A section longer than this is packed into several chunks. A heading-only
#: split leaves single-heading pages as one indivisible blob, which is the
#: same "all or nothing" problem retrieval exists to remove.
_MAX_CHUNK_CHARS = 1400
#: Below this a section is folded into its neighbour rather than standing as
#: its own result - a two-line chunk wins searches it cannot answer.
_MIN_CHUNK_CHARS = 120

_STOP_WORDS = frozenset(
    (
        "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
        "has", "have", "how", "if", "in", "into", "is", "it", "its", "of", "on",
        "or", "our", "that", "the", "their", "this", "to", "us", "was", "we",
        "were", "what", "when", "where", "which", "who", "will", "with", "you", "your",
    )
)


@dataclass(frozen=True)
class Chunk:
    """One retrievable slice of one document."""

    document_id: str
    document_title: str
    source: str
    index: int
    content: str
    heading: str = ""

    def render(self) -> str:
        where = f"{self.document_title}" + (f" › {self.heading}" if self.heading else "")
        return f"[{where}]\n{self.content}"


@dataclass(frozen=True)
class Document:
    """A source as the corpus sees it - identity, provenance, and its text."""

    id: str
    title: str
    content: str
    source: str = ""
    source_type: str = ""

    def render(self, limit: int | None = None) -> str:
        body = self.content if limit is None else self.content[:limit]
        origin = f" ({self.source})" if self.source else ""
        return f"### {self.title}{origin}\n{body}"


def _tokenize(text: str) -> list[str]:
    return [word for word in _WORD_RE.findall(text.lower()) if word not in _STOP_WORDS]


def split_document(document: Document) -> list[Chunk]:
    """Heading sections first, then packed paragraphs inside any section too
    long to be one answer."""
    sections: list[tuple[str, list[str]]] = []
    heading = ""
    lines: list[str] = []

    for line in document.content.splitlines():
        match = _HEADING_RE.match(line.strip())
        if match is None:
            lines.append(line)
            continue
        if any(existing.strip() for existing in lines):
            sections.append((heading, lines))
        heading = match.group(2).strip()
        lines = [line]
    if any(existing.strip() for existing in lines):
        sections.append((heading, lines))

    chunks: list[Chunk] = []
    for section_heading, section_lines in sections:
        body = "\n".join(section_lines).strip()
        if not body:
            continue
        for piece in _pack(body):
            if len(piece) < _MIN_CHUNK_CHARS and chunks and chunks[-1].heading == section_heading:
                merged = chunks.pop()
                piece = f"{merged.content}\n\n{piece}"
            chunks.append(
                Chunk(
                    document_id=document.id,
                    document_title=document.title,
                    source=document.source,
                    index=len(chunks),
                    content=piece,
                    heading=section_heading,
                )
            )
    return chunks


def _pack(body: str) -> list[str]:
    if len(body) <= _MAX_CHUNK_CHARS:
        return [body]
    pieces: list[str] = []
    current: list[str] = []
    size = 0
    for paragraph in _PARAGRAPH_SPLIT_RE.split(body):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if size and size + len(paragraph) > _MAX_CHUNK_CHARS:
            pieces.append("\n\n".join(current))
            current, size = [], 0
        current.append(paragraph)
        size += len(paragraph) + 2
    if current:
        pieces.append("\n\n".join(current))
    return pieces


@dataclass
class SourceCorpus:
    """The user's material, chunked and searchable."""

    documents: list[Document] = field(default_factory=list)
    chunks: list[Chunk] = field(default_factory=list)
    _document_frequency: Counter[str] = field(default_factory=Counter, repr=False)

    @classmethod
    def from_documents(cls, documents: list[Document]) -> "SourceCorpus":
        chunks = [chunk for document in documents for chunk in split_document(document)]
        frequency: Counter[str] = Counter()
        for chunk in chunks:
            frequency.update(set(_tokenize(chunk.content)))
        return cls(documents=documents, chunks=chunks, _document_frequency=frequency)

    @property
    def is_empty(self) -> bool:
        return not self.chunks

    @property
    def text(self) -> str:
        """Every word the user gave us, for the checks that must not miss a
        true detail just because retrieval did not surface it."""
        return "\n\n".join(document.content for document in self.documents)

    def search(self, query: str, limit: int = 6) -> list[Chunk]:
        """Chunks most likely to answer `query`, best first.

        Rare terms count for more than common ones (a chunk containing
        "SOC2" beats one that merely says "security" eight times), and length
        is normalized so a long page cannot win on volume alone.
        """
        terms = _tokenize(query)
        if not terms or not self.chunks:
            return []
        total = len(self.chunks)
        scored: list[tuple[float, int, Chunk]] = []
        for chunk in self.chunks:
            counts = Counter(_tokenize(chunk.content))
            if not counts:
                continue
            score = 0.0
            for term in set(terms):
                occurrences = counts.get(term, 0)
                if not occurrences:
                    continue
                idf = math.log(1 + total / (1 + self._document_frequency[term]))
                score += idf * (1 + math.log(occurrences))
            if score > 0:
                scored.append((score / math.sqrt(sum(counts.values())), chunk.index, chunk))
        scored.sort(key=lambda item: (-item[0], item[1]))
        return [chunk for _, _, chunk in scored[:limit]]

    def render_search(self, query: str, limit: int = 6) -> str:
        hits = self.search(query, limit)
        return "\n\n".join(hit.render() for hit in hits) or "Nothing in the material matches."

    def digest(self, budget_chars: int = 40_000) -> str:
        """A broad read of everything, for the compiler's first pass.

        Every document gets a share of the budget rather than the first few
        consuming it, because the whole point of compiling is to have looked
        at all of it once. Documents are read whole where they fit.
        """
        if not self.documents:
            return "The user provided no material."
        share = max(1_000, budget_chars // len(self.documents))
        parts: list[str] = []
        spent = 0
        for document in sorted(self.documents, key=lambda item: len(item.content)):
            remaining = budget_chars - spent
            if remaining <= 0:
                parts.append(f"### {document.title}\n(not read - budget exhausted)")
                continue
            allowance = min(share, remaining)
            body = document.content
            truncated = len(body) > allowance
            rendered = document.render(limit=allowance if truncated else None)
            if truncated:
                rendered += f"\n… ({len(body) - allowance:,} more characters not shown)"
            parts.append(rendered)
            spent += len(rendered)
        return "\n\n".join(parts)

    def documents_of_type(self, *source_types: str) -> list[Document]:
        return [document for document in self.documents if document.source_type in source_types]


def collapse(text: str, limit: int | None = None) -> str:
    flat = _WHITESPACE_RE.sub(" ", text).strip()
    if limit is not None and len(flat) > limit:
        return flat[:limit].rstrip() + "…"
    return flat


#: Typography a CMS applies and a model does not reproduce.
#:
#: Every published web page has been through something that turns "it's" into
#: "it’s" and "5-10" into "5–10". A model asked to quote that page back
#: answers in plain ASCII roughly as often as not - it is a different
#: character, and every comparison in this system that matches a quotation
#: against its source is an exact substring test.
#:
#: Both sides of every such test are folded through this. Nothing *stored* is
#: folded: the verbatim a user reads and a writer is shown keeps the
#: typography the company actually publishes.
_PUNCTUATION_FOLD = str.maketrans(
    {
        "“": '"', "”": '"', "„": '"', "‟": '"',
        "«": '"', "»": '"', "″": '"',
        "‘": "'", "’": "'", "‚": "'", "‛": "'", "′": "'",
        "–": "-", "—": "-", "‒": "-", "―": "-", "−": "-",
        "­": "",
    }
)


def fold(text: str, limit: int | None = None) -> str:
    """`collapse`, plus typography folded away and case dropped.

    The form to compare two pieces of text in when the question is "did this
    sentence come from that page". Never the form to store or display: a
    verbatim quotation is evidence, and evidence that has been rewritten -
    even only its punctuation - is not verbatim any more.
    """
    return collapse(text.translate(_PUNCTUATION_FOLD).replace("…", "..."), limit).lower()
