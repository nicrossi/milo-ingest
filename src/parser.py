import logging
from pathlib import Path
from docling.document_converter import DocumentConverter

logger = logging.getLogger(__name__)

class DocumentParser:
    def __init__(self):
        # Initialize converter once to load models into memory
        self._converter = DocumentConverter()

    def parse_to_markdown(self, file_path: Path | str) -> str:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        logger.info("Starting Docling parse for: %s", path.name)

        try:
            result = self._converter.convert(path)
            markdown_content = result.document.export_to_markdown()

            logger.info("Parse successful. Generated %d characters.", len(markdown_content))
            return markdown_content

        except Exception as e:
            logger.error("Docling parsing failed for %s: %s", path.name, e, exc_info=True)
            raise
