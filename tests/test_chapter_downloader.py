import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from oreilly_scraper.chapter_downloader import ChapterDownloader
from oreilly_scraper.state import ScrapeState, ChapterState, ChapterStatus


@pytest.fixture
def mock_page():
    return AsyncMock()

@pytest.fixture
def output_dir(tmp_path):
    return tmp_path

@pytest.fixture
def mock_state():
    return ScrapeState(book_url="http://example.com/book", total_chapters=0, chapters=[])

@pytest.fixture
def downloader(mock_page, mock_state, output_dir):
    return ChapterDownloader(page=mock_page, state=mock_state, output_dir=output_dir)

def test_downloader_init(downloader, mock_state, output_dir):
    assert downloader.output_dir == output_dir
    assert downloader.chapters_dir == output_dir / "chapters"
    assert downloader.state == mock_state
    assert downloader.chapters_dir.exists()

@pytest.mark.asyncio
async def test_download_chapter(downloader, mock_page, output_dir):
    url = "http://example.com/chapter1"
    filename = "01_chapter.pdf"
    await downloader.download_chapter(url, filename)
    mock_page.goto.assert_called_once_with(url, wait_until="networkidle")
    pdf_path = output_dir / "chapters" / filename
    mock_page.pdf.assert_called_once_with(path=str(pdf_path))

@pytest.mark.asyncio
@patch("oreilly_scraper.chapter_downloader.asyncio.sleep", new_callable=AsyncMock)
@patch("oreilly_scraper.chapter_downloader.random.uniform")
async def test_download_all_success(mock_uniform, mock_sleep, downloader, mock_page, output_dir, mock_state):
    mock_uniform.return_value = 42.0
    mock_state.chapters = [
        ChapterState(url="http://example.com/1", status=ChapterStatus.PENDING),
        ChapterState(url="http://example.com/2", status=ChapterStatus.PENDING),
        ChapterState(url="http://example.com/3", status=ChapterStatus.PENDING)
    ]
    mock_state.total_chapters = 3
    await downloader.download_all()
    assert mock_page.goto.call_count == 3
    assert mock_page.pdf.call_count == 3
    assert mock_sleep.call_count == 2
    mock_sleep.assert_called_with(42.0)
    assert all(c.status == ChapterStatus.DOWNLOADED for c in mock_state.chapters)
    assert mock_state.chapters[0].pdf_path == "chapters/chapter_000.pdf"
    assert mock_state.chapters[1].pdf_path == "chapters/chapter_001.pdf"
    assert mock_state.chapters[2].pdf_path == "chapters/chapter_002.pdf"

@pytest.mark.asyncio
@patch("oreilly_scraper.chapter_downloader.asyncio.sleep", new_callable=AsyncMock)
async def test_download_all_with_preexisting_state(mock_sleep, downloader, mock_page, output_dir, mock_state):
    mock_state.chapters = [
        ChapterState(url="http://example.com/1", status=ChapterStatus.DOWNLOADED, pdf_path="chapters/chapter_000.pdf"),
        ChapterState(url="http://example.com/2", status=ChapterStatus.PENDING)
    ]
    mock_state.total_chapters = 2
    await downloader.download_all()
    mock_page.goto.assert_called_once_with("http://example.com/2", wait_until="networkidle")
    mock_page.pdf.assert_called_once_with(path=str(output_dir / "chapters" / "chapter_001.pdf"))
    assert all(c.status == ChapterStatus.DOWNLOADED for c in mock_state.chapters)
    mock_sleep.assert_not_called()
