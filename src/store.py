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
        logger.info(f"Initialized vector store with dimension: {self.vector_dimension}")
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
            logger.error("Database transaction failed: %s", e)
            raise
        finally:
            self._pool.putconn(conn)

    def _init_schema(self):
        """Ensures the pgvector extension and table exist."""
        # We keep this here for self-contained worker resilience.
        ddl = f"""
        CREATE EXTENSION IF NOT EXISTS vector;

        CREATE TABLE IF NOT EXISTS document_embeddings (
            id SERIAL PRIMARY KEY,
            source_file TEXT NOT NULL,
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

    def save_vectors(self, filename: str, chunks: List[str], embeddings: List[List[float]]):
        if not chunks:
            return

        insert_query = """
            INSERT INTO document_embeddings (source_file, chunk_index, chunk_text, embedding)
            VALUES %s
        """

        data = [
            (filename, i, chunk, embed)
            for i, (chunk, embed) in enumerate(zip(chunks, embeddings))
        ]

        with self.get_cursor() as cur:
            execute_values(cur, insert_query, data)

        logger.info("Saved %d vectors for %s", len(data), filename)

    def close(self):
        """Cleanly close all connections in the pool."""
        self._pool.closeall()
