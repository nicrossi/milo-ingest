import pytest
from unittest.mock import MagicMock, patch
from src.store import VectorStore

@pytest.fixture
def mock_pool():
    with patch("src.store.ThreadedConnectionPool") as MockPool:
        pool_instance = MockPool.return_value
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # Setup context manager for cursor: with conn.cursor() as cur:
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        pool_instance.getconn.return_value = mock_conn

        yield pool_instance

def test_init_executes_create_table_statement_for_document_embeddings(mock_pool):
    """Verify that VectorStore initialization creates the document_embeddings table."""
    VectorStore("postgres://fake:url")

    mock_conn = mock_pool.getconn.return_value
    mock_cursor = mock_conn.cursor.return_value.__enter__.return_value

    # Check if CREATE TABLE was executed
    assert mock_cursor.execute.called
    assert "CREATE TABLE IF NOT EXISTS document_embeddings" in mock_cursor.execute.call_args[0][0]

def test_save_vectors_inserts_chunks_and_embeddings_into_database(mock_pool):
    """Test that save_vectors successfully inserts text chunks and their vector embeddings."""
    store = VectorStore("postgres://fake:url")

    chunks = ["text1", "text2"]
    vectors = [[0.1], [0.2]]
    activity_id = "123e4567-e89b-12d3-a456-426614174000"

    # We need to patch execute_values because it's imported directly
    with patch("src.store.execute_values") as mock_exec_values:
        store.save_vectors("test.pdf", chunks, vectors, activity_id=activity_id)

        assert mock_exec_values.called
        args = mock_exec_values.call_args
        assert args[0][1].strip().startswith("INSERT INTO")
        assert len(args[0][2]) == 2  # 2 rows of data
        assert args[0][2][0][1] == activity_id  # verify activity_id is in tuple

def test_save_vectors_skips_database_insert_when_chunks_are_empty(mock_pool):
    """Test that save_vectors returns early without database call when given empty chunks."""
    store = VectorStore("postgres://fake:url")

    with patch("src.store.execute_values") as mock_exec_values:
        store.save_vectors("test.pdf", [], [])
        assert not mock_exec_values.called

def test_delete_vectors_executes_delete_with_source_file_filter(mock_pool):
    """Verify delete_vectors issues DELETE filtered by source_file and returns rowcount."""
    store = VectorStore("postgres://fake:url")

    mock_conn = mock_pool.getconn.return_value
    mock_cursor = mock_conn.cursor.return_value.__enter__.return_value
    mock_cursor.rowcount = 5
    mock_cursor.execute.reset_mock()

    deleted = store.delete_vectors("test.pdf")

    assert deleted == 5
    mock_cursor.execute.assert_called_once()
    sql, params = mock_cursor.execute.call_args[0]
    assert "DELETE FROM document_embeddings" in sql
    assert "source_file = %s" in sql
    assert params == ("test.pdf",)
