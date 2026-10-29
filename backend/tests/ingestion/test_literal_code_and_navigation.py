import pytest

from app.ingestion.cleaners.base import CleanerPipeline
from app.ingestion.loaders.html_extract import extract_content
from app.ingestion.pipeline import default_cleaners


@pytest.mark.parametrize("fence,closing", [("```", "```"), ("~~~", "~~~~"), ("````", "`````"), ("```", "")])
def test_the_complete_cleaner_chain_preserves_code_exactly(fence, closing):
    code = f'{fence}html\n<script src="https://example.com/script.js"></script>\n#  literal\nrepeat\nrepeat\n\n\n\n{closing}'
    result = CleanerPipeline(default_cleaners()).apply(f"<p>Setup</p>\n\n{code}")
    assert code in result
    assert "<p>" not in result


def test_inline_markup_and_script_examples_survive_extraction_and_cleaning():
    html = '<main><h1>Embed</h1><p>Paste into <code>&lt;head&gt;</code>.</p><pre><code>&lt;script src="https://example.com/a.js"&gt;&lt;/script&gt;</code></pre></main>'
    text = CleanerPipeline(default_cleaners()).apply(extract_content(html)[2])
    assert '`<head>`' in text
    assert '<script src="https://example.com/a.js"></script>' in text


def test_main_content_avoids_global_menus_but_keeps_offer_hero():
    html = '<header><h1>Product</h1><p>From $19/year, paid features only.</p></header>'
    html += '<div role="navigation">Account menu</div><aside>'
    html += ''.join(f'<a href="/{i}">Menu entry {i}</a>' for i in range(12))
    html += '</aside><main><h2>Guide</h2><p>' + 'Install the integration carefully. ' * 12 + '</p></main>'
    result = extract_content(html)[2]
    assert '$19/year' in result
    assert 'Install the integration' in result
    assert 'Menu entry' not in result
    assert 'Account menu' not in result
