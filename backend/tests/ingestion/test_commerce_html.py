from app.ingestion.cleaners.base import CleanerPipeline
from app.ingestion.loaders.html_extract import extract_content, extract_links
from app.ingestion.pipeline import default_cleaners


def test_product_forms_keep_price_delivery_scope_and_product_links():
    html = '''<main><h1>Travel bag</h1><form action="/cart/add">
    <p>Travel bag — €45</p><p>Estimated delivery in 3–5 days to France.</p>
    <input name="quantity" value="999"><button>Add to cart</button></form>
    <a href="/products/travel-bag"><img src="https://cdn.example.com/photo.jpg?long=123456"
     alt="Travel bag in blue" title="30L capacity"></a>
    <figure><img src="https://cdn.example.com/details.webp"><figcaption>Recycled fabric, hand wash only.</figcaption></figure></main>'''
    body = extract_content(html)[2]
    assert '€45' in body
    assert '3–5 days to France' in body
    assert '999' not in body
    assert 'Travel bag in blue' in body and '30L capacity' in body
    assert '/products/travel-bag' in body
    assert 'Recycled fabric, hand wash only.' in body
    assert 'cdn.example.com' not in body
    assert extract_links(html,'https://shop.example.com/') == ['https://shop.example.com/products/travel-bag']


def test_signup_offer_is_not_discarded_with_its_form_and_password_value_is_not_copy():
    html = '''<form action="/register"><h1>Start the Free plan</h1>
    <p>Free forever, no card required. Up to 2,000 contacts.</p>
    <input type="password" value="private-value"><button>Create account</button></form>
    <form action="/localization">COUNTRY PICKER NOISE</form>
    <form role="search" action="/">SEARCH CONTROL NOISE</form>'''
    body = extract_content(html)[2]
    assert '2,000 contacts' in body and 'no card required' in body
    assert 'Create account' in body
    assert 'private-value' not in body
    assert 'PICKER NOISE' not in body and 'CONTROL NOISE' not in body


def test_literal_image_code_and_linked_media_cta_are_preserved():
    html = '''<h1>Embed an image</h1><pre><code>&lt;img src="https://example.com/code.png" alt="Example"&gt;</code></pre>
    <p><code>&lt;img src="https://example.com/inline.png"&gt;</code></p>
    <a href="https://example.com/walkthrough.mp4">Watch the walkthrough</a>'''
    body = CleanerPipeline(default_cleaners()).apply(extract_content(html)[2])
    assert '<img src="https://example.com/code.png" alt="Example">' in body
    assert 'https://example.com/inline.png' in body
    assert '[Watch the walkthrough](https://example.com/walkthrough.mp4)' in body
