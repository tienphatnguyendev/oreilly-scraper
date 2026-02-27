import re
import json
from pathlib import Path
from playwright.async_api import Page

def extract_playlist_id(url: str) -> str:
    """Extracts the UUID playlist ID from an O'Reilly playlist URL."""
    match = re.search(r"playlists/([a-f0-9\\-]+)/?", url)
    if not match:
        raise ValueError(f"Could not extract playlist ID from URL: {url}")
    return match.group(1)

async def fetch_playlist_data(page: Page, playlist_id: str) -> dict:
    """Fetches and cleans playlist data from the O'Reilly internal API."""
    api_url = f"https://learning.oreilly.com/api/v2/playlists/{playlist_id}/"
    response = await page.request.get(api_url)
    
    if not response.ok:
        raise Exception(f"Failed to fetch playlist data: {response.status}")
        
    raw_data = await response.json()
    
    cleaned_items = []
    for item in raw_data.get("results", []):
        cleaned_items.append({
            "title": item.get("title"),
            "format": item.get("format"),
            "url": f"https://learning.oreilly.com{item.get('content_url')}",
        })
        
    return {
        "id": playlist_id,
        "title": raw_data.get("title", ""),
        "description": raw_data.get("description", ""),
        "items": cleaned_items
    }
