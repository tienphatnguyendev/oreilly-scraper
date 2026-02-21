"""TDD tests for browser.py — SOLO-28: Initialize Playwright Stealth & Authentication.

All Playwright objects are mocked so no live network calls are made.
"""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

# Import the module under test at the top level so patch() can find it.
import oreilly_scraper.browser as browser_module
from oreilly_scraper.browser import create_authenticated_page, _is_authenticated
from oreilly_scraper.settings import Settings, Cookie
from playwright_stealth import Stealth


# ---------------------------------------------------------------------------
# Helpers & Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def settings():
    """Minimal valid Settings object."""
    return Settings(
        book_url="https://learning.oreilly.com/library/view/test/1234567890/",
        cookies=[Cookie(name="orm", value="abc123", domain=".oreilly.com", path="/")],
        output_dir="/tmp/books",
    )


def make_mock_page(url: str):
    page = AsyncMock()
    page.url = url
    page.goto = AsyncMock()
    return page


def make_mock_context(page):
    context = AsyncMock()
    context.add_cookies = AsyncMock()
    context.new_page = AsyncMock(return_value=page)
    return context


def make_mock_browser(context):
    browser = AsyncMock()
    browser.new_context = AsyncMock(return_value=context)
    return browser


def make_mock_playwright(browser):
    """Build a mock async_playwright context manager."""
    p = MagicMock()
    p.__aenter__ = AsyncMock(return_value=p)
    p.__aexit__ = AsyncMock(return_value=False)
    p.chromium.launch = AsyncMock(return_value=browser)
    return p


# ---------------------------------------------------------------------------
# Unit tests for _is_authenticated
# ---------------------------------------------------------------------------

def test_is_authenticated_home():
    assert _is_authenticated("https://learning.oreilly.com/home/") is True


def test_is_authenticated_login():
    assert _is_authenticated("https://learning.oreilly.com/login/") is False


def test_is_authenticated_sign_in():
    assert _is_authenticated("https://learning.oreilly.com/sign-in/") is False


# ---------------------------------------------------------------------------
# Integration-style tests (Playwright fully mocked)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cookies_are_injected(settings):
    """Cookies from settings are injected into the browser context."""
    page = make_mock_page("https://learning.oreilly.com/home/")
    context = make_mock_context(page)
    browser = make_mock_browser(context)
    mock_pw = make_mock_playwright(browser)

    with patch.object(browser_module, "async_playwright", return_value=mock_pw), \
         patch.object(Stealth, "apply_stealth_async", new_callable=AsyncMock) as mock_stealth:
        await create_authenticated_page(settings)

    expected = [{"name": "orm", "value": "abc123", "domain": ".oreilly.com", "path": "/"}]
    context.add_cookies.assert_awaited_once_with(expected)


@pytest.mark.asyncio
async def test_stealth_is_applied(settings):
    """playwright-stealth is applied to the browser context."""
    page = make_mock_page("https://learning.oreilly.com/home/")
    context = make_mock_context(page)
    browser = make_mock_browser(context)
    mock_pw = make_mock_playwright(browser)

    with patch.object(browser_module, "async_playwright", return_value=mock_pw), \
         patch.object(Stealth, "apply_stealth_async", new_callable=AsyncMock) as mock_stealth:
        await create_authenticated_page(settings)

    mock_stealth.assert_awaited_once()


@pytest.mark.asyncio
async def test_valid_session_returns_page(settings):
    """When the final URL is the home page, the authenticated page is returned."""
    page = make_mock_page("https://learning.oreilly.com/home/")
    context = make_mock_context(page)
    browser = make_mock_browser(context)
    mock_pw = make_mock_playwright(browser)

    with patch.object(browser_module, "async_playwright", return_value=mock_pw), \
         patch.object(Stealth, "apply_stealth_async", new_callable=AsyncMock):
        result = await create_authenticated_page(settings)

    assert result is page


@pytest.mark.asyncio
async def test_invalid_session_prompts_and_retries(settings, tmp_path):
    """When the session is invalid, the user is prompted; on retry valid page is returned."""
    # Write a config.json for the reload path
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({
        "book_url": "https://learning.oreilly.com/library/view/test/1234567890/",
        "cookies": [{"name": "orm", "value": "newtoken", "domain": ".oreilly.com", "path": "/"}],
        "output_dir": str(tmp_path),
    }))

    page = AsyncMock()
    page.goto = AsyncMock()
    page.url = "https://learning.oreilly.com/login/"

    context = make_mock_context(page)
    browser = make_mock_browser(context)
    mock_pw = make_mock_playwright(browser)

    # Simulate URL changing to /home/ on the second goto call
    goto_call_count = 0

    async def fake_goto(url, **kwargs):
        nonlocal goto_call_count
        goto_call_count += 1
        page.url = (
            "https://learning.oreilly.com/login/"
            if goto_call_count == 1
            else "https://learning.oreilly.com/home/"
        )

    page.goto.side_effect = fake_goto

    input_calls = []

    with patch.object(browser_module, "async_playwright", return_value=mock_pw), \
         patch.object(Stealth, "apply_stealth_async", new_callable=AsyncMock), \
         patch("builtins.input", side_effect=lambda _="": input_calls.append(True) or ""):
        result = await create_authenticated_page(settings, config_path=str(config_file))

    assert result is page
    assert len(input_calls) == 1, "User should have been prompted exactly once"
    assert context.add_cookies.await_count == 2, "Cookies should be re-injected on retry"
