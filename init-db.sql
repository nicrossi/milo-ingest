CREATE EXTENSION IF NOT EXISTS vector;

-- IMPORTANT: The vector dimension (384) MUST match the VECTOR_DIMENSION environment variable
-- used by both the ingest and RAG services. If using a different embedding model, update both:
--   - EMBEDDING_MODEL (e.g., sentence-transformers/all-MiniLM-L6-v2)
--   - VECTOR_DIMENSION (e.g., 384 for all-MiniLM-L6-v2)
CREATE TABLE IF NOT EXISTS document_embeddings (
    id SERIAL PRIMARY KEY,
    source_file TEXT NOT NULL,
    chunk_index INT NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding vector(384),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_embedding ON document_embeddings
    USING hnsw (embedding vector_cosine_ops);