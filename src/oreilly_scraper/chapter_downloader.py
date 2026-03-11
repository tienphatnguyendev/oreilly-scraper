import asyncio
import random
from pathlib import Path

from playwright.async_api import Page, TimeoutError as PlaywrightTimeout
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn

from .state import ScrapeState, ChapterStatus, save_state
from .exporters import ChapterExporter

console = Console()

MAX_RETRIES = 3
RETRY_BASE_DELAY = 5.0  # seconds, doubles each attempt


class ChapterDownloader:
    def __init__(self, page: Page, state: ScrapeState, output_dir: Path, exporters: list[ChapterExporter]):
        self.page = page
        self.state = state
        self.output_dir = Path(output_dir)
        self.exporters = exporters
        self.chapters_dir = self.output_dir / "chapters"

        self.chapters_dir.mkdir(parents=True, exist_ok=True)

    async def download_chapter(self, url: str, filename_base: str):
        """Download a single chapter with retry logic using the configured exporters."""
        last_error: Exception | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = await self.page.goto(url, wait_until="domcontentloaded")
                
                if response is not None and not response.ok:
                    raise Exception(f"HTTP Error {response.status}: {response.status_text} for {url}")
                
                # Wait for content to render
                await self.page.wait_for_timeout(3000)
                
                saved_paths = []
                for exporter in self.exporters:
                    saved_filename = await exporter.export(self.page, self.chapters_dir, filename_base)
                    saved_paths.append(saved_filename)
                    
                return saved_paths  # success
            except (PlaywrightTimeout, Exception) as exc:
                last_error = exc
                if attempt < MAX_RETRIES:
                    delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                    console.print(
                        f"  [yellow]⚠ Attempt {attempt}/{MAX_RETRIES} failed: {exc}[/yellow]"
                    )
                    console.print(f"  [dim]Retrying in {delay:.0f}s...[/dim]")
                    await asyncio.sleep(delay)

        # All retries exhausted
        raise last_error  # type: ignore[misc]

    async def download_all(self, progress_manager: Progress = None, parent_task=None):
        """Download all pending/failed chapters with a progress bar."""
        total = len(self.state.chapters)
        already_done = sum(
            1 for c in self.state.chapters if c.status == ChapterStatus.DOWNLOADED
        )
        failed_count = 0

        # Create a progress context if none provided
        if progress_manager is None:
            progress_context = Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TextColumn("({task.completed}/{task.total})"),
                TimeElapsedColumn(),
                console=console,
            )
        else:
            # We don't want to close an external manager
            from contextlib import nullcontext
            progress_context = nullcontext(progress_manager)

        with progress_context as progress:
            task = progress.add_task("Downloading chapters", total=total, completed=already_done)
            # Link to parent if provided (requires TaskID)
            # Note: parent support in rich is via add_task(..., parent=parent_task)
            # but we'll just use the provided progress instance.

            for idx, chapter in enumerate(self.state.chapters):
                if chapter.status == ChapterStatus.DOWNLOADED:
                    continue

                slug = chapter.url.split("/")[-1]
                progress.update(task, description=f"[bold blue]Ch {idx}: {slug}")

                book_name = self.output_dir.name
                filename_base = f"{book_name}_chapter_{idx:03d}"
                try:
                    saved_paths = await self.download_chapter(chapter.url, filename_base)
                    chapter.status = ChapterStatus.DOWNLOADED
                    for saved_path in saved_paths:
                        if saved_path.endswith(".pdf"):
                            chapter.pdf_path = f"chapters/{saved_path}"
                        elif saved_path.endswith(".md"):
                            chapter.markdown_path = f"chapters/{saved_path}"
                except Exception as exc:
                    chapter.status = ChapterStatus.FAILED
                    failed_count += 1
                    progress.console.print(
                        f"\n  [bold red]✗ Chapter {idx} ({slug}) failed "
                        f"after {MAX_RETRIES} retries: {exc}[/bold red]"
                    )

                # Persist state after every chapter
                state_path = self.output_dir / "state.json"
                save_state(self.state, state_path)
                progress.advance(task)

                # Polite delay between chapters
                if idx < total - 1:
                    delay = random.uniform(5.0, 15.0)
                    await asyncio.sleep(delay)

        # Cleanup: Remove the nested book task if we're in a playlist
        if progress_manager is not None:
            progress_manager.remove_task(task)

        # Summary
        downloaded = sum(1 for c in self.state.chapters if c.status == ChapterStatus.DOWNLOADED)
        console.print(f"\n[bold green]✓ Downloaded:[/bold green] {downloaded}/{total}")
        if failed_count:
            console.print(f"[bold red]✗ Failed:[/bold red] {failed_count}/{total}")
