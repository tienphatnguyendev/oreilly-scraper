# SOLO-28: Design — Playwright Stealth & Authentication

## Summary

This module builds the browser bootstrapping layer on top of the `settings.py` config loader from SOLO-27.

## Module: `browser.py`

**Public API:** `async create_authenticated_page(settings: Settings) -> Page`

### Flow

```
load_config() → Settings
  └─► create_authenticated_page(settings)
        1. Launch headless Chromium
        2. Apply playwright-stealth to context
        3. Inject cookies from settings.cookies
        4. Navigate to https://learning.oreilly.com/home/
        5. Check URL for /login redirect
           ├─ authenticated → return Page
           └─ NOT authenticated →
                ├─ print ⚠️  prompt (rich console)
                ├─ input() ← blocks for user, reloads config.json
                └─ retry from step 3
```

## Auth Check Strategy

- Navigate to `https://learning.oreilly.com/home/`
- If the final `page.url` contains `/login` or `/sign-in` → session is invalid.

## Cookie Format

`settings.cookies` is `list[Cookie]` (Pydantic model). Playwright's `add_cookies` requires dicts with keys: `name`, `value`, `domain`, `path`. `Cookie.model_dump()` produces exactly this.

## TDD Plan

| Test | Input | Expected |
|---|---|---|
| `test_cookies_injected` | settings with 1 cookie | `add_cookies` called with correct dict |
| `test_stealth_applied` | any settings | `stealth_async` called on context |
| `test_valid_session_returns_page` | page.url = `oreilly.com/home/` | returns page |
| `test_invalid_then_valid_retries` | 1st url = `/login`, 2nd = `/home/` | input() called, returns page on 2nd try |
