import pytest
from oreilly_scraper.discovery import extract_playlist_id

def test_extract_playlist_id():
    url = "https://learning.oreilly.com/playlists/53038940-d734-45ec-9e63-01e0ffaa4657/"
    playlist_id = extract_playlist_id(url)
    assert playlist_id == "53038940-d734-45ec-9e63-01e0ffaa4657"

def test_extract_playlist_id_invalid():
    with pytest.raises(ValueError):
        extract_playlist_id("https://learning.oreilly.com/playlists/invalid/")
