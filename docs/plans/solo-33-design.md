# Design Document: O'Reilly PDF Downloader

## Problem Statement
O'Reilly Learning prevents easy offline access to high-quality PDFs. Existing tools often fail due to complex SSO/MFA.

## Proposed Solution
A Python-based tool using Playwright with `stealth` plugins to simulate a real user.
- **Auth**: Injected via browser cookies extracted from a live session.
- **Extraction**: Sequential chapter printing to PDF using Playwright's `pdf()` API.
- **Resilience**: `state.json` tracks progress to handle interruptions.
- **Safety**: Randomized delays (30-60s) between chapter loads.

## Architecture
- **Settings**: `.env` and `config.json` (for paths).
- **Automation**: Playwright (Headless Chromium).
- **PDF**: `pypdf` for merging.
- **UI**: Rich for terminal progress tracking.

## Hard Gate Requirements
- [x] Linear Issue: [SOLO-33](https://linear.app/aaron-solo/issue/SOLO-33/implement-oreilly-pdf-downloader)
- [ ] Approved Design
