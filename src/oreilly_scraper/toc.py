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

    # The URL might have changed due to redirection (e.g. from /-/ shortened URL to canonical)
    current_url = page.url
    
    # Extract the book's ID (typically the ISBN, which is the last path segment)
    path_parts = [p for p in urlparse(current_url).path.split("/") if p]
    book_id = path_parts[-1] if path_parts else ""

    # JS-side filtering: only grab hrefs that contain the book ID AND end in .html, .xhtml, or .htm
    hrefs = await page.evaluate(
        """(bookId) => {
        return Array.from(document.querySelectorAll('a.orm-Link-root'))
            .map(a => a.getAttribute('href'))
            .filter(href => href && href.includes(bookId) && (href.endsWith('.html') || href.endsWith('.xhtml') || href.endsWith('.htm')))
    }""",
        book_id,
    )

    # Resolve relative URLs to absolute
    chapter_urls = [urljoin(current_url, href) for href in hrefs]

    # Remove duplicates but preserve order
    result = list(dict.fromkeys(chapter_urls))

    if not result:
        raise RuntimeError(
            f"TOC extraction found 0 chapter links on {book_url}. "
            "The page structure may have changed or authentication failed."
        )

    return result

