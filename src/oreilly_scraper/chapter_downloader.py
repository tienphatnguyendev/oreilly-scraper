import asyncio
import logging
import random
from pathlib import Path
from playwright.async_api import Page
from .state import ScrapeState, ChapterStatus, save_state

logger = logging.getLogger(__name__)


class ChapterDownloader:
    def __init__(self, page: Page, state: ScrapeState, output_dir: Path):
        self.page = page
        self.state = state
        self.output_dir = Path(output_dir)
        self.chapters_dir = self.output_dir / "chapters"
        
        self.chapters_dir.mkdir(parents=True, exist_ok=True)

    async def download_chapter(self, url: str, filename: str):
        logger.info(f"Navigating to {url}")
        await self.page.goto(url, wait_until="networkidle")
        
        pdf_path = self.chapters_dir / filename
        logger.info(f"Saving PDF to {pdf_path}")
        await self.page.pdf(path=str(pdf_path))

    async def download_all(self):
        """
        Downloads all pending chapters found in self.state
        """
        for idx, chapter in enumerate(self.state.chapters):
            if chapter.status == ChapterStatus.DOWNLOADED:
                logger.info(f"Skipping already downloaded chapter: {chapter.url}")
                continue

            filename = f"chapter_{idx:03d}.pdf"
            await self.download_chapter(chapter.url, filename)

            # Update state
            chapter.status = ChapterStatus.DOWNLOADED
            chapter.pdf_path = f"chapters/{filename}"
            
            state_path = self.output_dir / "state.json"
            save_state(self.state, state_path)

            if idx < len(self.state.chapters) - 1:
                delay = random.uniform(30.0, 60.0)
                logger.info(f"Sleeping for {delay:.2f} seconds before next chapter...")
                await asyncio.sleep(delay)
