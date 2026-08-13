import io

import httpx
import pytest

WEBSITE_HTML = """
<html>
<head>
  <title>My Page</title>
  <meta name="description" content="A test page about widgets">
</head>
<body>
  <nav><a href="/">Home</a><a href="/about">About</a></nav>
  <script>console.log("tracked");</script>
  <style>.hidden { display: none; }</style>
  <header>Site Header</header>
  <h1>Welcome</h1>
  <p>This is a <a href="https://example.com/docs">link</a> in a paragraph.</p>
  <h2>Features</h2>
  <ul><li>Item one</li><li>Item two</li></ul>
  <footer>Copyright 2026</footer>
</body>
</html>
"""


def make_mock_client(html: str = WEBSITE_HTML, status_code: int = 200) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, text=html)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.fixture
def mock_website_client() -> httpx.AsyncClient:
    return make_mock_client()


def build_minimal_pdf(text: bytes) -> bytes:
    """Hand-rolls a minimal, valid single-page PDF containing `text`, since no
    PDF-writing library (reportlab/fpdf) is a project dependency. Uses a
    proper xref table so pypdf parses it without falling back to recovery."""
    content_stream = b"BT /F1 24 Tf 10 100 Td (" + text + b") Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(content_stream)).encode() + b" >>\nstream\n" + content_stream + b"\nendstream",
    ]

    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(out.tell())
        out.write(str(i).encode() + b" 0 obj\n" + obj + b"\nendobj\n")

    xref_offset = out.tell()
    out.write(b"xref\n0 " + str(len(objects) + 1).encode() + b"\n")
    out.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        out.write(f"{offset:010d} 00000 n \n".encode())
    out.write(
        b"trailer\n<< /Size "
        + str(len(objects) + 1).encode()
        + b" /Root 1 0 R >>\nstartxref\n"
        + str(xref_offset).encode()
        + b"\n%%EOF"
    )
    return out.getvalue()
