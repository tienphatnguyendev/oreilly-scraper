# O'Reilly PDF Downloader - Specification

## Overview
A locally-run Python tool designed to download books from O'Reilly Learning as high-quality, single PDF files with formatting preserved. The tool operates semi-manually (using manually updated cookies) to bypass complex authentication flows and relies on a headless Playwright instance with stealth capabilities to prevent bot detection.

## Key Features & Requirements
1. **Single PDF Output**: The script will consolidate all chapters into a single PDF located at `/Users/aaronng/Documents/books/<Book Name>/<Book Name>.pdf`.
2. **Formatting Preservation**: The downloaded PDF must retain original visual formatting (fonts, code blocks, images).
3. **Configuration Driven**: Target Book URL and manually-updated cookies are read from a local `config.json`.
4. **Stealth & Headless**: Runs in the background (headless mode) using `playwright-stealth`.
5. **Rate-Limit Evasion**: Introduces a randomized 30 to 60-second delay between chapter fetches to avoid IP bans or rate limits.
6. **Resumable State**: Downloads are tracked in a `state.json` file. If interrupted, the script picks up where it left off instead of restarting.
7. **Progress Tracking**: A console-based progress bar indicates exact progress, based on the Table of Contents fetched initially.

## Architecture
- **Language**: Python 3.x
- **Core Automation**: `playwright` (with `playwright-stealth` plugin)
- **PDF Manipulation**: `PyPDF2` or `pypdf` for final merging
- **CLI Feedback**: `tqdm` or `rich` for progress visualization

## Task Breakdown (One Feature Per Task)
- **Task 1: Project Setup & Settings Parsing**: Scaffold the project, configure `pyproject.toml`, parse `config.json`.
- **Task 2: Playwright Stealth Setup & Auth**: Initialize browser state, inject cookies, verify connection to `learning.oreilly.com`.
- **Task 3: Table of Contents Extractor**: Fetch book TOC, evaluate total chapters, set up `state.json`.
- **Task 4: Chapter Downloader & Resumability**: Download loop with anti-bot delay, saving individual PDFs sequentially.
- **Task 5: PDF Consolidation**: Logic to sew individual PDFs into the master PDF and save to the correct destination directory.
- **Task 6: CLI & Progress UI**: Add the terminal aesthetics (progress bar) and wrap up error handling.
