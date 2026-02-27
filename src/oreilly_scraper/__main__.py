import asyncio
import sys
import argparse
import json
import random
from pathlib import Path

from rich.console import Console

from .settings import load_config, Settings, ExportFormat
from .browser import create_authenticated_page
from .toc import extract_toc
from .state import ScrapeState, ChapterState, ChapterStatus, load_state, save_state
from .exporters import PdfExporter, MarkdownExporter
from .discovery import discover_playlist

console = Console()


def main():
    parser = argparse.ArgumentParser(description="O'Reilly Scraper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Scrape command (default)
    scrape_parser = subparsers.add_parser("scrape", help="Scrape a book from O'Reilly")

    # Discover command
    discover_parser = subparsers.add_parser("discover", help="Discover a playlist from O'Reilly")
    discover_parser.add_argument("playlist_url", help="The URL of the playlist to discover")

    # Scrape Playlist command
    playlist_parser = subparsers.add_parser("scrape-playlist", help="Scrape all books in a discovered playlist JSON")
    playlist_parser.add_argument("playlist_path", help="Path to the discovered playlist JSON file")

    args = parser.parse_args()

    console.print("[bold green]O'Reilly Scraper[/bold green] initializing...")
    try:
        config: Settings = load_config()
    except FileNotFoundError as e:
        console.print(f"[bold red]Config not found:[/bold red] {e}")
        sys.exit(1)

    if args.command == "scrape":
        # Extract book slug from URL
        parts = [p for p in config.book_url.path.split("/") if p]
        book_slug = parts[-2] if len(parts) >= 2 else "book"
        if book_slug == "-":
            book_slug = parts[-1]
        config.output_dir = config.output_dir / book_slug
        console.print(f"Loaded config for book: [cyan]{config.book_url}[/cyan]")
        asyncio.run(_run_scrape(config))
    elif args.command == "discover":
        console.print(f"Discovering playlist: [cyan]{args.playlist_url}[/cyan]")
        asyncio.run(discover_playlist(args.playlist_url, config))
    elif args.command == "scrape-playlist":
        console.print(f"Scraping playlist from: [cyan]{args.playlist_path}[/cyan]")
        asyncio.run(_run_scrape_playlist(args.playlist_path, config))

async def _run_scrape(config: Settings):
    p, browser, page = await create_authenticated_page(config)
    try:
        console.print(f"[bold green]Ready![/bold green] Authenticated at [cyan]{page.url}[/cyan]")
        await _scrape_single_book(page, config)
    finally:
        await browser.close()
        await p.stop()


async def _scrape_single_book(page, config: Settings, progress_manager=None, parent_task=None):
    console.print(f"[bold blue]Extracting Table of Contents for {config.book_url}...[/bold blue]")
    chapter_urls = await extract_toc(page, str(config.book_url))
    console.print(f"[green]Found {len(chapter_urls)} chapters[/green]")

    config.output_dir.mkdir(parents=True, exist_ok=True)
    state_path = config.output_dir / "state.json"

    state: ScrapeState
    if state_path.exists():
        state = load_state(state_path)
        existing_urls = [c.url for c in state.chapters]

        if existing_urls != chapter_urls:
            console.print(f"[yellow]⚠ State mismatch — rebuilding state.[/yellow]")
            state = _build_state(config, chapter_urls)
            save_state(state, state_path)
        else:
            done = sum(1 for c in state.chapters if c.status == ChapterStatus.DOWNLOADED)
            console.print(f"[bold yellow]Resuming — {done}/{state.total_chapters} downloaded[/bold yellow]")
    else:
        state = _build_state(config, chapter_urls)
        save_state(state, state_path)
        console.print(f"[bold green]Created state file[/bold green] at {state_path}")

    console.print(f"[bold]Total Chapters:[/bold] {state.total_chapters}")
    console.print("[bold blue]Starting chapter downloads...[/bold blue]")

    from .chapter_downloader import ChapterDownloader
    
    exporters = []
    if ExportFormat.PDF in config.formats:
        exporters.append(PdfExporter())
    if ExportFormat.MARKDOWN in config.formats:
        exporters.append(MarkdownExporter())
        
    console.print(f"[bold]Active Exporters:[/bold] {', '.join([e.__class__.__name__ for e in exporters])}")

    downloader = ChapterDownloader(page=page, state=state, output_dir=config.output_dir, exporters=exporters)
    await downloader.download_all(progress_manager=progress_manager, parent_task=parent_task)

    failed = sum(1 for c in state.chapters if c.status == ChapterStatus.FAILED)
    if failed:
        console.print(f"[bold yellow]Finished with {failed} failed chapter(s).[/bold yellow]")
    else:
        console.print("[bold green]All chapters downloaded successfully![/bold green]")


async def _run_scrape_playlist(playlist_path: str, config: Settings):
    path = Path(playlist_path)
    if not path.exists():
        console.print(f"[bold red]Playlist not found:[/bold red] {playlist_path}")
        sys.exit(1)
        
    with open(path, "r", encoding="utf-8") as f:
        playlist_data = json.load(f)
        
    items = [item for item in playlist_data.get("items", []) if item.get("format") == "book" or "book" in item.get("url", "")]
    console.print(f"[bold green]Found {len(items)} books in playlist.[/bold green]")
    
    if not items:
        return

    # Enforce Markdown output as requested
    if ExportFormat.MARKDOWN not in config.formats:
        console.print("[bold yellow]Warning: Markdown format not in config.json. Adding it for playlist run...[/bold yellow]")
        config.formats.append(ExportFormat.MARKDOWN)

    base_output_dir = config.output_dir
    playlist_id = playlist_data.get("id", "playlist")
    
    p, browser, page = await create_authenticated_page(config)
    try:
        console.print(f"[bold green]Ready![/bold green] Authenticated at [cyan]{page.url}[/cyan]")
        
        success_count = 0
        skip_count = 0
        fail_count = 0
        
        from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("({task.completed}/{task.total})"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            playlist_task = progress.add_task("Playlist Overall", total=len(items))
            
            for idx, item in enumerate(items):
                url = item.get("url")
                title = item.get("title", "Unknown Title")
                progress.update(playlist_task, description=f"Book {idx+1}/{len(items)}: {title}")
                
                # Extract book slug
                import re
                clean_title = re.sub(r'[^\w\s-]', '', title).strip().lower()
                book_slug = re.sub(r'[-\s]+', '-', clean_title)
                
                # Fallback to URL if title is missing or "unknown-title"
                if not book_slug or book_slug == "unknown-title":
                    parts = [part for part in url.split("/") if part]
                    book_slug = parts[-2] if len(parts) >= 2 else f"book_{idx}"
                    if book_slug == "-":
                        book_slug = parts[-1]
                
                # Override config for this book
                from pydantic import HttpUrl
                try:
                    book_config = config.model_copy()
                    book_config.book_url = HttpUrl(url)
                    book_config.output_dir = base_output_dir / playlist_id / book_slug
                except Exception as e:
                    console.print(f"[bold red]Failed to setup config for {url}:[/bold red] {e}")
                    fail_count += 1
                    progress.advance(playlist_task)
                    continue
                    
                state_path = book_config.output_dir / "state.json"
                if state_path.exists():
                    try:
                        state = load_state(state_path)
                        done = sum(1 for c in state.chapters if c.status == ChapterStatus.DOWNLOADED)
                        if done == state.total_chapters and state.total_chapters > 0:
                            # Use console.print because we are outside the with block's direct rendering area
                            # wait, rich Progress manages console output safely.
                            progress.console.print(f"[bold green]Skipping - Already fully downloaded: {title}[/bold green]")
                            skip_count += 1
                            progress.advance(playlist_task)
                            continue
                    except Exception:
                        pass # Proceed to scrape if state file is broken
                
                try:
                    await _scrape_single_book(page, book_config, progress_manager=progress, parent_task=playlist_task)
                    success_count += 1
                except Exception as e:
                    progress.console.print(f"[bold red]Failed to scrape book {title}:[/bold red] {e}")
                    fail_count += 1
                
                progress.advance(playlist_task)
                
                if idx < len(items) - 1:
                    delay = random.uniform(30.0, 90.0)
                    # We can't really "wait" inside the progress bar without blocking the spinner
                    # but it's fine for this CLI app.
                    progress.update(playlist_task, description=f"[dim]Waiting {delay:.0f}s...[/dim]")
                    await asyncio.sleep(delay)
                
        console.print(f"\n[bold green]Playlist Run Complete![/bold green]")
        console.print(f"Success: {success_count}, Skipped: {skip_count}, Failed: {fail_count}")
        
    finally:
        await browser.close()
        await p.stop()


def _build_state(config: Settings, chapter_urls: list[str]) -> ScrapeState:
    chapters = [ChapterState(url=url, status=ChapterStatus.PENDING) for url in chapter_urls]
    return ScrapeState(book_url=str(config.book_url), total_chapters=len(chapters), chapters=chapters)


if __name__ == "__main__":
    main()
