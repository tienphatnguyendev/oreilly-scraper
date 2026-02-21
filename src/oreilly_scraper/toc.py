from playwright.async_api import Page
from urllib.parse import urljoin, urlparse


async def extract_toc(page: Page, book_url: str) -> list[str]:
    """
    Navigate to the book's Table of Contents page and extract all chapter URLs.

    Args:
        page: An authenticated Playwright page.
        book_url: The absolute URL of the book.

    Returns:
        A list of absolute chapter URLs, ordered as they appear in the TOC.

    Raises:
        RuntimeError: If no chapter links are found on the page.
    """
    await page.goto(book_url, wait_until="domcontentloaded")

    # O'Reilly renders the TOC sidebar with JS; chapter links use the
    # class "orm-Link-root" inside a scrollable wrapper.
    toc_links_locator = page.locator("a.orm-Link-root")

    try:
        await toc_links_locator.first.wait_for(state="attached", timeout=30000)
        # Give JS a moment to finish rendering all links
        await page.wait_for_timeout(2000)
    except Exception:
        pass

    # Extract the book's base path
    book_path = urlparse(book_url).path.rstrip("/")

    # JS-side filtering: only grab hrefs that contain the book path AND end in .html
    hrefs = await page.evaluate(
        """(bookPath) => {
        return Array.from(document.querySelectorAll('a.orm-Link-root'))
            .map(a => a.getAttribute('href'))
            .filter(href => href && href.includes(bookPath) && href.endsWith('.html'))
    }""",
        book_path,
    )

    # Resolve relative URLs to absolute
    chapter_urls = [urljoin(book_url, href) for href in hrefs]

    # Remove duplicates but preserve order
    result = list(dict.fromkeys(chapter_urls))

    if not result:
        raise RuntimeError(
            f"TOC extraction found 0 chapter links on {book_url}. "
            "The page structure may have changed or authentication failed."
        )

    return result

