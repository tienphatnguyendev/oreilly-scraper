# src/oreilly_scraper/discovery.py
import re

def extract_playlist_id(url: str) -> str:
    """Extracts the UUID playlist ID from an O'Reilly playlist URL."""
    match = re.search(r"playlists/([a-f0-9\-]+)/?", url)
    if not match:
        raise ValueError(f"Could not extract playlist ID from URL: {url}")
    return match.group(1)

from playwright.async_api import Page

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

import json
from pathlib import Path
from .browser import create_authenticated_page
from .settings import Settings

async def discover_playlist(url: str, settings: Settings):
    """Main entrypoint for discovering a playlist and exporting to JSON."""
    playlist_id = extract_playlist_id(url)
    
    p, browser, page = await create_authenticated_page(settings)
    try:
        data = await fetch_playlist_data(page, playlist_id)
        
        output_dir = Path("playlists")
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / f"{playlist_id}.json"
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        print(f"Playlist exported to {output_file}")
    finally:
        await browser.close()
        await p.stop()
