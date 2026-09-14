"""Disposable extraction process. No database or model access."""
import json
import sys
from pathlib import Path
from zipfile import ZipFile

MAX_CHARS = 1_000_000


def extract(kind: str, source: str) -> dict:
    if Path(source).stat().st_size > 20 * 1024 * 1024:
        raise ValueError("Document exceeds 20 MB")
    if kind == "pdf":
        from pypdf import PdfReader
        reader = PdfReader(source)
        if reader.is_encrypted:
            raise ValueError("Encrypted PDFs are not supported")
        if len(reader.pages) > 200:
            raise ValueError("PDF exceeds the 200 page limit")
        pages, size = [], 0
        for page in reader.pages:
            text = page.extract_text() or ""
            size += len(text)
            if size > MAX_CHARS:
                raise ValueError("Extracted document exceeds the text limit")
            pages.append(text.strip())
        meta = reader.metadata or {}
        return {"content": "\n\n".join(p for p in pages if p), "metadata": {
            "title": str(meta.get("/Title") or "").strip(),
            "author": str(meta.get("/Author") or "").strip(), "page_count": len(reader.pages),
        }}
    from docx import Document
    from docx.table import Table
    with ZipFile(source) as archive:
        entries = archive.infolist()
        if len(entries) > 2000 or sum(e.file_size for e in entries) > 50_000_000:
            raise ValueError("DOCX archive exceeds the decompression limit")
    document = Document(source)
    lines, size = [], 0
    for block in document.iter_inner_content():
        if isinstance(block, Table):
            text = "\n".join(" | ".join(cell.text.strip() for cell in row.cells) for row in block.rows)
        else:
            text = block.text.strip()
            style = block.style.name if block.style else ""
            if style.startswith("Heading") and text:
                level = min(6, int("".join(ch for ch in style if ch.isdigit()) or "1"))
                text = f"{'#' * level} {text}"
        size += len(text)
        if size > MAX_CHARS:
            raise ValueError("Extracted document exceeds the text limit")
        if text:
            lines.append(text)
    return {"content": "\n\n".join(lines), "metadata": {
        "title": (document.core_properties.title or "").strip(),
        "author": (document.core_properties.author or "").strip(),
    }}


if __name__ == "__main__":
    try:
        from app.ingestion.process_limits import limit_memory
        limit_memory()
        print(json.dumps(extract(sys.argv[1], sys.argv[2])))
    except Exception as exc:  # noqa: BLE001 - serialize parser failures across the process boundary
        print(json.dumps({"error": str(exc)}))
        sys.exit(1)
