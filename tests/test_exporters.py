import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch

class MockPage:
    def __init__(self):
        self.pdf = AsyncMock()
        self.inner_html = AsyncMock(return_value="""
        <div class="contentArea">
            <h1>Test Chapter</h1>
            <p>This is a paragraph.</p>
            <pre><code>print("hello world")</code></pre>
            <img src="https://example.com/image.jpg" alt="test image" />
            <a href="https://example.com/link">Link</a>
        </div>
        """)
        self.add_style_tag = AsyncMock()

@pytest.fixture
def mock_page():
    return MockPage()

@pytest.mark.asyncio
async def test_pdf_exporter(mock_page, tmp_path):
    from oreilly_scraper.exporters import PdfExporter
    
    exporter = PdfExporter()
    output_path = tmp_path
    
    saved_file = await exporter.export(mock_page, output_path, "test_chapter")
    
    assert saved_file == "test_chapter.pdf"
    mock_page.add_style_tag.assert_awaited_once()
    mock_page.pdf.assert_awaited_once_with(path=str(output_path / "test_chapter.pdf"))

@pytest.mark.asyncio
async def test_markdown_exporter_converts_html_to_markdown(mock_page, tmp_path):
    from oreilly_scraper.exporters import MarkdownExporter
    
    exporter = MarkdownExporter()
    output_path = tmp_path
    
    saved_file = await exporter.export(mock_page, output_path, "test_chapter")
    
    assert saved_file == "test_chapter.md"
    
    # Check if file was written
    result_file = output_path / "test_chapter.md"
    assert result_file.exists()
    
    # Read the content and verify conversion
    content = result_file.read_text("utf-8")
    
    # Check headers
    assert "# Test Chapter" in content
    # Check paragraphs
    assert "This is a paragraph." in content
    # Check code blocks
    assert "```" in content
    assert 'print("hello world")' in content
    # Check images
    assert "![test image](https://example.com/image.jpg)" in content
    # Check links
    assert "[Link](https://example.com/link)" in content
    
    # Verify inner_html was called with the correct selector
    mock_page.inner_html.assert_awaited_once_with('main, article, [class*="contentArea"]')
