import pytest
from oreilly_scraper.discovery import extract_playlist_id, discover_playlist
from unittest.mock import AsyncMock, patch
import json
from pathlib import Path

def test_extract_playlist_id():
    url = "https://learning.oreilly.com/playlists/53038940-d734-45ec-9e63-01e0ffaa4657/"
    playlist_id = extract_playlist_id(url)
    assert playlist_id == "53038940-d734-45ec-9e63-01e0ffaa4657"

def test_extract_playlist_id_invalid():
    with pytest.raises(ValueError):
        extract_playlist_id("https://example.com/not-a-playlist/")

@pytest.mark.asyncio
@patch('oreilly_scraper.discovery.create_authenticated_page')
@patch('oreilly_scraper.discovery.fetch_playlist_data')
async def test_discover_playlist_orchestration(mock_fetch_data, mock_create_page):
    # Arrange
    mock_settings = AsyncMock()
    mock_create_page.return_value = (AsyncMock(), AsyncMock(), AsyncMock())
    mock_fetch_data.return_value = {
        "id": "test-id",
        "title": "Test Playlist",
        "description": "Test description",
        "items": []
    }
    
    # Act
    await discover_playlist("https://learning.oreilly.com/playlists/test-id/", mock_settings)
    
    # Assert
    output_file = Path("playlists/test-id.json")
    assert output_file.exists()
    with open(output_file, 'r') as f:
        data = json.load(f)
        assert data["title"] == "Test Playlist"
    
    # Clean up
    output_file.unlink()
