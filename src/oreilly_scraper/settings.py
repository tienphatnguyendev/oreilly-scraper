import json
from enum import Enum
from pathlib import Path
from pydantic import BaseModel, HttpUrl, field_validator


class ExportFormat(str, Enum):
    PDF = "pdf"
    MARKDOWN = "markdown"


class Cookie(BaseModel):
    name: str
    value: str
    domain: str
    path: str = "/"


class Settings(BaseModel):
    book_url: HttpUrl
    cookies: list[Cookie]
    output_dir: Path
    formats: list[ExportFormat] = [ExportFormat.PDF]

    @field_validator("formats")
    @classmethod
    def formats_not_empty(cls, v: list) -> list:
        if not v:
            raise ValueError("formats list must not be empty")
        return list(set(v))  # Remove duplicates if any

    @field_validator("cookies")
    @classmethod
    def cookies_not_empty(cls, v: list) -> list:
        if not v:
            raise ValueError("cookies list must not be empty")
        return v


def load_config(config_path: str = "config.json") -> Settings:
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(path, "r") as f:
        data = json.load(f)
    return Settings(**data)
