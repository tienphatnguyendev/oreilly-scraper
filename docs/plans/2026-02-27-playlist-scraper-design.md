# Playlist Batch Scraper Design

## Overview
A new feature to process an entire O'Reilly playlist JSON file and download all associated books. This design prioritizes avoiding bot detection and rate limits by reusing a single browser session and introducing significant delays between book downloads.

## Architecture & Data Flow
1. **New CLI Command:** A `scrape-playlist` command will be added to `__main__.py`.
2. **Session Management:** Playwright will be launched once, apply stealth, inject cookies, and authenticate at the start of the playlist run. This `page` object will be passed down to individual book scraping tasks.
3. **Iteration:** The script reads the playlist JSON, filters for `format == "book"`, and iterates through the list.
4. **State Check Shortcut:** Before navigating to a book's table of contents, the script will check if `state.json` exists in the book's output directory and if all chapters are marked as `DOWNLOADED`. If true, the book is skipped entirely without any web requests.
5. **Book Scraping:** The core scraping logic currently in `_run_scrape` will be refactored into `_scrape_single_book(page, config)`, which processes a single book given a reusable page and a book-specific configuration.

## Bot Detection & Rate Limiting
1. **Inter-Chapter Delays:** Retain the existing random delays between downloading individual chapters (e.g., 5-15 seconds).
2. **Inter-Book Delays:** Introduce a longer delay between books. After finishing a book, wait for a random duration (e.g., 30 to 90 seconds) before starting the next.
3. **Persistent Context:** Reusing the Playwright session avoids triggering anomalies from rapidly launching and closing Chromium instances.

## Error Handling & Resiliency
1. **Isolated Failures:** Each book's scraping process is wrapped in a `try...except` block. Failures on a specific book (e.g., max retries exceeded, formatting issues) will be logged, and the script will continue to the next book.
2. **End of Run Summary:** The CLI will output a final summary showing successful, skipped, and failed books.

## Output Structure & Formats
1. **Folder Hierarchy:** Output will be nested by playlist ID: `output/<playlist_id>/<book_slug>/chapters/`.
2. **Markdown Check:** Output formats (e.g., Markdown) will be driven by `config.json`. The user is expected to have `"markdown"` configured in the `formats` array to save chapters as Markdown.