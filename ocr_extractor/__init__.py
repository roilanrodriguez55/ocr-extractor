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

When the caller has to decide whether a page came out well enough to trust,
ask for the structured result instead. It carries a confidence per page and a
box per word, from the same single Tesseract pass:

    from ocr_extractor import read_document_detailed

    doc = read_document_detailed("plano.pdf", lang="spa+eng")
    if doc.confidence < 70:
        send_for_human_review(doc)             # or escalate to a better model

    for word in doc.pages[0].words:
        print(word.text, word.confidence, word.left, word.top)

``confidence`` is ``None`` for formats read without OCR (DOCX, PPTX, XLSX):
their text is exact, so there is nothing to be confident about.

CLI (installed alongside the package):

    ocr-extractor document.pdf -o output.txt --lang spa
    ocr-extractor scan.tiff -o output.txt
    ocr-extractor report.docx -o output.txt
"""

from ocr_extractor.core import (
    DEFAULT_PUNCTUATION,
    clean_line,
    clean_text,
    ocr_page,
    preprocess_image,
    read_pdf,
)
from ocr_extractor.dispatcher import read_document, read_document_detailed
from ocr_extractor.readers import SUPPORTED_FORMATS
from ocr_extractor.result import DocumentResult, PageResult, Word

__version__ = "0.3.2"

__all__ = [
    "__version__",
    "read_document",
    "read_document_detailed",
    "read_pdf",
    "ocr_page",
    "preprocess_image",
    "clean_line",
    "clean_text",
    "DEFAULT_PUNCTUATION",
    "DocumentResult",
    "PageResult",
    "Word",
    "SUPPORTED_FORMATS",
]