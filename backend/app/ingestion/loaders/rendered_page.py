"""Optional, bounded rendering of incomplete public pages. No model calls.

The browser never sends requests directly: GET resources are fulfilled through
public_http, retaining public-address pinning and redirect/body limits. A fresh
context supplies no operator cookies or account state. Missing browser support
leaves the caller's explicit source-coverage warning intact.
"""

import asyncio
import logging
import re
import sys
from urllib.parse import urldefrag

from app.ai._win_loop import _needs_proactor_thread, _ProactorLoopThread
from app.core.public_http import fetch_render_resource, public_client, public_host
from app.ingestion.exceptions import LoaderError
from app.ingestion.loaders.html_extract import extract_content, within_source_site
from app.ingestion.loaders.public_content import content_issues

logger = logging.getLogger("marketingos.ingestion")
_SLOTS = asyncio.Semaphore(1)
_MAX_REQUESTS = 32
_MAX_ACCEPTED_BYTES = 20_000_000


def _values_loaded(original: str, body: str) -> bool:
    if "dynamic_values_missing" not in content_issues(original):
        return True
    # Hydration can remove placeholders before it fills the price widgets.
    return len(re.findall(r"\b\d+\b", body)) >= len(re.findall(r"\b\d+\b", original)) + 3


class RenderGateway:
    """Read-only request admission, independently testable without Chromium."""

    def __init__(self, client, url: str, initial_html: str):
        self.client = client
        self.url = urldefrag(url)[0]
        self.initial_html = initial_html
        self.requests = 0
        self.accepted_bytes = 0

    async def handle(self, route) -> None:
        request = route.request
        try:
            public_host(request.url)
            if request.method != "GET":
                logger.info("Render request blocked: %s %s", request.method, request.url.partition("?")[0])
                await route.abort()
                return
            if request.resource_type in {"image", "media", "font", "websocket", "other"}:
                await route.abort()
                return
            self.requests += 1
            if self.requests > _MAX_REQUESTS:
                logger.info("Render request budget reached: %s", request.url.partition("?")[0])
                await route.abort()
                return
            if request.resource_type == "document":
                if urldefrag(request.url)[0] != self.url:
                    await route.abort()
                    return
                await route.fulfill(status=200, content_type="text/html", body=self.initial_html)
                return
            response = await fetch_render_resource(self.client, request.url)
            self.accepted_bytes += len(response.content)
            if self.accepted_bytes > _MAX_ACCEPTED_BYTES:
                await route.abort()
                return
            headers = {key: value for key, value in response.headers.items()
                       if key.lower() not in {"content-length", "content-encoding", "transfer-encoding", "connection", "set-cookie"}}
            await route.fulfill(status=response.status_code, headers=headers, body=response.content)
        except LoaderError as exc:
            logger.info("Render resource unavailable: %s (%s)", request.url, str(exc)[:160])
            await route.abort()


_VISIBLE_HTML = """() => {
  let count = 0;
  function copy(node) {
    if (++count > 20000) return '';
    if (node.nodeType === Node.TEXT_NODE) {
      const span = document.createElement('span'); span.textContent = node.textContent;
      return span.innerHTML;
    }
    if (node.nodeType !== Node.ELEMENT_NODE) return '';
    const name = node.tagName.toLowerCase();
    if (['script','style','noscript','iframe','object','embed','svg','canvas','input','textarea'].includes(name)) return '';
    const style = getComputedStyle(node);
    if (node.hidden || node.getAttribute('aria-hidden') === 'true' || style.display === 'none' || style.visibility === 'hidden') return '';
    // Reading a web component must not instantiate another copy of it.
    const clone = document.createElement(name.includes('-') ? 'div' : name);
    if (name === 'a' && node.href) clone.setAttribute('href', node.href);
    if (name === 'img' && node.alt) clone.setAttribute('alt', node.alt);
    const children = name === 'slot' ? node.assignedNodes({flatten:true})
      : node.shadowRoot ? node.shadowRoot.childNodes : node.childNodes;
    clone.innerHTML = Array.from(children).map(copy).join('');
    return clone.outerHTML;
  }
  const title = document.createElement('title'); title.textContent = document.title;
  return '<html><head>' + title.outerHTML + '</head>' + copy(document.body) + '</html>';
}"""


async def _render(url: str, initial_html: str) -> str | None:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return None
    async with _SLOTS, asyncio.timeout(35), public_client() as client, async_playwright() as driver:
        browser = await driver.chromium.launch(
            channel="msedge" if sys.platform == "win32" else None, headless=True,
            chromium_sandbox=True,
        )
        try:
            context = await browser.new_context(service_workers="block", accept_downloads=False)
            await context.add_init_script("""for (const key of ['RTCPeerConnection','webkitRTCPeerConnection','WebTransport','Worker','SharedWorker']) {
                try { Object.defineProperty(window, key, {value: undefined, configurable: false}); } catch (_) {}
            }""")
            async def close_socket(socket):
                await socket.close()
            await context.route_web_socket("**/*", close_socket)
            gateway = RenderGateway(client, url, initial_html)
            await context.route("**/*", gateway.handle)
            page = await context.new_page()
            page.on("pageerror", lambda error: logger.info("Public page script error: %s", str(error)[:200]))
            await page.goto(url, wait_until="domcontentloaded", timeout=20_000)
            # No interaction or form submission. Allow bounded hydration, and
            # stop as soon as the missing values have actually appeared.
            latest = ""
            original = extract_content(initial_html)[2]
            original_numbers = len(re.findall(r"\b\d+\b", original))
            previous_body = ""
            stable_samples = 0
            for _ in range(24):
                latest = await page.evaluate(_VISIBLE_HTML)
                if len(latest) > 1_000_000 or not within_source_site(page.url, url):
                    return None
                body = extract_content(latest)[2]
                stable_samples = stable_samples + 1 if body == previous_body else 0
                previous_body = body
                values_loaded = _values_loaded(original, body)
                if len(body) >= 200 and not content_issues(body) and values_loaded and stable_samples >= 2:
                    return latest
                await page.wait_for_timeout(500)
            logger.info("Rendered source incomplete: requests=%d bytes=%d original_numbers=%d actual_numbers=%d",
                        gateway.requests, gateway.accepted_bytes, original_numbers,
                        len(re.findall(r"\b\d+\b", previous_body)))
            return None
        finally:
            await browser.close()


async def render_public_html(url: str, initial_html: str) -> str | None:
    public_host(url)
    # A browser is not a fallback for authentication, a bot challenge or a
    # publication's access restriction.
    if any(term in initial_html.lower() for term in (
        "verify you are human", "access denied", "sign in to read", "subscribe to continue",
        "prove your humanity", "js_challenge", "blocked by network security",
    )):
        return None
    try:
        from playwright.async_api import Error as BrowserError
    except ImportError:
        return None
    try:
        if _needs_proactor_thread():
            return await _ProactorLoopThread.instance().run(lambda: _render(url, initial_html))
        return await _render(url, initial_html)
    except (BrowserError, TimeoutError, OSError, NotImplementedError) as exc:
        logger.info("Public page rendering unavailable for %s (%s)", url, str(exc)[:180])
        return None
