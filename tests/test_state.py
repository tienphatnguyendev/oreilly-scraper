import pytest
from pathlib import Path
from pydantic import ValidationError
from oreilly_scraper.state import ScrapeState, ChapterState, ChapterStatus, load_state, save_state

def test_chapter_state_defaults():
    chapter = ChapterState(url="https://example.com/ch1")
    assert chapter.status == ChapterStatus.PENDING
    assert chapter.pdf_path is None
    assert chapter.markdown_path is None


def test_scrape_state_serialization(tmp_path):
    state_file = tmp_path / "state.json"
    
    chapters = [
        ChapterState(url="https://example.com/ch1", status=ChapterStatus.DOWNLOADED, pdf_path="/tmp/ch1.pdf"),
        ChapterState(url="https://example.com/ch2", status=ChapterStatus.DOWNLOADED, markdown_path="/tmp/ch2.md"),
        ChapterState(url="https://example.com/ch3")
    ]
    
    state = ScrapeState(
        book_url="https://example.com/book",
        total_chapters=3,
        chapters=chapters
    )
    
    # Save state
    save_state(state, state_file)
    assert state_file.exists()
    
    # Load state
    loaded_state = load_state(state_file)
    
    assert str(loaded_state.book_url).rstrip("/") == "https://example.com/book"
    assert loaded_state.total_chapters == 3
    assert len(loaded_state.chapters) == 3
    
    assert loaded_state.chapters[0].status == ChapterStatus.DOWNLOADED
    assert loaded_state.chapters[0].pdf_path == "/tmp/ch1.pdf"
    assert loaded_state.chapters[0].markdown_path is None
    
    assert loaded_state.chapters[1].status == ChapterStatus.DOWNLOADED
    assert loaded_state.chapters[1].pdf_path is None
    assert loaded_state.chapters[1].markdown_path == "/tmp/ch2.md"

    assert loaded_state.chapters[2].status == ChapterStatus.PENDING

def test_load_state_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_state(tmp_path / "nonexistent.json")

def test_invalid_state_data_raises():
    with pytest.raises(ValidationError):
        # Missing total_chapters
        ScrapeState(
            book_url="https://example.com/book",
            chapters=[]
        )
