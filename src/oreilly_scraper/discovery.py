import re
import json
from pathlib import Path
from playwright.async_api import Page
from .browser import create_authenticated_page
from .settings import Settings

def extract_playlist_id(url: str) -> str:
    """Extracts the playlist ID from an O'Reilly playlist URL."""
    match = re.search(r"playlists/([a-zA-Z0-9\\-]+)/?", url)
    if not match:
        raise ValueError(f"Could not extract playlist ID from URL: {url}")
    return match.group(1)

async def fetch_playlist_data(page: Page, playlist_id: str) -> dict:
    """Fetches and cleans playlist data by scraping the playlist page."""
    playlist_url = f"https://learning.oreilly.com/playlists/{playlist_id}/"
    await page.goto(playlist_url, wait_until="domcontentloaded")

    title = await page.locator("h1").first.inner_text()
    
    try:
        description = await page.locator(".description").first.inner_text(timeout=5000)
    except Exception:
        description = ""

    items = []
    for item_locator in await page.locator("a[data-testid='playlist-item-title']").all():
        item_title = await item_locator.inner_text()
        item_url = await item_locator.get_attribute("href")
        items.append({
            "title": item_title,
            "format": "unknown",
            "url": f"https://learning.oreilly.com{item_url}",
        })

    return {
        "id": playlist_id,
        "title": title,
        "description": description,
        "items": items
    }

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
