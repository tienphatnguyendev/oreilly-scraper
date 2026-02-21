import pytest
from unittest.mock import AsyncMock, MagicMock
from urllib.parse import urljoin
from oreilly_scraper.toc import extract_toc

@pytest.mark.asyncio
async def test_extract_toc():
    # Setup mock page
    mock_page = AsyncMock()
    mock_locator = MagicMock()
    # page.locator() is a synchronous method returning a Locator
    mock_page.locator = MagicMock(return_value=mock_locator)
    
    # Setup mock for first.wait_for()
    mock_first = AsyncMock()
    mock_locator.first = mock_first
    
    # Setup mock for evaluate_all()
    # Let's say it returns a mix of relative and absolute links
    mock_locator.evaluate_all = AsyncMock(return_value=[
        "/library/view/book/123/ch01.html",
        "/library/view/book/123/ch02.html",
        "https://learning.oreilly.com/library/view/book/123/ch03.html",
        "/library/view/book/123/ch02.html",  # Duplicate
    ])
    
    book_url = "https://learning.oreilly.com/library/view/book/123/"
    
    result = await extract_toc(mock_page, book_url)
    
    # Verify navigations
    mock_page.goto.assert_called_once_with(book_url, wait_until="domcontentloaded")
    
    # Verify locator
    mock_page.locator.assert_called_once_with("a.t-chapter, #toc a, .js-toc a, .toc a, a.chapter")
    
    # Verify result (absolute, no duplicates, order preserved)
    expected = [
        "https://learning.oreilly.com/library/view/book/123/ch01.html",
        "https://learning.oreilly.com/library/view/book/123/ch02.html",
        "https://learning.oreilly.com/library/view/book/123/ch03.html"
    ]
    
    assert result == expected
