# TOC Extraction Bug Design

**Problem Context:**
O'Reilly scraper is failing to extract TOC on certain books loaded with the shorthand `/library/view/-/<ISBN>/`. The scraper gets 0 chapter links because the Playwright evaluation script filters `href.includes(bookPath)` where `bookPath` uses the `/-/` shorthand, but the DOM's React-rendered links use the canonical slug `/library/view/pci-dss-version/<ISBN>/xhtml/...`.

## Proposed Solution: Filter Links by Book ID (ISBN)
Since all O'Reilly book URLs consistently end in `<ISBN>/` (the 13-digit number), the simplest and robust solution is to extract the book ID and filter `href.includes(bookId)` instead of the full URL path. 

### Approach Trade-offs

**Alternative considered:** Force Playwright to wait for Canonical Redirect
Wait until `page.url` updates and does NOT contain `/-/` before fetching the TOC.
* **Pros**: Keeps the `bookPath` logic exactly intact.
* **Cons**: Brittle. O'Reilly might be migrating to single-page app (SPA) routing where the URL bar doesn't immediately reflect the canonical slug, leading to unnecessary timeouts.

**Selected Approach: Filter by Book ID (ISBN)**
Extract the Book ID (the last segment of the URL, e.g., `9781787785090`) and check if `href.includes(book_id)`.
* **Pros**: Incredibly robust. It works seamlessly whether the URL has the canonical slug or the `/-/` shorthand. No timeouts.
* **Cons**: Marginally less strict, practically impossible to have false positives.

## Required Changes
1. `src/oreilly_scraper/toc.py`:
   - Parse `page.url` (or `book_url`) to extract the final path segment resolving to the Book ID (ISBN).
   - Substitute `bookPath` with `bookId` in the `page.evaluate` script.
   
```python
    current_url = page.url
    # e.g., /library/view/-/9781787785090
    book_id = [p for p in urlparse(current_url).path.split('/') if p][-1]
```
```javascript
        return Array.from(document.querySelectorAll('a.orm-Link-root'))
            .map(a => a.getAttribute('href'))
            .filter(href => href && href.includes(bookId) && href.endsWith('.html'))
```
