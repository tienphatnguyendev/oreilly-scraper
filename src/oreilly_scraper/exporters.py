from abc import ABC, abstractmethod
from pathlib import Path
from playwright.async_api import Page
import markdownify
from bs4 import BeautifulSoup
from rich.console import Console

console = Console()

class ChapterExporter(ABC):
    @abstractmethod
    async def export(self, page: Page, output_dir: Path, filename_base: str) -> str:
        """
        Exports the chapter from the given page to the output directory.
        Returns the filename (with extension) that was saved.
        """
        pass

class PdfExporter(ChapterExporter):
    """
    Exports a chapter as a PDF by injecting CSS to hide site nav and printing to PDF.
    """
    # Use the same CSS block previously defined in chapter_downloader.py
    _FULLWIDTH_CSS = """
        /* Hide O'Reilly navigation, sidebar, header, and footer */
        nav, header, footer,
        [class*="SiteHeader"], [class*="siteHeader"],
        [class*="Sidebar"], [class*="sidebar"],
        [id*="sidebar"], [id*="nav"],
        .sbo-site-nav, .js-sbo-top-nav,
        .interface-controls {
            display: none !important;
            visibility: hidden !important;
            opacity: 0 !important;
            height: 0 !important;
            width: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
            position: absolute !important;
            overflow: hidden !important;
        }

        /* Force main content area to take full width and height */
        main, article, [class*="contentArea"], [class*="ContentArea"],
        .t-main-content, #main-content,
        .sbo-reading-content {
            width: 100% !important;
            max-width: 100% !important;
            margin: 0 !important;
            padding: 20px !important;
            position: relative !important;
            left: 0 !important;
            right: 0 !important;
            top: 0 !important;
            box-sizing: border-box !important;
            float: none !important;
        }

        /* Reset body and html to avoid scrollbars and extra margins */
        body, html {
            width: 100% !important;
            height: auto !important;
            margin: 0 !important;
            padding: 0 !important;
            overflow: visible !important;
            background: white !important;
        }

        /* Prevent content from being shifted by any remaining hidden elements */
        * {
            box-sizing: border-box !important;
        }
    """

    async def export(self, page: Page, output_dir: Path, filename_base: str) -> str:
        pdf_filename = f"{filename_base}.pdf"
        pdf_path = output_dir / pdf_filename
        
        # Inject CSS to hide menus and make content full width
        await page.add_style_tag(content=self._FULLWIDTH_CSS)
        
        # Print to PDF
        await page.pdf(path=str(pdf_path))
        
        return pdf_filename

class MarkdownExporter(ChapterExporter):
    """
    Exports a chapter as Markdown by extracting the inner HTML of the content area 
    and using markdownify to convert it.
    """
    
    # Selectors to remove before converting to Markdown
    _EXCLUDE_SELECTORS = [
        "nav", "header", "footer", 
        "[class*='SiteHeader']", "[class*='siteHeader']", 
        "[class*='Sidebar']", "[class*='sidebar']", 
        "[id*='sidebar']", "[id*='nav']", 
        ".sbo-site-nav", ".js-sbo-top-nav", 
        ".interface-controls"
    ]

    async def export(self, page: Page, output_dir: Path, filename_base: str) -> str:
        md_filename = f"{filename_base}.md"
        md_path = output_dir / md_filename
        
        # Best selectors found via investigation: article is the semantic container
        target_selector = 'article, [class*="contentSection"], .chapter'
        
        try:
            # Wait for the content to actually appear in the DOM
            await page.wait_for_selector(target_selector, timeout=15000)
            # Give a tiny bit more for sub-content if any
            await page.wait_for_timeout(1000)
            
            # Extract HTML
            content_html = await page.inner_html(target_selector)
            
            if not content_html or len(content_html.strip()) < 100:
                raise Exception(f"Content extraction for {filename_base} returned very little data ({len(content_html) if content_html else 0} chars).")
        except Exception as e:
            raise Exception(f"Failed to extract content for {filename_base}: {e}")

        # Parse HTML with BeautifulSoup to remove unwanted navigation elements
        soup = BeautifulSoup(content_html, "html.parser")
        for selector in self._EXCLUDE_SELECTORS:
            for element in soup.select(selector):
                element.decompose()
                
        cleaned_html = str(soup)
        
        # Convert to Markdown
        md_content = markdownify.markdownify(
            cleaned_html, 
            heading_style="ATX", 
            escape_asterisks=False,
            escape_underscores=False,
            wrap=True,
            wrap_width=80
        )
        
        if not md_content or len(md_content.strip()) < 10:
             raise Exception(f"Markdown conversion resulted in empty content for {filename_base}.")

        # Save to file
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        
        return md_filename
