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
        
        results = raw_data.get("results", raw_data.get("items", []))
        items = []
        
        for item in results:
            url_path = item.get("content_url") or item.get("url")
            if url_path:
                full_url = url_path if url_path.startswith("http") else f"https://learning.oreilly.com{url_path}"
                # Extract ISBN from URL if possible
                isbn_match = re.search(r'/(\d{10,13})/?$', full_url)
                isbn = isbn_match.group(1) if isbn_match else None
                
                items.append({
                    "title": item.get("title"),
                    "format": item.get("format"),
                    "url": full_url,
                    "description": item.get("description", ""),
                    "isbn": isbn
                })
            
        playlist_data = {
            "id": playlist_id,
            "title": raw_data.get("title", actual_title),
            "description": raw_data.get("description", actual_description),
            "items": items
        }
    except asyncio.TimeoutError:
        console.print("[yellow]Interception failed. Scraping from HTML content...[/yellow]")
        content = await page.content()
        playlist_data = await _scrape_from_html(content, playlist_id)
        if actual_title != "Unknown Playlist" and playlist_data["title"] == "Discovered from HTML":
            playlist_data["title"] = actual_title
        playlist_data["description"] = actual_description if actual_description else playlist_data["description"]

    # Enrich with descriptions if missing
    await _enrich_with_metadata(page, playlist_data)
    
    return playlist_data

async def _enrich_with_metadata(page: Page, data: dict):
    """Enriches items with metadata (like descriptions) from the internal API."""
    items_to_enrich = [i for i in data["items"] if not i.get("description") and i.get("isbn")]
    if not items_to_enrich:
        return

    console.print(f"Enriching [bold]{len(items_to_enrich)}[/bold] items with metadata...")
    
    # Batch size for API
    batch_size = 15
    for i in range(0, len(items_to_enrich), batch_size):
        batch = items_to_enrich[i:i+batch_size]
        isbns = [item["isbn"] for item in batch]
        
        # Build the metadata query
        query_parts = [f"ourn=urn:orm:book:{isbn}" for isbn in isbns]
        api_url = f"https://learning.oreilly.com/api/v2/metadata/?limit={batch_size}&include_hidden=true&{'&'.join(query_parts)}"
        
        try:
            metadata_raw = await page.evaluate(f"""
                async () => {{
                    const response = await fetch('{api_url}');
                    if (!response.ok) return null;
                    return await response.json();
                }}
            """)
            
            if metadata_raw and "results" in metadata_raw:
                # Create a map of ISBN to description
                meta_map = {}
                for res in metadata_raw["results"]:
                    ident = res.get("archive_id") or res.get("identifier")
                    if ident:
                        # Extract plain isbn (handle urn:orm:book:123 or just 123)
                        clean_ident = str(ident).split(":")[-1]
                        meta_map[clean_ident] = res.get("description", "")
                
                # Update batch items
                for item in batch:
                    isbn = str(item["isbn"])
                    if isbn in meta_map:
                        item["description"] = meta_map[isbn]
        except Exception as e:
            console.print(f"[yellow]Metadata enrichment batch failed: {e}[/yellow]")

async def _scrape_from_html(html: str, playlist_id: str) -> dict:
    """Fallback method to scrape data using regex on the full HTML."""
    title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.IGNORECASE | re.DOTALL)
    title = title_match.group(1).strip() if title_match else "Discovered from HTML"
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
                "url": full_url,
                "isbn": isbn,
                "description": ""
            })
            seen_urls.add(full_url)
    
    # Also look for traditional library/view links
    lib_matches = re.findall(r'href=["\'](/library/view/[^"\']+/(\d+)/?)["\']', html)
    for path, isbn in lib_matches:
        full_url = f"https://learning.oreilly.com{path.rstrip('/')}/"
        if full_url not in seen_urls:
            item_title = path.split("/")[-2].replace("-", " ").title()
            items.append({
                "title": item_title,
                "format": "unknown",
                "url": full_url,
                "isbn": isbn,
                "description": ""
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
