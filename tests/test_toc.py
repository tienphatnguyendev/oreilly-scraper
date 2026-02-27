import pytest
from unittest.mock import AsyncMock, MagicMock
from oreilly_scraper.toc import extract_toc


@pytest.mark.asyncio
async def test_extract_toc_finds_chapters():
    """Extract chapter URLs from a.orm-Link-root links filtered by book path."""
    mock_page = AsyncMock()
    mock_locator = MagicMock()
    mock_page.locator = MagicMock(return_value=mock_locator)
    mock_first = AsyncMock()
    mock_locator.first = mock_first

    book_url = "https://learning.oreilly.com/library/view/book/123/"
    mock_page.url = book_url
    # page.evaluate returns hrefs filtered by JS
    mock_page.evaluate = AsyncMock(
        return_value=[
            "/library/view/book/123/ch01.html",
            "/library/view/book/123/ch02.html",
            "https://learning.oreilly.com/library/view/book/123/ch03.html",
            "/library/view/book/123/ch02.html",  # Duplicate
        ]
    )

    result = await extract_toc(mock_page, book_url)

    # Verify navigation
    mock_page.goto.assert_called_once_with(book_url, wait_until="domcontentloaded")

    # Verify locator was used to wait
    mock_page.locator.assert_called_once_with("a.orm-Link-root")

    # Verify result: absolute, no duplicates, order preserved
    expected = [
        "https://learning.oreilly.com/library/view/book/123/ch01.html",
        "https://learning.oreilly.com/library/view/book/123/ch02.html",
        "https://learning.oreilly.com/library/view/book/123/ch03.html",
    ]
    assert result == expected


@pytest.mark.asyncio
async def test_extract_toc_raises_on_empty():
    """RuntimeError raised when no chapters found."""
    mock_page = AsyncMock()
    mock_locator = MagicMock()
    mock_page.locator = MagicMock(return_value=mock_locator)
    mock_first = AsyncMock()
    mock_locator.first = mock_first

    book_url = "https://learning.oreilly.com/library/view/book/123/"
    mock_page.url = book_url
    mock_page.evaluate = AsyncMock(return_value=[])

    with pytest.raises(RuntimeError, match="0 chapter links"):
        await extract_toc(mock_page, "https://learning.oreilly.com/library/view/book/123/")


@pytest.mark.asyncio
async def test_extract_toc_with_shorthand_url():
    """Extract chapter URLs correctly handles shorthand URLs like /library/view/-/<ISBN>/"""
    mock_page = AsyncMock()
    mock_locator = MagicMock()
    mock_page.locator = MagicMock(return_value=mock_locator)
    mock_first = AsyncMock()
    mock_locator.first = mock_first

    # Shorthand URL format
    shorthand_url = "https://learning.oreilly.com/library/view/-/9781787785090/"
    mock_page.url = shorthand_url

    # Return some chapters
    mock_page.evaluate = AsyncMock(
        return_value=[
            "https://learning.oreilly.com/library/view/pci-dss-version/9781787785090/xhtml/ch01.html"
        ]
    )

    result = await extract_toc(mock_page, shorthand_url)

    # Check evaluate was called with the correct book ID
    # The first arg to evaluate is the JS script string, the second is the book_id
    args, kwargs = mock_page.evaluate.call_args
    assert args[1] == "9781787785090"

    expected = ["https://learning.oreilly.com/library/view/pci-dss-version/9781787785090/xhtml/ch01.html"]
    assert result == expected
