import logging
import os
from contextlib import contextmanager
from typing import List, Generator

import psycopg2
from psycopg2.extras import execute_values
from psycopg2.pool import ThreadedConnectionPool

logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self, db_url: str, min_conn: int = 1, max_conn: int = 10):
        self._pool = ThreadedConnectionPool(min_conn, max_conn, db_url)
        self.vector_dimension = int(os.getenv("VECTOR_DIMENSION", "384"))
        logger.info("Initialized vector store with dimension: %d", self.vector_dimension)
        self._init_schema()

    @contextmanager
    def get_cursor(self) -> Generator:
        """Yields a cursor from a pooled connection, handling commits/rollbacks."""
        conn = self._pool.getconn()
        try:
            with conn.cursor() as cur:
                yield cur
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error("Database transaction failed: %s", e, exc_info=True)
            raise
        finally:
            self._pool.putconn(conn)

    def _init_schema(self):
        """Ensures the pgvector extension and table exist."""
        ddl = f"""
        CREATE EXTENSION IF NOT EXISTS vector;

        CREATE TABLE IF NOT EXISTS document_embeddings (
            id SERIAL PRIMARY KEY,
            source_file TEXT NOT NULL,
            activity_id UUID,
            chunk_index INT NOT NULL,
            chunk_text TEXT NOT NULL,
            embedding vector({self.vector_dimension}),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_embedding ON document_embeddings
        USING hnsw (embedding vector_cosine_ops);
        """
        with self.get_cursor() as cur:
            cur.execute(ddl)
            
            # ensure activity_id exists if the table was created before this update
            try:
                cur.execute("ALTER TABLE document_embeddings ADD COLUMN IF NOT EXISTS activity_id UUID;")
            except Exception as e:
                logger.warning("Could not add activity_id column (it might already exist): %s", e)

    def save_vectors(self, filename: str, chunks: List[str], embeddings: List[List[float]], activity_id: str | None = None):
        if not chunks:
            return

        insert_query = """
                       INSERT INTO document_embeddings (source_file, activity_id, chunk_index, chunk_text, embedding)
                       VALUES %s \
                       """

        data = [
            (filename, activity_id, i, chunk, embed)
            for i, (chunk, embed) in enumerate(zip(chunks, embeddings))
        ]

        with self.get_cursor() as cur:
            execute_values(cur, insert_query, data)

        logger.info("Saved %d vectors for %s", len(data), filename)

    def close(self):
        """Cleanly close all connections in the pool."""
        self._pool.closeall()