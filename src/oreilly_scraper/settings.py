import json
from pathlib import Path
from pydantic import BaseModel, HttpUrl, field_validator


class Cookie(BaseModel):
    name: str
    value: str
    domain: str
    path: str = "/"


class Settings(BaseModel):
    book_url: HttpUrl
    cookies: list[Cookie]
    output_dir: Path

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
