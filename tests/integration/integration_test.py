import logging
import os
import sys
from pathlib import Path
from typing import List

import requests
from dotenv import load_dotenv

from src.embedder import ContentEmbedder
from src.parser import DocumentParser
from src.store import VectorStore

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("integration_test")

# Build DB_URL from environment variables
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5433")
DB_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{DB_HOST}:{DB_PORT}/{POSTGRES_DB}"
PDF_URL = "https://github.com/mozilla/pdf.js/raw/master/test/pdfs/tracemonkey.pdf"
TEST_FILE = Path("tracemonkey.pdf")
SIMILARITY_THRESHOLD = 0.001

def ensure_test_file(path: Path, url: str) -> None:
    if path.exists():
        return

    logger.info("Downloading test PDF from %s", url)
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        path.write_bytes(response.content)
    except requests.RequestException as e:
        logger.error("Download failed: %s", e)
        raise

def verify_database_content(store: VectorStore, filename: str, reference_vector: List[float]) -> None:
    logger.info("Verifying database integrity...")

    with store.get_cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM document_embeddings WHERE source_file = %s",
            (filename,)
        )
        count = cur.fetchone()[0]
        if count == 0:
            raise AssertionError(f"No rows found for {filename}")

        logger.info("Found %d rows for %s", count, filename)

        # Verify Vector Similarity
        # Distance between the stored vector and itself should be near 0
        cur.execute(
            """
            SELECT (embedding <=> %s::vector) as distance
            FROM document_embeddings
            WHERE source_file = %s
            ORDER BY distance ASC
                LIMIT 1
            """,
            (str(reference_vector), filename)
        )

        result = cur.fetchone()
        if not result:
            raise AssertionError("Vector query returned no results")

        distance = result[0]
        if distance >= SIMILARITY_THRESHOLD:
            raise AssertionError(f"Vector mismatch. Distance {distance} exceeds threshold {SIMILARITY_THRESHOLD}")

        logger.info("Vector verification passed (Distance: %.6f)", distance)

def main():
    ensure_test_file(TEST_FILE, PDF_URL)

    parser = DocumentParser()
    embedder = ContentEmbedder()
    store = VectorStore(DB_URL)
    test_activity_id = "11111111-1111-1111-1111-111111111111"

    try:
        logger.info("Starting integration pipeline")

        # 1. Parse
        markdown = parser.parse_to_markdown(TEST_FILE)
        logger.info("Parsed %d characters", len(markdown))

        # 2. Chunk
        chunks = embedder.chunk_text(markdown)
        if not chunks:
            raise ValueError("No text chunks generated")
        logger.info("Generated %d chunks", len(chunks))

        # 3. Embed
        vectors = embedder.embed_chunks(chunks)
        logger.info("Generated %d vectors", len(vectors))

        # 4. Persist
        store.save_vectors(str(TEST_FILE), chunks, vectors, activity_id=test_activity_id)
        logger.info("Data persisted to database")

        # 5. Verify
        verify_database_content(store, str(TEST_FILE), vectors[0])
        logger.info("Integration test passed successfully")

    except Exception as e:
        logger.error("Test execution failed: %s", e, exc_info=True)
        sys.exit(1)
    finally:
        store.close()

if __name__ == "__main__":
    main()