import json
from pathlib import Path
from scripts.reorganize_output import reorganize_directory

def test_reorganize_directory(tmp_path):
    # Setup mock structure
    output_dir = tmp_path / "output"
    playlist_dir = output_dir / "playlist-1"
    book_dir = playlist_dir / "1234567890"
    chapters_dir = book_dir / "chapters"
    chapters_dir.mkdir(parents=True)
    
    # Mock files
    (chapters_dir / "chapter_001.md").write_text("# Chapter 1")
    
    state_data = {
        "book_url": "https://learning.oreilly.com/library/view/test-book/1234567890/",
        "total_chapters": 1,
        "chapters": [{"markdown_path": "chapters/chapter_001.md"}]
    }
    (book_dir / "state.json").write_text(json.dumps(state_data))

    # Run reorganization
    reorganize_directory(output_dir)

    # Verify new structure
    expected_book_dir = output_dir / "test-book"
    assert expected_book_dir.exists()
    assert (expected_book_dir / "chapter_001.md").exists()
    assert not chapters_dir.exists()
    
    # Verify state.json is updated
    new_state = json.loads((expected_book_dir / "state.json").read_text())
    assert new_state["chapters"][0]["markdown_path"] == "chapter_001.md"
