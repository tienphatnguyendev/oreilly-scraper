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
import json
from oreilly_scraper.discovery import fetch_playlist_data

@pytest.mark.asyncio
async def test_fetch_playlist_data():
    mock_page = AsyncMock()
    mock_response = AsyncMock()
    mock_response.json.return_value = {
        "title": "Test Playlist",
        "description": "Test description",
        "results": [
            {
                "title": "Test Book",
                "content_url": "/library/view/test-book/123/",
                "format": "book"
            }
        ]
    }
    mock_page.request.get.return_value = mock_response

    data = await fetch_playlist_data(mock_page, "test-id")
    
    assert data["title"] == "Test Playlist"
    assert len(data["items"]) == 1
    assert data["items"][0]["url"] == "https://learning.oreilly.com/library/view/test-book/123/"
