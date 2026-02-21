"""browser.py — SOLO-28: Initialize Playwright Stealth & Authentication.

Public API:
    async create_authenticated_page(settings, config_path="config.json") -> Page

Flow:
    1. Launch headless Chromium.
    2. Apply playwright-stealth to the browser context.
    3. Inject cookies from settings.cookies.
    4. Navigate to https://learning.oreilly.com/home/ and check for a login redirect.
       - Authenticated  → return the Page object.
       - Not authenticated → print a warning, prompt user to update config.json, reload
         and retry (loops until valid).
"""

from playwright.async_api import async_playwright, BrowserContext, Page
from playwright_stealth import Stealth
from rich.console import Console

from .settings import load_config, Settings

console = Console()

AUTH_URL = "https://learning.oreilly.com/home/"
_LOGIN_INDICATORS = ("/login", "/sign-in", "/accounts/login")


def _is_authenticated(url: str) -> bool:
    """Return True if the final URL does NOT look like a login redirect."""
    return not any(indicator in url for indicator in _LOGIN_INDICATORS)


async def create_authenticated_page(
    settings: Settings,
    config_path: str = "config.json",
) -> Page:
    """Launch a stealth Playwright browser, inject cookies, and validate the session.

    Args:
        settings: Loaded Settings object (provides initial cookies).
        config_path: Path to config.json, used when the user updates cookies and retries.

    Returns:
        An authenticated Playwright Page ready for scraping.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        await Stealth().apply_stealth_async(context)
        page = await context.new_page()

        current_settings = settings

        while True:
            # Inject / re-inject cookies on every attempt
            cookies = [c.model_dump() for c in current_settings.cookies]
            await context.add_cookies(cookies)

            await page.goto(AUTH_URL, wait_until="domcontentloaded")

            if _is_authenticated(page.url):
                console.print(
                    f"[bold green]✅ Authenticated![/bold green] Landing at: [cyan]{page.url}[/cyan]"
                )
                return page

            # Session invalid — prompt user
            console.print(
                "[bold yellow]⚠️  Session invalid.[/bold yellow] "
                "Your cookies appear to be expired or missing."
            )
            console.print(
                "Please update [bold]config.json[/bold] with fresh cookies "
                "from your browser, then press [bold]Enter[/bold] to retry."
            )
            input("")
            current_settings = load_config(config_path)
