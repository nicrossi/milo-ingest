import logging
import os
from typing import List, Tuple
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

class ContentEmbedder:
    def __init__(self, model_name: str = None):
        if model_name is None:
            model_name = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        self.model = SentenceTransformer(model_name)
        logger.info(f"Initialized embedder with model: {model_name}")

    def chunk_text(self, text: str, chunk_size: int = 1000) -> List[str]:
        """Simple semantic splitter based on double newlines (paragraphs)."""
        chunks = []
        current_chunk = []
        current_length = 0

        # Split by Markdown paragraphs
        paragraphs = text.split("\n\n")

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if current_length + len(para) > chunk_size and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_length = 0

            current_chunk.append(para)
            current_length += len(para)

        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        return chunks

    def embed_chunks(self, chunks: List[str]) -> List[List[float]]:
        if not chunks:
            return []

        logger.info("Generating embeddings for %d chunks...", len(chunks))
        embeddings = self.model.encode(chunks)
        return embeddings.tolist()
