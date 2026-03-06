import argparse
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from embedder import ContentEmbedder
from parser import DocumentParser
from store import VectorStore


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("milo-manual-ingest")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Manually ingest a local document into document_embeddings."
    )
    parser.add_argument("--file", required=True, help="Absolute or relative path to a document.")
    parser.add_argument(
        "--source-file",
        default=None,
        help="Logical source_file value stored in DB. Defaults to the input filename.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1000,
        help="Maximum characters per chunk before split.",
    )
    parser.add_argument(
        "--limit-chunks",
        type=int,
        default=None,
        help="Optional cap for number of chunks (useful for quick tests).",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Delete existing rows for the same source_file before inserting.",
    )
    return parser.parse_args()


def resolve_db_url() -> str:
    db_url = os.getenv("DB_URL") or os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("Set DB_URL (or DATABASE_URL) before running manual_ingest.")
    return db_url


def main() -> None:
    load_dotenv()
    args = parse_args()

    file_path = Path(args.file).expanduser().resolve()
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    source_file = args.source_file or file_path.name
    db_url = resolve_db_url()

    logger.info("Starting manual ingest for %s", file_path)
    logger.info("Target source_file: %s", source_file)

    parser = DocumentParser()
    embedder = ContentEmbedder()
    store = VectorStore(db_url)

    try:
        markdown = parser.parse_to_markdown(file_path)
        chunks = embedder.chunk_text(markdown, chunk_size=args.chunk_size)
        if args.limit_chunks is not None:
            chunks = chunks[: args.limit_chunks]

        if not chunks:
            logger.warning("No chunks generated. Nothing to persist.")
            return

        if args.replace:
            with store.get_cursor() as cur:
                cur.execute("DELETE FROM document_embeddings WHERE source_file = %s", (source_file,))
            logger.info("Deleted previous rows for source_file=%s", source_file)

        vectors = embedder.embed_chunks(chunks)
        store.save_vectors(source_file, chunks, vectors)

        with store.get_cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM document_embeddings WHERE source_file = %s",
                (source_file,),
            )
            count = cur.fetchone()[0]

        logger.info("Manual ingest completed. Total rows for '%s': %s", source_file, count)
    finally:
        store.close()


if __name__ == "__main__":
    main()
