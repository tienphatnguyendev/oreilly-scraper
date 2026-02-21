import asyncio
import sys

from rich.console import Console

from .settings import load_config, Settings
from .browser import create_authenticated_page
from .toc import extract_toc
from .state import ScrapeState, ChapterState, ChapterStatus, load_state, save_state

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
    p, browser, page = await create_authenticated_page(config)
    try:
        console.print(
            f"[bold green]Ready![/bold green] Authenticated at [cyan]{page.url}[/cyan]"
        )

        console.print("[bold blue]Extracting Table of Contents...[/bold blue]")
        chapter_urls = await extract_toc(page, str(config.book_url))
        console.print(f"[green]Found {len(chapter_urls)} chapters[/green]")

        config.output_dir.mkdir(parents=True, exist_ok=True)
        state_path = config.output_dir / "state.json"

        state: ScrapeState
        if state_path.exists():
            state = load_state(state_path)
            existing_urls = [c.url for c in state.chapters]

            # Reconcile: if the saved state has different chapters, rebuild
            if existing_urls != chapter_urls:
                console.print(
                    f"[yellow]⚠ State mismatch — saved {len(existing_urls)} chapters "
                    f"vs {len(chapter_urls)} found. Rebuilding state.[/yellow]"
                )
                state = _build_state(config, chapter_urls)
                save_state(state, state_path)
            else:
                done = sum(1 for c in state.chapters if c.status == ChapterStatus.DOWNLOADED)
                console.print(
                    f"[bold yellow]Resuming — {done}/{state.total_chapters} already downloaded[/bold yellow]"
                )
        else:
            state = _build_state(config, chapter_urls)
            save_state(state, state_path)
            console.print(
                f"[bold green]Created state file[/bold green] at {state_path}"
            )

        console.print(f"[bold]Total Chapters:[/bold] {state.total_chapters}")
        console.print("[bold blue]Starting chapter downloads...[/bold blue]")

        from .chapter_downloader import ChapterDownloader

        downloader = ChapterDownloader(
            page=page, state=state, output_dir=config.output_dir
        )
        await downloader.download_all()

        # Final summary
        failed = sum(1 for c in state.chapters if c.status == ChapterStatus.FAILED)
        if failed:
            console.print(
                f"[bold yellow]Finished with {failed} failed chapter(s). "
                f"Re-run to retry.[/bold yellow]"
            )
        else:
            console.print(
                "[bold green]All chapters downloaded successfully![/bold green]"
            )
    finally:
        await browser.close()
        await p.stop()


def _build_state(config: Settings, chapter_urls: list[str]) -> ScrapeState:
    """Build a fresh ScrapeState from a list of chapter URLs."""
    chapters = [
        ChapterState(url=url, status=ChapterStatus.PENDING) for url in chapter_urls
    ]
    return ScrapeState(
        book_url=str(config.book_url),
        total_chapters=len(chapters),
        chapters=chapters,
    )


if __name__ == "__main__":
    main()
