"""
PDF Processing Service

Handles PDF upload, text extraction, and chunking.
"""

import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import fitz  # PyMuPDF
import structlog

from apps.backend.app.core.config import get_settings

logger = structlog.get_logger(__name__)


def sanitize_text_for_db(text: str) -> str:
    """
    Sanitize text for database storage.

    Removes null bytes and other problematic characters that SurrealDB doesn't support.
    """
    if not text:
        return ""

    # Remove null bytes
    text = text.replace('\x00', '')

    # Remove other control characters except newline, tab, carriage return
    text = re.sub(r'[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    # Normalize Unicode combining characters
    text = unicodedata.normalize('NFKC', text)

    return text


class PDFService:
    """Service for processing PDF files"""

    def __init__(self):
        self.settings = get_settings()
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Ensure required directories exist"""
        self.settings.pdf_dir.mkdir(parents=True, exist_ok=True)
        self.settings.cache_dir.mkdir(parents=True, exist_ok=True)
        self.settings.upload_dir.mkdir(parents=True, exist_ok=True)

    def save_pdf(self, filename: str, file_content: bytes, user_id: str) -> tuple[str, dict]:
        """
        Save uploaded PDF file and extract metadata.

        Returns (paper_id, pdf_metadata)
        """
        # Generate paper ID
        paper_id = f"paper_{user_id}_{datetime.utcnow().timestamp()}"

        # Save PDF file
        pdf_path = self.settings.pdf_dir / f"{paper_id}.pdf"
        pdf_path.write_bytes(file_content)

        logger.info(f"PDF saved: {pdf_path}")

        # Extract PDF metadata
        try:
            doc = fitz.open(pdf_path)
            title = doc.metadata.get("title") or filename
            author = doc.metadata.get("author") or "Unknown"
            metadata = {
                "title": title,
                "author": author,
                "page_count": len(doc),
                "created_at": datetime.utcnow(),
            }
            doc.close()
        except Exception as e:
            logger.warning(f"Failed to extract PDF metadata: {e}")
            metadata = {
                "title": filename,
                "author": "Unknown",
                "page_count": 0,
                "created_at": datetime.utcnow(),
            }

        return paper_id, metadata

    def extract_text_and_chunk(
        self, pdf_path: Path, paper_id: str, paper_title: str, user_id: str
    ) -> List[dict]:
        """
        Extract text from PDF and create chunks.

        Returns list of chunk data dicts ready for storage.
        """
        chunks = []

        try:
            doc = fitz.open(pdf_path)
            page_count = len(doc)

            logger.info(f"Extracting text from PDF: {pdf_path}, {page_count} pages")

            for page_num in range(page_count):
                page = doc[page_num]
                text = page.get_text()

                # Sanitize text for database storage
                text = sanitize_text_for_db(text)

                if not text.strip():
                    continue

                # Simple chunking by character count
                chunk_size = self.settings.chunk_size
                overlap_chars = int(chunk_size * self.settings.chunk_overlap)

                start = 0
                chunk_index = 0

                while start < len(text):
                    end = min(start + chunk_size, len(text))
                    chunk_text = text[start:end]

                    if chunk_text.strip():
                        chunks.append({
                            "paper_id": paper_id,
                            "paper_title": paper_title,
                            "user_id": user_id,
                            "page_number": page_num + 1,
                            "content": chunk_text,
                            "chunk_index": chunk_index,
                            "start_char": start,
                            "end_char": end,
                        })

                    start = end - overlap_chars if end < len(text) else end
                    chunk_index += 1

            doc.close()
            logger.info(f"Created {len(chunks)} text chunks from {page_count} pages")

        except Exception as e:
            logger.error(f"Failed to extract text from PDF: {e}")
            raise

        return chunks

    def get_pdf_path(self, paper_id: str) -> Optional[Path]:
        """Get the file path for a paper ID"""
        pdf_path = self.settings.pdf_dir / f"{paper_id}.pdf"
        if pdf_path.exists():
            return pdf_path
        return None

    def delete_pdf(self, paper_id: str) -> bool:
        """Delete PDF file"""
        pdf_path = self.settings.pdf_dir / f"{paper_id}.pdf"
        try:
            if pdf_path.exists():
                pdf_path.unlink()
                logger.info(f"Deleted PDF: {pdf_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete PDF: {e}")
            return False


# Singleton instance
_pdf_service: Optional[PDFService] = None


def get_pdf_service() -> PDFService:
    """Get or create PDF service singleton"""
    global _pdf_service
    if _pdf_service is None:
        _pdf_service = PDFService()
    return _pdf_service
