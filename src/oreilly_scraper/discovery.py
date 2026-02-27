# src/oreilly_scraper/discovery.py
import re

def extract_playlist_id(url: str) -> str:
    """Extracts the UUID playlist ID from an O'Reilly playlist URL."""
    match = re.search(r"playlists/([a-f0-9\-]+)/?", url)
    if not match:
        raise ValueError(f"Could not extract playlist ID from URL: {url}")
    return match.group(1)
