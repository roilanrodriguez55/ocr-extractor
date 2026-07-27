"""OCR Extractor — extract text from PDF files via OCR (Tesseract + OpenCV).

Programmatic usage:

    from ocr_extractor import read_pdf
    text = read_pdf("document.pdf", dpi=300, lang="eng")

CLI (installed alongside the package):

    ocr-extractor document.pdf -o output.txt --lang spa
"""

from ocr_extractor.core import (
    clean_line,
    clean_text,
    preprocess_image,
    read_pdf,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "clean_line",
    "clean_text",
    "preprocess_image",
    "read_pdf",
]
