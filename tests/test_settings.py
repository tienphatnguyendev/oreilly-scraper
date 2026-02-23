import json
import pytest
from pydantic import ValidationError
from oreilly_scraper.settings import load_config, Settings


def test_load_valid_config_returns_settings(tmp_path):
    config = {
        "book_url": "https://learning.oreilly.com/library/view/test/9781234567890/",
        "cookies": [{"name": "session", "value": "abc", "domain": ".oreilly.com", "path": "/"}],
        "output_dir": str(tmp_path),
        "formats": ["pdf", "markdown"]
    }
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps(config))
    result = load_config(str(cfg_file))
    assert isinstance(result, Settings)
    assert str(result.book_url).startswith("https://learning.oreilly.com")


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


def test_load_invalid_format_raises(tmp_path):
    config = {
        "book_url": "https://learning.oreilly.com/library/view/test/9781234567890/",
        "cookies": [{"name": "s", "value": "v", "domain": ".oreilly.com", "path": "/"}],
        "output_dir": str(tmp_path),
        "formats": ["invalid_format"]
    }
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps(config))
    with pytest.raises(ValidationError):
        load_config(str(cfg_file))


def test_load_empty_format_raises(tmp_path):
    config = {
        "book_url": "https://learning.oreilly.com/library/view/test/9781234567890/",
        "cookies": [{"name": "s", "value": "v", "domain": ".oreilly.com", "path": "/"}],
        "output_dir": str(tmp_path),
        "formats": []
    }
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps(config))
    with pytest.raises(ValidationError):
        load_config(str(cfg_file))


def test_load_defaults_to_pdf_format_if_omitted(tmp_path):
    config = {
        "book_url": "https://learning.oreilly.com/library/view/test/9781234567890/",
        "cookies": [{"name": "session", "value": "abc", "domain": ".oreilly.com", "path": "/"}],
        "output_dir": str(tmp_path),
    }
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps(config))
    result = load_config(str(cfg_file))
    from oreilly_scraper.settings import ExportFormat
    assert result.formats == [ExportFormat.PDF]
