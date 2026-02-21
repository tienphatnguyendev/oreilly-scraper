# Setup Project & Parse Configuration — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the raw-dict config loader with a validated Pydantic `Settings` model and cover it with a strict TDD pytest suite.

**Architecture:** A `Settings` Pydantic v2 BaseModel in `settings.py` validates all required fields (URL, cookies, output dir) at load time. Tests use `tmp_path` — no real files touched outside the test run.

**Tech Stack:** Python 3.10+, Pydantic v2, pytest 8

---

## Task 1: Scaffold the test file with one failing test (RED)

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/test_settings.py`

**Step 1: Write the failing test**

```python
# tests/test_settings.py
import json
import pytest
from oreilly_scraper.settings import load_config, Settings

def test_load_valid_config_returns_settings(tmp_path):
    config = {
        "book_url": "https://learning.oreilly.com/library/view/test/9781234567890/",
        "cookies": [{"name": "session", "value": "abc", "domain": ".oreilly.com", "path": "/"}],
        "output_dir": str(tmp_path),
    }
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps(config))
    result = load_config(str(cfg_file))
    assert isinstance(result, Settings)
    assert str(result.book_url).startswith("https://learning.oreilly.com")
```

**Step 2: Run to verify RED**

```bash
cd .worktrees/solo-27-setup
python3 -m pytest tests/test_settings.py::test_load_valid_config_returns_settings -v
```

Expected: `FAILED` — `Settings` doesn't exist yet / `load_config` returns a dict.

---

## Task 2: Implement the Pydantic Settings model (GREEN)

**Files:**
- Modify: `src/oreilly_scraper/settings.py`
- Modify: `pyproject.toml` (add pydantic dependency)

**Step 1: Rewrite `settings.py`**

```python
# src/oreilly_scraper/settings.py
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
```

**Step 2: Add pydantic to `pyproject.toml`**

```toml
dependencies = [
    "playwright>=1.40.0",
    "playwright-stealth>=1.0.6",
    "pypdf>=4.0.0",
    "rich>=13.0.0",
    "pydantic>=2.0.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0.0", "pytest-cov>=5.0.0"]
```

**Step 3: Run to verify GREEN**

```bash
python3 -m pytest tests/test_settings.py::test_load_valid_config_returns_settings -v
```

Expected: `PASSED`

**Step 4: Commit**

```bash
git add src/oreilly_scraper/settings.py pyproject.toml tests/__init__.py tests/test_settings.py
git commit -m "feat(SOLO-27): add Pydantic Settings model with config loader"
```

---

## Task 3: Add error-case tests (RED → GREEN → commit)

**Files:**
- Modify: `tests/test_settings.py`

**Step 1: Add 4 failing tests**

```python
from pydantic import ValidationError

def test_load_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_config(str(tmp_path / "nonexistent.json"))

def test_load_missing_book_url_raises(tmp_path):
    config = {
        "cookies": [{"name": "s", "value": "v", "domain": ".oreilly.com", "path": "/"}],
        "output_dir": str(tmp_path),
    }
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps(config))
    with pytest.raises(ValidationError):
        load_config(str(cfg_file))

def test_load_invalid_url_raises(tmp_path):
    config = {
        "book_url": "not-a-url",
        "cookies": [{"name": "s", "value": "v", "domain": ".oreilly.com", "path": "/"}],
        "output_dir": str(tmp_path),
    }
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps(config))
    with pytest.raises(ValidationError):
        load_config(str(cfg_file))

def test_load_empty_cookies_raises(tmp_path):
    config = {
        "book_url": "https://learning.oreilly.com/library/view/test/9781234567890/",
        "cookies": [],
        "output_dir": str(tmp_path),
    }
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps(config))
    with pytest.raises(ValidationError):
        load_config(str(cfg_file))
```

**Step 2: Run to verify RED**

```bash
python3 -m pytest tests/test_settings.py -v
```

Expected: 4 new tests `FAILED` (or `ERROR`), 1 still passing.

**Step 3: Run all tests to verify GREEN (implementation already handles these)**

```bash
python3 -m pytest tests/test_settings.py -v
```

Expected: All 5 `PASSED`

**Step 4: Commit**

```bash
git add tests/test_settings.py
git commit -m "test(SOLO-27): add error-case coverage for Settings validation"
```

---

## Task 4: Update __main__.py to use typed Settings

**Files:**
- Modify: `src/oreilly_scraper/__main__.py`

**Step 1: Update to use Settings type**

```python
import sys
from rich.console import Console
from .settings import load_config, Settings

console = Console()

def main():
    console.print("[bold green]O'Reilly PDF Downloader[/bold green] initializing...")
    try:
        config: Settings = load_config()
        console.print(f"Loaded config for: [cyan]{config.book_url}[/cyan]")
        console.print(f"Cookies: [yellow]{len(config.cookies)} loaded[/yellow]")
        console.print(f"Output dir: [blue]{config.output_dir}[/blue]")
    except FileNotFoundError as e:
        console.print(f"[bold red]Config not found:[/bold red] {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

**Step 2: Run all tests (regression check)**

```bash
python3 -m pytest tests/ -v
```

Expected: All 5 `PASSED`

**Step 3: Commit**

```bash
git add src/oreilly_scraper/__main__.py
git commit -m "feat(SOLO-27): update __main__ to use typed Settings"
```

---

## Task 5: Update Linear issue status to In Progress, verify all tests pass

**Step 1: Run full suite**

```bash
python3 -m pytest tests/ -v --tb=short
```

Expected: 5 passed, 0 failed, 0 warnings

**Step 2: Update Linear issue SOLO-27 → In Progress**

Use the task-manager skill: `mcp_linear-mcp-server_update_issue` with `state: "In Progress"`.
