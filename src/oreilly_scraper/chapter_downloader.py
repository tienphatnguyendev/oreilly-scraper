import asyncio
import random
from pathlib import Path

from playwright.async_api import Page, TimeoutError as PlaywrightTimeout
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn

from .state import ScrapeState, ChapterStatus, save_state

console = Console()

MAX_RETRIES = 3
RETRY_BASE_DELAY = 5.0  # seconds, doubles each attempt

# CSS injected before each PDF to hide sidebar/navbar and expand content
_FULLWIDTH_CSS = """
/* Hide O'Reilly navigation, sidebar, header, and footer */
nav, header, footer,
[class*="SiteHeader"], [class*="siteHeader"],
[class*="Sidebar"], [class*="sidebar"],
[class*="LeftColumn"], [class*="leftColumn"],
[class*="toc"], [class*="Toc"],
[class*="_tocScrollWrapper"],
[class*="annotator"],
[class*="Annotator"],
[data-testid="left-column"],
[data-testid="site-header"],
[class*="MuiDrawer"],
[class*="MuiAppBar"] {
    display: none !important;
}

/* Expand the content/reader area to full page width */
[class*="RightColumn"], [class*="rightColumn"],
[class*="reader"], [class*="Reader"],
[class*="contentArea"], [class*="ContentArea"],
main, article,
[data-testid="right-column"] {
    margin: 0 !important;
    padding: 0 2rem !important;
    max-width: 100% !important;
    width: 100% !important;
    flex: 1 !important;
}

/* Remove grid/flex constraints on parent containers */
[class*="ContentLayout"], [class*="contentLayout"],
[class*="Layout"], [class*="Container"] {
    display: block !important;
    max-width: 100% !important;
}

/* Ensure body is full width */
body {
    overflow: visible !important;
    max-width: 100% !important;
}
"""


class ChapterDownloader:
    def __init__(self, page: Page, state: ScrapeState, output_dir: Path):
        self.page = page
        self.state = state
        self.output_dir = Path(output_dir)
        self.chapters_dir = self.output_dir / "chapters"

        self.chapters_dir.mkdir(parents=True, exist_ok=True)

    async def _inject_pdf_styles(self):
        """Inject CSS to hide sidebar/nav and make content full-width for clean PDF."""
        await self.page.add_style_tag(content=_FULLWIDTH_CSS)

    async def download_chapter(self, url: str, filename: str):
        """Download a single chapter with retry logic."""
        last_error: Exception | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                await self.page.goto(url, wait_until="domcontentloaded")
                # Wait for content to render
                await self.page.wait_for_timeout(3000)
                # Inject CSS for clean full-width PDF
                await self._inject_pdf_styles()
                await self.page.wait_for_timeout(500)

                pdf_path = self.chapters_dir / filename
                await self.page.pdf(path=str(pdf_path))
                return  # success
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

    async def download_all(self):
        """Download all pending/failed chapters with a progress bar."""
        total = len(self.state.chapters)
        already_done = sum(
            1 for c in self.state.chapters if c.status == ChapterStatus.DOWNLOADED
        )
        failed_count = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("({task.completed}/{task.total})"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Downloading chapters", total=total, completed=already_done)

            for idx, chapter in enumerate(self.state.chapters):
                if chapter.status == ChapterStatus.DOWNLOADED:
                    continue

                slug = chapter.url.split("/")[-1]
                progress.update(task, description=f"[bold blue]Ch {idx}: {slug}")

                filename = f"chapter_{idx:03d}.pdf"
                try:
                    await self.download_chapter(chapter.url, filename)
                    chapter.status = ChapterStatus.DOWNLOADED
                    chapter.pdf_path = f"chapters/{filename}"
                except Exception as exc:
                    chapter.status = ChapterStatus.FAILED
                    failed_count += 1
                    console.print(
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

        # Summary
        downloaded = sum(1 for c in self.state.chapters if c.status == ChapterStatus.DOWNLOADED)
        console.print(f"\n[bold green]✓ Downloaded:[/bold green] {downloaded}/{total}")
        if failed_count:
            console.print(f"[bold red]✗ Failed:[/bold red] {failed_count}/{total}")
