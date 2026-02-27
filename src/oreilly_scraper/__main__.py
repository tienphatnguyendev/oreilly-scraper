import asyncio
import sys
import argparse

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
        config.output_dir = config.output_dir / book_slug
        console.print(f"Loaded config for book: [cyan]{config.book_url}[/cyan]")
        asyncio.run(_run_scrape(config))
    elif args.command == "discover":
        console.print(f"Discovering playlist: [cyan]{args.playlist_url}[/cyan]")
        asyncio.run(discover_playlist(args.playlist_url, config))


async def _run_scrape(config: Settings):
    p, browser, page = await create_authenticated_page(config)
    try:
        console.print(f"[bold green]Ready![/bold green] Authenticated at [cyan]{page.url}[/cyan]")
        console.print("[bold blue]Extracting Table of Contents...[/bold blue]")
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
        await downloader.download_all()

        failed = sum(1 for c in state.chapters if c.status == ChapterStatus.FAILED)
        if failed:
            console.print(f"[bold yellow]Finished with {failed} failed chapter(s).[/bold yellow]")
        else:
            console.print("[bold green]All chapters downloaded successfully![/bold green]")
    finally:
        await browser.close()
        await p.stop()


def _build_state(config: Settings, chapter_urls: list[str]) -> ScrapeState:
    chapters = [ChapterState(url=url, status=ChapterStatus.PENDING) for url in chapter_urls]
    return ScrapeState(book_url=str(config.book_url), total_chapters=len(chapters), chapters=chapters)


if __name__ == "__main__":
    main()
