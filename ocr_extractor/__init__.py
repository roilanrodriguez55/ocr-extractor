"""OCR Extractor — extract text from office documents and images.

Supported formats (high priority):

- **PDF** (``pdf``, ``png``, ``jpg``, ``jpeg``, ``bmp``, ``webp``, ``heic``,
  ``tif``, ``tiff``) — OCR via Tesseract.
- **Office** (``docx``, ``pptx``, ``xlsx``) — direct text extraction
  (python-docx, python-pptx, openpyxl).
- **Legacy Office** (``doc``, ``xls``, ``ppt``) — converted to a modern
  format via LibreOffice headless, then processed as above.

Programmatic usage:

    from ocr_extractor import read_document
    text = read_document("document.pdf", dpi=300, lang="eng")
    text = read_document("scan.tiff")          # multi-page TIFF
    text = read_document("report.docx")        # no OCR

CLI (installed alongside the package):

    ocr-extractor document.pdf -o output.txt --lang spa
    ocr-extractor scan.tiff -o output.txt
    ocr-extractor report.docx -o output.txt
"""

from ocr_extractor.core import (
    clean_line,
    clean_text,
    preprocess_image,
    read_pdf,
)
from ocr_extractor.dispatcher import read_document
from ocr_extractor.readers import SUPPORTED_FORMATS

__version__ = "0.3.1"

__all__ = [
    "__version__",
    "read_document",
    "read_pdf",
    "preprocess_image",
    "clean_line",
    "clean_text",
    "SUPPORTED_FORMATS",
]