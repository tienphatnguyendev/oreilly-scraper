import pytest
from oreilly_scraper.discovery import extract_playlist_id

def test_extract_playlist_id():
    url = "https://learning.oreilly.com/playlists/53038940-d734-45ec-9e63-01e0ffaa4657/"
    playlist_id = extract_playlist_id(url)
    assert playlist_id == "53038940-d734-45ec-9e63-01e0ffaa4657"

def test_extract_playlist_id_invalid():
    with pytest.raises(ValueError):
        extract_playlist_id("https://learning.oreilly.com/playlists/invalid/")

from unittest.mock import AsyncMock, patch
from oreilly_scraper.discovery import fetch_playlist_data

@pytest.mark.asyncio
async def test_fetch_playlist_data():
    mock_page = AsyncMock()
    # Mock content to return a string for regex fallback
    mock_page.content.return_value = """
        <a href="/api/v1/continue/12345/">Test Book</a>
        <a href="/library/view/another-book/67890/">Another Book</a>
    """
    
    # Mock show_more button
    mock_show_more = AsyncMock()
    mock_show_more.is_visible.return_value = False
    mock_page.get_by_role.return_value = mock_show_more
    
    # We expect fetch_playlist_data to time out on API interception in this mock 
    # and fall back to _scrape_from_html which uses the mock_page.content
    data = await fetch_playlist_data(mock_page, "test-id")
    
    assert data["id"] == "test-id"
    assert len(data["items"]) >= 1
    assert any(item["title"] == "Test Book" for item in data["items"])
    assert any(item["url"] == "https://learning.oreilly.com/library/view/-/12345/" for item in data["items"])
