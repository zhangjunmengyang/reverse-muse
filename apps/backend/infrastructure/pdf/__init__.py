"""
PDF Infrastructure
"""

from apps.backend.infrastructure.pdf.pdf_service import PDFService, get_pdf_service

__all__ = [
    "PDFService",
    "get_pdf_service",
]
