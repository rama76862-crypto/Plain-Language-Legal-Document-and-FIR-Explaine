"""Local bounded PDF/DOCX extraction. This module never calls remote services."""
from .service import extract_document
from .ocr import ocr_capabilities

__all__ = ['extract_document', 'ocr_capabilities']
