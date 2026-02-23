import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

from playwright.async_api import TimeoutError as PlaywrightTimeout

from oreilly_scraper.chapter_downloader import ChapterDownloader, MAX_RETRIES
from oreilly_scraper.exporters import ChapterExporter
from oreilly_scraper.state import ScrapeState, ChapterState, ChapterStatus


@pytest.fixture
def mock_page():
    page = AsyncMock()
    page.add_style_tag = AsyncMock()
    return page


@pytest.fixture
def output_dir(tmp_path):
    return tmp_path


@pytest.fixture
def mock_state():
    return ScrapeState(book_url="http://example.com/book", total_chapters=0, chapters=[])


class MockExporter(ChapterExporter):
    async def export(self, page, output_dir, filename_base):
        return f"{filename_base}.pdf"

@pytest.fixture
def mock_exporters():
    return [MockExporter()]

@pytest.fixture
def downloader(mock_page, mock_state, output_dir, mock_exporters):
    return ChapterDownloader(page=mock_page, state=mock_state, output_dir=output_dir, exporters=mock_exporters)


def test_downloader_init(downloader, mock_state, output_dir):
    assert downloader.output_dir == output_dir
    assert downloader.chapters_dir == output_dir / "chapters"
    assert downloader.state == mock_state
    assert downloader.chapters_dir.exists()


@pytest.mark.asyncio
async def test_download_chapter(downloader, mock_page, output_dir):
    url = "http://example.com/chapter1"
    filename_base = "01_chapter"
    saved_paths = await downloader.download_chapter(url, filename_base)
    mock_page.goto.assert_called_once_with(url, wait_until="domcontentloaded")
    assert saved_paths == ["01_chapter.pdf"]


@pytest.mark.asyncio
@patch("oreilly_scraper.chapter_downloader.asyncio.sleep", new_callable=AsyncMock)
@patch("oreilly_scraper.chapter_downloader.random.uniform")
async def test_download_all_success(mock_uniform, mock_sleep, downloader, mock_page, output_dir, mock_state):
    mock_uniform.return_value = 10.0
    mock_state.chapters = [
        ChapterState(url="http://example.com/1", status=ChapterStatus.PENDING),
        ChapterState(url="http://example.com/2", status=ChapterStatus.PENDING),
        ChapterState(url="http://example.com/3", status=ChapterStatus.PENDING),
    ]
    mock_state.total_chapters = 3
    await downloader.download_all()
    assert mock_page.goto.call_count == 3
    assert mock_sleep.call_count == 2  # delay between chapters only
    assert all(c.status == ChapterStatus.DOWNLOADED for c in mock_state.chapters)
    assert mock_state.chapters[0].pdf_path == "chapters/chapter_000.pdf"
    assert mock_state.chapters[1].pdf_path == "chapters/chapter_001.pdf"
    assert mock_state.chapters[2].pdf_path == "chapters/chapter_002.pdf"


@pytest.mark.asyncio
@patch("oreilly_scraper.chapter_downloader.asyncio.sleep", new_callable=AsyncMock)
async def test_download_all_skips_downloaded(mock_sleep, downloader, mock_page, output_dir, mock_state):
    mock_state.chapters = [
        ChapterState(url="http://example.com/1", status=ChapterStatus.DOWNLOADED, pdf_path="chapters/chapter_000.pdf"),
        ChapterState(url="http://example.com/2", status=ChapterStatus.PENDING),
    ]
    mock_state.total_chapters = 2
    await downloader.download_all()
    mock_page.goto.assert_called_once_with("http://example.com/2", wait_until="domcontentloaded")
    assert all(c.status == ChapterStatus.DOWNLOADED for c in mock_state.chapters)
    # No sleep expected since download is the last chapter
    mock_sleep.assert_not_called()


@pytest.mark.asyncio
@patch("oreilly_scraper.chapter_downloader.asyncio.sleep", new_callable=AsyncMock)
async def test_download_chapter_retries_on_timeout(mock_sleep, downloader, mock_page, output_dir):
    """Chapter download retries on PlaywrightTimeout then succeeds."""
    call_count = 0

    async def flaky_goto(url, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise PlaywrightTimeout("Timeout 30000ms exceeded")

    mock_page.goto.side_effect = flaky_goto

    await downloader.download_chapter("http://example.com/ch1", "chapter_000")

    assert call_count == 2  # Failed once, then succeeded


@pytest.mark.asyncio
@patch("oreilly_scraper.chapter_downloader.asyncio.sleep", new_callable=AsyncMock)
async def test_download_all_marks_failed_after_retries(mock_sleep, downloader, mock_page, output_dir, mock_state):
    """Chapter marked FAILED after MAX_RETRIES exhausted, other chapters continue."""
    mock_page.goto.side_effect = PlaywrightTimeout("Timeout 30000ms exceeded")

    mock_state.chapters = [
        ChapterState(url="http://example.com/1", status=ChapterStatus.PENDING),
    ]
    mock_state.total_chapters = 1
    await downloader.download_all()

    assert mock_state.chapters[0].status == ChapterStatus.FAILED
    assert mock_page.goto.call_count == MAX_RETRIES
