from playwright.async_api import Page
from urllib.parse import urljoin

async def extract_toc(page: Page, book_url: str) -> list[str]:
    """
    Navigate to the book's Table of Contents page and extract all chapter URLs.
    
    Args:
        page (Page): An authenticated Playwright page.
        book_url (str): The absolute URL of the book.
        
    Returns:
        list[str]: A list of absolute chapter URLs, ordered as they appear in the TOC.
    """
    await page.goto(book_url, wait_until="domcontentloaded")
    
    # We wait for the table of contents container to appear
    # O'Reilly usually has a structured TOC.
    # Looking at similar scrapers, '.t-chapter a' or '#toc a' or '.js-toc a' are common.
    # We will grab all anchor tags within the likely TOC containers.
    # It's better to fetch `a.t-chapter` or grab the table of contents list.
    
    # A generic robust selector: look for links inside an element with class or id containing 'toc' 
    # or elements with class 't-chapter'
    toc_links_locator = page.locator("a.t-chapter, #toc a, .js-toc a, .toc a, a.chapter")
    
    try:
        await toc_links_locator.first.wait_for(state="attached", timeout=10000)
    except Exception:
        # If we can't find specific ones, just find all links in the main content area
        # and we can try to filter them. But usually .t-chapter is correct.
        pass

    # Extract all hrefs
    hrefs = await toc_links_locator.evaluate_all(
        "elements => elements.map(e => e.getAttribute('href')).filter(href => href)"
    )
    
    # Resolve relative URLs
    chapter_urls = []
    for href in hrefs:
        # ensure absolute URL
        absolute_url = urljoin(book_url, href)
        # remove fragments if any, unless O'Reilly actually uses fragments to delimit chapters inside a single page
        # Often it is a separate page per chapter
        if absolute_url.startswith(book_url) or "learning.oreilly.com" in absolute_url:
            chapter_urls.append(absolute_url)
            
    # Remove duplicates but preserve order (dict.fromkeys does this)
    return list(dict.fromkeys(chapter_urls))
