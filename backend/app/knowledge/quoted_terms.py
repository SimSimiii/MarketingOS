"""Literal commercial excerpts which must not depend on a model remembering them."""

import re

from app.ingestion.cleaners.code_regions import preserve_code
from app.knowledge.corpus import Document, collapse, fold
from app.knowledge.ledger import Evidence, EvidenceContext, EvidenceKind
from app.knowledge.taxonomy import FactCategory

_LINK = re.compile(r"\[([^\]\n]{12,300})\]\([^\)\n]+\)")


def with_question(quote: str, document: Document) -> str:
    """Keep an adjacent FAQ question with its answer, without rewriting either."""
    blocks = re.split(r"\n\s*\n", document.content)
    matches = [i for i, block in enumerate(blocks) if fold(quote) in fold(block)]
    if len(matches) != 1 or not matches[0]:
        return quote
    index = matches[0]
    question, answer = blocks[index - 1].strip(), blocks[index].strip()
    if not question.endswith("?") or len(question) > 240 or len(answer) > 1600:
        return quote
    return question + "\n\n" + answer


def retain_billing_links(document: Document, entries: list[Evidence]) -> None:
    """Retain quantified billing-link labels verbatim, including their conditions.

    This is quotation capture, not a price interpretation. Only pricing material,
    whole link-only lines, explicit billing periods and numeric offers qualify.
    Examples and prose comparisons are not billing offers.
    """
    if not re.search(r"\b(?:pricing|billing|plans?|tarifs?)\b", document.title, re.IGNORECASE):
        return

    def collect(prose: str) -> str:
        kept = 0
        for line in prose.splitlines():
            if not re.fullmatch(r"\s*(?:\[[^\]\n]+\]\([^\)\n]+\)\s*)+", line):
                continue
            for match in _LINK.finditer(line):
                label = match.group(1)
                if (kept >= 8 or not re.search(r"\b(?:get|save|receive)\b", label, re.IGNORECASE)
                        or not re.search(r"\b(?:annual\w*|yearly|monthly)\b", label, re.IGNORECASE)
                        or not re.search(r"\b\d+(?:[.,]\d+)?\s*(?:%|months?\s+free|free\s+months?)", label, re.IGNORECASE)):
                    continue
                if any(fold(label) in fold(entry.verbatim) for entry in entries):
                    continue
                entries.append(Evidence(
                    id=f"E{len(entries) + 1}", kind=EvidenceKind.PRICE,
                    claim=collapse(label), verbatim=match.group(0),
                    source=document.source, document_id=document.id,
                    category=FactCategory.COMMERCIAL,
                    context=EvidenceContext(subject=document.title, claim_scope="offer",
                        conditions=label, verification="quote_verified_in_material",
                        limitations="Literal billing offer; no eligibility or terms beyond this quotation established."),
                ))
                kept += 1
        return prose

    preserve_code(document.content, collect)
