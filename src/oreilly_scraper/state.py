from enum import Enum
from pathlib import Path
from typing import List, Optional, Union
from pydantic import BaseModel, HttpUrl

class ChapterStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADED = "downloaded"
    FAILED = "failed"

class ChapterState(BaseModel):
    url: str
    status: ChapterStatus = ChapterStatus.PENDING
    pdf_path: Optional[str] = None
    markdown_path: Optional[str] = None

class ScrapeState(BaseModel):
    book_url: HttpUrl
    total_chapters: int
    chapters: List[ChapterState]

def load_state(state_path: Union[str, Path]) -> ScrapeState:
    path = Path(state_path)
    if not path.exists():
        raise FileNotFoundError(f"State file not found: {state_path}")
    
    with open(path, "r", encoding="utf-8") as f:
        # We can parse raw json directly into the Pydantic model
        return ScrapeState.model_validate_json(f.read())

def save_state(state: ScrapeState, state_path: Union[str, Path]) -> None:
    path = Path(state_path)
    # Write beautifully formatted JSON
    with open(path, "w", encoding="utf-8") as f:
        f.write(state.model_dump_json(indent=2))
