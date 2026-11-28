import json
import socket
import threading
import time
from collections.abc import Generator
from contextlib import suppress
from pathlib import Path
from typing import Any

import pytest
import uvicorn
from fastapi.testclient import TestClient
from playwright.async_api import Page, Route, async_playwright

from app.main import app

CHROME_CANDIDATES = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
)


def _find_chrome_executable() -> str | None:
    for candidate in CHROME_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    return None


class _NoSignalServer(uvicorn.Server):
    def install_signal_handlers(self) -> None:
        return None


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="module")
def live_dashboard_url() -> Generator[str, None, None]:
    port = _get_free_port()
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=port,
        lifespan="off",
        log_level="warning",
    )
    server = _NoSignalServer(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    deadline = time.monotonic() + 10.0
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.05)

    yield f"http://127.0.0.1:{port}"

    server.should_exit = True
    thread.join(timeout=5.0)


async def _set_streaming_enabled(page: Page, enabled: bool) -> None:
    await page.click("#chatgpt-dropdown-btn")
    toggle = page.locator("#chat-stream-toggle")
    if enabled:
        await toggle.check()
    else:
        await toggle.uncheck()
    await page.click("button:has-text('Apply & Close')")


async def _setup_authenticated_dashboard(page: Page, base_url: str) -> list[str]:
    page_errors: list[str] = []
    page.on("pageerror", lambda exc: page_errors.append(str(exc)))

    async def handle_collections(route: Route) -> None:
        await route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps([{"id": "col-1", "name": "QA Policies"}]),
        )

    async def handle_documents(route: Route) -> None:
        await route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"items": []}),
        )

    async def handle_analytics(route: Route) -> None:
        await route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "total_queries": 0,
                    "avg_groundedness": 0.0,
                    "abstention_rate": 0.0,
                    "cache_hit_rate": 0.0,
                    "p95_latency_ms": 0.0,
                }
            ),
        )

    await page.route("**/api/v1/collections", handle_collections)
    await page.route("**/api/v1/documents*", handle_documents)
    await page.route("**/api/v1/analytics/overview", handle_analytics)

    await page.add_init_script(
        """
        localStorage.setItem('ekip_token', 'test-jwt-token');
        localStorage.setItem('ekip_tenant', 'qa-tenant');
        localStorage.setItem('ekip_role', 'admin');
        """
    )
    await page.goto(f"{base_url}/dashboard", wait_until="domcontentloaded")
    await page.wait_for_function(
        "() => document.getElementById('chat-collection-select')?.options.length > 0"
    )
    return page_errors


def test_dashboard_html_and_compiled_css() -> None:
    client = TestClient(app)
    html_res = client.get("/dashboard")
    assert html_res.status_code == 200
    assert 'id="new-collection-btn"' in html_res.text
    assert "scrollToSourceCard" in html_res.text
    assert "extractApiErrorMessage" in html_res.text
    assert "renderAssistantError" in html_res.text
    assert "Abstained" in html_res.text
    assert "Not applicable" in html_res.text

    css_res = client.get("/static/css/dashboard.css")
    assert css_res.status_code == 200
    for utility in ("ring-brand-500", "bg-rose-50", "text-rose-800", "inline-flex"):
        assert utility in css_res.text


@pytest.mark.asyncio
async def test_browser_streamed_citations_and_clickable_scroll(
    live_dashboard_url: str,
) -> None:
    chrome_path = _find_chrome_executable()
    if chrome_path is None:
        pytest.skip("Chrome executable not installed")

    citations_payload: list[dict[str, Any]] = [
        {
            "source_id": 1,
            "document_id": "doc-1",
            "section_path": "Policy > Security",
            "snippet": "All tokens expire every 24 hours.",
            "relevance_score": 0.96,
        },
        {
            "source_id": 2,
            "document_id": "doc-1",
            "section_path": "Policy > Audits",
            "snippet": "Audit logs are retained for 365 days.",
            "relevance_score": 0.91,
        },
    ]
    sse_body = (
        f"event: sources\ndata: {json.dumps({'sources': citations_payload, 'cached': False})}\n\n"
        f"event: token\ndata: {json.dumps({'text': 'Tokens expire daily [1] '})}\n\n"
        f"event: token\ndata: {json.dumps({'text': 'and logs last one year [2].'})}\n\n"
        "event: done\n"
        f"data: {json.dumps({
            'query_id': 'q-stream-1',
            'cached': False,
            'citations': citations_payload,
            'groundedness_score': 0.85,
            'hallucination_warning': False,
            'abstained': False,
            'latency_ms': 42,
        })}\n\n"
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=chrome_path, headless=True)
        try:
            page = await browser.new_page(viewport={"width": 1440, "height": 900})
            page_errors = await _setup_authenticated_dashboard(page, live_dashboard_url)

            async def handle_stream(route: Route) -> None:
                await route.fulfill(
                    status=200,
                    content_type="text/event-stream",
                    body=sse_body,
                )

            await page.route("**/api/v1/query/stream", handle_stream)
            await page.fill("#chat-input", "What are token and log policies?")
            await page.click("#send-btn")

            await page.wait_for_selector("text=Verified Sources (2)")
            badge_text = await page.locator("[data-groundedness-badge]").last.inner_text()
            assert badge_text == "Grounded: 85%"

            assert await page.locator("a.citation-link[data-citation-ref='1']").count() == 1
            assert await page.locator("a.citation-link[data-citation-ref='2']").count() == 1
            assert await page.locator("[data-source-card]").count() == 2

            await page.locator("a.citation-link[data-citation-ref='2']").click()
            card_classes = await page.locator("[data-source-card='2']").get_attribute("class")
            assert card_classes is not None
            assert "ring-brand-500" in card_classes
            assert page_errors == []
        finally:
            await browser.close()


@pytest.mark.asyncio
async def test_browser_groundedness_abstained_and_not_applicable_badges(
    live_dashboard_url: str,
) -> None:
    chrome_path = _find_chrome_executable()
    if chrome_path is None:
        pytest.skip("Chrome executable not installed")

    abstention_sse = (
        f"event: sources\ndata: {json.dumps({'sources': [], 'cached': False})}\n\n"
        "event: abstention\n"
        f"data: {json.dumps({
            'message': 'I do not have enough information in the provided documents.',
            'abstained': True,
            'groundedness_score': None,
            'latency_ms': 18,
        })}\n\n"
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=chrome_path, headless=True)
        try:
            page = await browser.new_page(viewport={"width": 1440, "height": 900})
            page_errors = await _setup_authenticated_dashboard(page, live_dashboard_url)

            async def handle_stream(route: Route) -> None:
                await route.fulfill(
                    status=200,
                    content_type="text/event-stream",
                    body=abstention_sse,
                )

            async def handle_sync_query(route: Route) -> None:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(
                        {
                            "query_id": "q-zero-1",
                            "answer": "Okay.",
                            "citations": [],
                            "groundedness_score": None,
                            "hallucination_warning": False,
                            "abstained": False,
                            "latency_ms": 14,
                            "cached": False,
                        }
                    ),
                )

            await page.route("**/api/v1/query/stream", handle_stream)
            await page.route("**/api/v1/query", handle_sync_query)

            await page.fill("#chat-input", "Unrelated question")
            await page.click("#send-btn")
            await page.wait_for_selector("text=Abstained")
            assert await page.locator("[data-groundedness-badge]").last.inner_text() == "Abstained"
            chat_text = await page.locator("#chat-messages").inner_text()
            assert "Grounded: 100%" not in chat_text

            await _set_streaming_enabled(page, False)
            await page.fill("#chat-input", "Zero-claim ping")
            await page.click("#send-btn")
            await page.wait_for_selector("text=Not applicable")
            assert (
                await page.locator("[data-groundedness-badge]").last.inner_text()
                == "Not applicable"
            )
            chat_text_after = await page.locator("#chat-messages").inner_text()
            assert "Grounded: 100%" not in chat_text_after
            assert page_errors == []
        finally:
            await browser.close()


@pytest.mark.asyncio
async def test_browser_error_bubbles_for_429_and_server_errors(
    live_dashboard_url: str,
) -> None:
    chrome_path = _find_chrome_executable()
    if chrome_path is None:
        pytest.skip("Chrome executable not installed")

    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=chrome_path, headless=True)
        try:
            page = await browser.new_page(viewport={"width": 1440, "height": 900})
            page_errors = await _setup_authenticated_dashboard(page, live_dashboard_url)

            stream_calls = 0

            async def handle_stream(route: Route) -> None:
                nonlocal stream_calls
                stream_calls += 1
                if stream_calls == 1:
                    await route.fulfill(
                        status=429,
                        headers={"Retry-After": "58"},
                        content_type="application/json",
                        body=json.dumps({"detail": "Rate limit exceeded"}),
                    )
                else:
                    await route.fulfill(
                        status=500,
                        content_type="application/json",
                        body=json.dumps({"detail": "LLM gateway timeout"}),
                    )

            async def handle_sync_query(route: Route) -> None:
                await route.fulfill(
                    status=429,
                    headers={"Retry-After": "42"},
                    content_type="application/json",
                    body=json.dumps({"detail": "Too many requests"}),
                )

            await page.route("**/api/v1/query/stream", handle_stream)
            await page.route("**/api/v1/query", handle_sync_query)

            # 1. Streamed 429
            await page.fill("#chat-input", "Query 21 stream")
            await page.click("#send-btn")
            await page.wait_for_selector("text=Rate limit reached, try again in 58s.")

            # 2. Streamed 500
            await page.fill("#chat-input", "Query error stream")
            await page.click("#send-btn")
            await page.wait_for_selector("text=LLM gateway timeout")

            # 3. Non-streamed 429
            await _set_streaming_enabled(page, False)
            await page.fill("#chat-input", "Query 21 sync")
            await page.click("#send-btn")
            await page.wait_for_selector("text=Rate limit reached, try again in 42s.")

            chat_text = await page.locator("#chat-messages").inner_text()
            assert "HTTP 429: Rate limit reached, try again in 58s." in chat_text
            assert "HTTP 429: Rate limit reached, try again in 42s." in chat_text
            assert "Grounded: 100%" not in chat_text
            assert "Latency: 0ms" not in chat_text
            assert page_errors == []
        finally:
            await browser.close()


@pytest.mark.asyncio
async def test_browser_new_collection_button_mouse_click(
    live_dashboard_url: str,
) -> None:
    chrome_path = _find_chrome_executable()
    if chrome_path is None:
        pytest.skip("Chrome executable not installed")

    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=chrome_path, headless=True)
        try:
            page = await browser.new_page(viewport={"width": 1440, "height": 900})
            page_errors = await _setup_authenticated_dashboard(page, live_dashboard_url)

            # Open ChatGPT config dropdown first, then switch to Documents tab
            with suppress(Exception):
                await page.click("#chatgpt-dropdown-btn")

            await page.click("#tab-btn-documents")
            await page.locator("#new-collection-btn").click()

            modal_display = await page.eval_on_selector(
                "#collection-modal",
                "el => window.getComputedStyle(el).display",
            )
            assert modal_display == "flex"
            assert await page.locator("#collection-modal").is_visible()

            # Backdrop click closes modal
            await page.locator("#collection-modal").click(position={"x": 10, "y": 10})
            closed_display = await page.eval_on_selector(
                "#collection-modal",
                "el => window.getComputedStyle(el).display",
            )
            assert closed_display == "none"

            # Second direct mouse click reopens modal cleanly
            await page.locator("#new-collection-btn").click()
            reopened_display = await page.eval_on_selector(
                "#collection-modal",
                "el => window.getComputedStyle(el).display",
            )
            assert reopened_display == "flex"
            assert page_errors == []
        finally:
            await browser.close()
