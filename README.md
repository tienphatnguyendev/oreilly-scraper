# O'Reilly PDF Downloader

A locally-run Python tool designed to download books from O'Reilly Learning as high-quality, single PDF files with formatting preserved.

## Setup

1. Install `uv` (e.g., `brew install uv`).
2. Run `uv sync` to initialize the virtual environment and dependencies.
3. Run `uv run playwright install chromium` to fetch browser binaries.
4. Provide `config.json` with the target `book_url` and valid `.oreilly.com` cookies.

## Usage

- Scrape a single book: `uv run oreilly-scraper scrape`
- Discover a playlist: `uv run oreilly-scraper discover <url>`
- Scrape an entire playlist: `uv run oreilly-scraper scrape-playlist playlists/<id>.json`
