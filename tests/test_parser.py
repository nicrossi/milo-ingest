import pytest
from unittest.mock import MagicMock, patch
from src.parser import DocumentParser

@pytest.fixture
def mock_converter():
    with patch("src.parser.DocumentConverter") as MockClass:
        # Setup the chain: converter.convert().document.export_to_markdown()
        mock_instance = MockClass.return_value
        mock_result = MagicMock()
        mock_result.document.export_to_markdown.return_value = "# Test Header\nContent"
        mock_instance.convert.return_value = mock_result
        yield mock_instance

def test_parse_to_markdown_returns_markdown_content_when_file_exists(mock_converter):
    """Test that parse_to_markdown successfully converts document to markdown."""
    parser = DocumentParser()

    # Create a fake path that 'exists'
    with patch("pathlib.Path.exists", return_value=True):
        result = parser.parse_to_markdown("dummy.pdf")

    assert result == "# Test Header\nContent"
    mock_converter.convert.assert_called_once()

def test_parse_to_markdown_raises_file_not_found_error_when_file_missing():
    """Test that parse_to_markdown raises FileNotFoundError for nonexistent files."""
    parser = DocumentParser()

    with pytest.raises(FileNotFoundError):
        parser.parse_to_markdown("nonexistent.pdf")
