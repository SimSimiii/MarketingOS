import pytest
from docx import Document as DocxDocument

from app.ingestion.documents import SourceType
from app.ingestion.exceptions import LoaderError
from app.ingestion.loaders.docx_loader import DocxLoader
from app.ingestion.loaders.json_loader import JsonLoader
from app.ingestion.loaders.markdown_loader import MarkdownLoader
from app.ingestion.loaders.text_loader import PlainTextLoader


@pytest.mark.asyncio
async def test_markdown_loader_accepts_raw_text():
    raw = await MarkdownLoader().load("# Title\n\nBody text.")
    assert raw.source_type == SourceType.MARKDOWN
    assert raw.content == "# Title\n\nBody text."


@pytest.mark.asyncio
async def test_markdown_loader_reads_from_file(tmp_path):
    path = tmp_path / "doc.md"
    path.write_text("# From file\n", encoding="utf-8")
    raw = await MarkdownLoader().load(str(path), is_path=True)
    assert raw.content == "# From file"


@pytest.mark.asyncio
async def test_plain_text_loader_accepts_raw_text():
    raw = await PlainTextLoader().load("just some text")
    assert raw.source_type == SourceType.PLAIN_TEXT
    assert raw.content == "just some text"


@pytest.mark.asyncio
async def test_json_loader_pretty_prints_raw_json():
    raw = await JsonLoader().load('{"a": 1, "b": [2, 3]}')
    assert raw.source_type == SourceType.JSON
    assert '"a": 1' in raw.content


@pytest.mark.asyncio
async def test_json_loader_reads_from_file(tmp_path):
    path = tmp_path / "data.json"
    path.write_text('{"key": "value"}', encoding="utf-8")
    raw = await JsonLoader().load(str(path), is_path=True)
    assert '"key": "value"' in raw.content


@pytest.mark.asyncio
async def test_json_loader_invalid_json_raises_loader_error():
    with pytest.raises(LoaderError):
        await JsonLoader().load("{not valid json")


@pytest.mark.asyncio
async def test_docx_loader_extracts_headings_and_paragraphs(tmp_path):
    path = tmp_path / "doc.docx"
    document = DocxDocument()
    document.add_heading("My Heading", level=1)
    document.add_paragraph("A regular paragraph.")
    document.save(str(path))

    raw = await DocxLoader().load(str(path), is_path=True)

    assert raw.source_type == SourceType.DOCX
    assert "# My Heading" in raw.content
    assert "A regular paragraph." in raw.content


@pytest.mark.asyncio
async def test_docx_loader_missing_file_raises_loader_error(tmp_path):
    with pytest.raises(LoaderError):
        await DocxLoader().load(str(tmp_path / "missing.docx"), is_path=True)


@pytest.mark.asyncio
async def test_pasted_text_naming_a_real_file_is_kept_as_text(tmp_path):
    """The ingestion form's "paste your text" field reaches these loaders as
    `source`. They used to ask the filesystem whether that string happened to
    name a file and read it if so, which turns the field into "read this path
    off the server" - a secret in `.env` is one paste away. A path is only a
    path when the caller says so."""
    secret = tmp_path / "secret.txt"
    secret.write_text("SUPER_SECRET=hunter2", encoding="utf-8")

    raw = await PlainTextLoader().load(str(secret))

    assert raw.content == str(secret)
    assert "hunter2" not in raw.content


@pytest.mark.asyncio
async def test_markdown_pasted_text_naming_a_real_file_is_kept_as_text(tmp_path):
    secret = tmp_path / "secret.md"
    secret.write_text("# leaked", encoding="utf-8")

    raw = await MarkdownLoader().load(str(secret))

    assert raw.content == str(secret)
    assert "leaked" not in raw.content


@pytest.mark.asyncio
async def test_a_binary_loader_refuses_a_path_it_was_not_handed_deliberately(tmp_path):
    """PDF and DOCX have no text form, so an unvouched path is never a
    mistake - it is the same read-my-file request wearing an extension."""
    path = tmp_path / "doc.docx"
    document = DocxDocument()
    document.add_paragraph("Confidential.")
    document.save(str(path))

    with pytest.raises(LoaderError, match="uploaded as a file"):
        await DocxLoader().load(str(path))
