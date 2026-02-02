import pytest
from unittest.mock import patch
import numpy as np
from src.embedder import ContentEmbedder

@pytest.fixture
def mock_model():
    with patch("src.embedder.SentenceTransformer") as MockClass:
        mock_instance = MockClass.return_value
        # Mock .encode() to return a numpy array (as SentenceTransformer does)
        mock_array = np.array([[0.1, 0.2, 0.3]])
        mock_instance.encode.return_value = mock_array
        yield mock_instance

def test_chunk_text_splits_paragraphs_when_exceeding_chunk_size():
    """Test that text is split into separate chunks when paragraphs exceed chunk size."""
    # Initialize with a dummy model name to avoid real download
    with patch("src.embedder.SentenceTransformer"):
        embedder = ContentEmbedder()

    text = "Para 1\n\nPara 2\n\nPara 3"
    # Force small chunk size to verify splitting
    chunks = embedder.chunk_text(text, chunk_size=10)

    assert len(chunks) == 3
    assert chunks[0] == "Para 1"

def test_embed_chunks_returns_vector_embeddings_for_text(mock_model):
    """Test that embed_chunks returns vector embeddings by calling the model."""
    embedder = ContentEmbedder()
    chunks = ["Hello world"]

    vectors = embedder.embed_chunks(chunks)

    assert vectors == [[0.1, 0.2, 0.3]]
    mock_model.encode.assert_called_with(chunks)
