import asyncio
import sys
from rich.console import Console
from .settings import load_config, Settings
from .browser import create_authenticated_page
from .toc import extract_toc
from .state import ScrapeState, ChapterState, ChapterStatus, load_state, save_state
import json

console = Console()


def main():
    console.print("[bold green]O'Reilly PDF Downloader[/bold green] initializing...")
    try:
        config: Settings = load_config()
        console.print(f"Loaded config for: [cyan]{config.book_url}[/cyan]")
        console.print(f"Cookies: [yellow]{len(config.cookies)} loaded[/yellow]")
        console.print(f"Output dir: [blue]{config.output_dir}[/blue]")
    except FileNotFoundError as e:
        console.print(f"[bold red]Config not found:[/bold red] {e}")
        sys.exit(1)

    asyncio.run(_run(config))


async def _run(config: Settings):
    page = await create_authenticated_page(config)
    console.print(f"[bold green]Ready![/bold green] Authenticated at [cyan]{page.url}[/cyan]")
    
    console.print(f"[bold blue]Extracting Table of Contents...[/bold blue]")
    chapter_urls = await extract_toc(page, str(config.book_url))
    
    state_path = config.output_dir / "state.json"
    
    if state_path.exists():
        console.print(f"[bold yellow]Found existing state file at {state_path}. Resuming...[/bold yellow]")
        state = load_state(state_path)
    else:
        # Initialize new state
        chapters = [ChapterState(url=url, status=ChapterStatus.PENDING) for url in chapter_urls]
        state = ScrapeState(
            book_url=str(config.book_url),
            total_chapters=len(chapters),
            chapters=chapters
        )
        save_state(state, state_path)
        console.print(f"[bold green]Created new state tracking file at {state_path}.[/bold green]")
        
    console.print(f"[bold]Total Chapters:[/bold] {state.total_chapters}")
    
    console.print(f"[bold blue]Starting chapter downloads...[/bold blue]")
    from .chapter_downloader import ChapterDownloader
    downloader = ChapterDownloader(page=page, state=state, output_dir=config.output_dir)
    await downloader.download_all()
    
    console.print(f"[bold green]All chapters downloaded successfully![/bold green]")
    
    # We will close the page/browser to be clean if needed, or leave it for the next task
    await page.context.browser.close()

if __name__ == "__main__":
    main()
