import pytest
from unittest.mock import patch, MagicMock
from scripts.enrich_with_llm import check_api_health, has_frontmatter, extract_metadata, MetadataResponse

@patch("scripts.enrich_with_llm.Groq")
def test_check_api_health_success(mock_groq_class):
    mock_client = MagicMock()
    mock_groq_class.return_value = mock_client
    # Mocking a successful models.list call
    mock_client.models.list.return_value = MagicMock()
    
    assert check_api_health("fake_key") is True

@patch("scripts.enrich_with_llm.Groq")
def test_check_api_health_failure(mock_groq_class):
    mock_client = MagicMock()
    mock_groq_class.return_value = mock_client
    mock_client.models.list.side_effect = Exception("API down")
    
    assert check_api_health("fake_key") is False

def test_has_frontmatter():
    content_with_fm = "---\ntitle: test\n---\n# Chapter 1"
    content_without_fm = "# Chapter 1\nContent goes here"
    
    assert has_frontmatter(content_with_fm) is True
    assert has_frontmatter(content_without_fm) is False

@patch("scripts.enrich_with_llm.Groq")
def test_extract_metadata(mock_groq_class):
    mock_client = MagicMock()
    mock_groq_class.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.choices[0].message.content = '{"semantic_filename": "01-introduction-to-aws", "chapter_title": "Introduction to AWS"}'
    mock_client.chat.completions.create.return_value = mock_response
    
    result = extract_metadata("# Chapter 1. Introduction to AWS\nBlah", "api_key")
    
    assert isinstance(result, MetadataResponse)
    assert result.semantic_filename == "01-introduction-to-aws"
    assert result.chapter_title == "Introduction to AWS"