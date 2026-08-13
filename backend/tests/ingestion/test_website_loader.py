import pytest

from app.ingestion.documents import SourceType
from app.ingestion.exceptions import LoaderError
from app.ingestion.loaders.website_loader import WebsiteLoader
from tests.ingestion.conftest import make_mock_client


@pytest.mark.asyncio
async def test_loads_and_converts_to_markdown(mock_website_client):
    loader = WebsiteLoader(client=mock_website_client)
    raw = await loader.load("https://example.com")

    assert raw.source_type == SourceType.WEBSITE
    assert raw.source == "https://example.com"
    assert "# Welcome" in raw.content
    assert "## Features" in raw.content


@pytest.mark.asyncio
async def test_strips_nav_scripts_styles_header_footer(mock_website_client):
    loader = WebsiteLoader(client=mock_website_client)
    raw = await loader.load("https://example.com")

    assert "console.log" not in raw.content
    assert "display: none" not in raw.content
    assert "Site Header" not in raw.content
    assert "Copyright 2026" not in raw.content
    assert "Home" not in raw.content  # nav link text


@pytest.mark.asyncio
async def test_preserves_links_and_lists(mock_website_client):
    loader = WebsiteLoader(client=mock_website_client)
    raw = await loader.load("https://example.com")

    assert "[link](https://example.com/docs)" in raw.content
    assert "Item one" in raw.content
    assert "-" in raw.content  # bullet marker present


@pytest.mark.asyncio
async def test_extracts_title_and_description_metadata(mock_website_client):
    loader = WebsiteLoader(client=mock_website_client)
    raw = await loader.load("https://example.com")

    assert raw.metadata["title"] == "My Page"
    assert raw.metadata["description"] == "A test page about widgets"


@pytest.mark.asyncio
async def test_http_error_raises_loader_error():
    client = make_mock_client(status_code=500)
    loader = WebsiteLoader(client=client)

    with pytest.raises(LoaderError):
        await loader.load("https://example.com")


@pytest.mark.asyncio
async def test_never_calls_an_llm_or_summarizes(mock_website_client):
    # The output should just be the structural Markdown transform of the
    # original content - nothing shorter/rewritten, no summary sentence.
    loader = WebsiteLoader(client=mock_website_client)
    raw = await loader.load("https://example.com")

    assert "This is a" in raw.content  # original paragraph text intact, verbatim
