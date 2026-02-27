# src/oreilly_scraper/discovery.py
import re
import json
import asyncio
from pathlib import Path
from playwright.async_api import Page
from .browser import create_authenticated_page
from .settings import Settings
from rich.console import Console

console = Console()

def extract_playlist_id(url: str) -> str:
    """Extracts the UUID playlist ID from an O'Reilly playlist URL."""
    match = re.search(r"playlists/([a-f0-9\-]+)/?", url)
    if not match:
        raise ValueError(f"Could not extract playlist ID from URL: {url}")
    return match.group(1)

async def fetch_playlist_data(page: Page, playlist_id: str) -> dict:
    """Fetches and cleans playlist data from the O'Reilly internal API."""
    playlist_url = f"https://learning.oreilly.com/playlists/{playlist_id}/"
    
    # Store the result in a future
    future = asyncio.get_event_loop().create_future()

    async def handle_response(response):
        if "/api/" in response.url:
            try:
                # O'Reilly sometimes uses different API versions or paths for playlists
                if playlist_id in response.url and ("playlist" in response.url or "collection" in response.url):
                    data = await response.json()
                    if isinstance(data, dict) and ("results" in data or "items" in data or "title" in data):
                        if not future.done():
                            console.print(f"[green]Found playlist API: {response.url}[/green]")
                            future.set_result(data)
            except Exception:
                pass

    page.on("response", handle_response)

    console.print(f"Navigating to playlist page: [cyan]{playlist_url}[/cyan]")
    await page.goto(playlist_url, wait_until="commit", timeout=60000)
    
    # Wait for the page to settle manually
    await asyncio.sleep(10)

    # Try to get the title and description from the page first
    actual_title = "Unknown Playlist"
    actual_description = ""
    try:
        title_elem = page.locator("h1")
        if await title_elem.count() > 0:
            actual_title = (await title_elem.first.inner_text()).strip()
            
        desc_elem = page.locator(".playlist-description, [data-testid='playlist-description'], .description-text")
        if await desc_elem.count() > 0:
            actual_description = (await desc_elem.first.inner_text()).strip()
    except Exception:
        pass

    # Click "Show More Titles" until it's gone or we've clicked it enough
    for _ in range(5):
        try:
            show_more = page.get_by_role("button", name="Show More Titles")
            if await show_more.is_visible(timeout=3000):
                console.print("Clicking 'Show More Titles'...")
                await show_more.click()
                await asyncio.sleep(2)
            else:
                break
        except Exception:
            break

    try:
        # Wait for the API response
        raw_data = await asyncio.wait_for(future, timeout=2.0)
        
        cleaned_items = []
        results = raw_data.get("results", raw_data.get("items", []))
        
        for item in results:
            url_path = item.get("content_url") or item.get("url")
            if url_path:
                full_url = url_path if url_path.startswith("http") else f"https://learning.oreilly.com{url_path}"
                cleaned_items.append({
                    "title": item.get("title"),
                    "format": item.get("format"),
                    "url": full_url,
                })
            
        return {
            "id": playlist_id,
            "title": raw_data.get("title", actual_title),
            "description": raw_data.get("description", actual_description),
            "items": cleaned_items
        }
    except asyncio.TimeoutError:
        console.print("[yellow]Interception failed. Scraping from HTML content...[/yellow]")
        content = await page.content()
        data = await _scrape_from_html(content, playlist_id)
        # Use the title/description we found via locators if they are better
        if actual_title != "Unknown Playlist" and data["title"] == "Discovered from HTML":
            data["title"] = actual_title
        data["description"] = actual_description if actual_description else data["description"]
        return data

async def _scrape_from_html(html: str, playlist_id: str) -> dict:
    """Fallback method to scrape data using regex on the full HTML."""
    # Try to find title in h1 if not provided
    title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.IGNORECASE | re.DOTALL)
    title = title_match.group(1).strip() if title_match else "Discovered from HTML"
    # Clean tags from title
    title = re.sub(r'<[^>]*>', '', title)

    # Pattern: <a href="/api/v1/continue/9798341630147/" ...>GraphRAG: The Definitive Guide</a>
    matches = re.findall(r'href="/api/v1/continue/(\d+)/"[^>]*>([^<]+)</a>', html)
    
    items = []
    seen_urls = set()
    for isbn, item_title in matches:
        full_url = f"https://learning.oreilly.com/library/view/-/{isbn}/"
        if full_url not in seen_urls:
            items.append({
                "title": item_title.strip(),
                "format": "book",
                "url": full_url
            })
            seen_urls.add(full_url)
    
    # Also look for traditional library/view links just in case
    lib_matches = re.findall(r'href=["\'](/library/view/[^"\']+)["\']', html)
    for path in lib_matches:
        clean_path = path.split("?")[0].rstrip("/")
        full_url = f"https://learning.oreilly.com{clean_path}/"
        if full_url not in seen_urls:
            item_title = clean_path.split("/")[-2].replace("-", " ").title()
            items.append({
                "title": item_title,
                "format": "unknown",
                "url": full_url
            })
            seen_urls.add(full_url)
            
    return {
        "id": playlist_id,
        "title": title,
        "description": "",
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
            
        console.print(f"[bold green]Success![/bold green] Playlist exported to [cyan]{output_file}[/cyan]")
        console.print(f"Playlist Title: [bold]{data['title']}[/bold]")
        if data['description']:
            console.print(f"Description: [dim]{data['description']}[/dim]")
        console.print(f"Found [bold]{len(data['items'])}[/bold] items.")
    finally:
        await browser.close()
        await p.stop()
