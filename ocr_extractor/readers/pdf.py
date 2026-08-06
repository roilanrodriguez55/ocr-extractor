"""PDF reader — OCR each page with Tesseract.

Extracted from the previous ``ocr_extractor.core.read_pdf`` without any
behavior change. Each page is rendered to an image with ``pdf2image``,
preprocessed with ``preprocess_image``, and OCR'd with Tesseract. The
result is wrapped in ``=== PAGE N ===`` / ``=== END PAGE N ===`` markers.
"""

from pdf2image import convert_from_path

from ocr_extractor.core import DEFAULT_PUNCTUATION, clean_text, ocr_page, preprocess_image
from ocr_extractor.result import DocumentResult, wrap_page
import pytesseract


def read_pdf_pages(pdf_path, dpi=300, lang="eng", verbose=True):
    """Read a PDF, run OCR on each page, and return the cleaned text.

    Parameters
    ----------
    pdf_path : str
        Path to the PDF file.
    dpi : int, optional
        Resolution (dots per inch) used to render each page. Defaults to
        ``300``.
    lang : str, optional
        Tesseract language code (e.g. ``"eng"``, ``"spa"``). Defaults to
        ``"eng"``.
    verbose : bool, optional
        If ``True``, print progress messages per page. Defaults to
        ``True``.

    Returns
    -------
    str
        Extracted text with per-page markers.
    """
    if verbose:
        print(f"Reading {pdf_path}...")
    pages = convert_from_path(pdf_path, dpi=dpi)
    all_text = ""

    for i, page in enumerate(pages):
        if verbose:
            print(f"Processing page {i + 1}...")

        img_processed = preprocess_image(page)
        text = pytesseract.image_to_string(img_processed, lang=lang)
        text = clean_text(text)

        all_text += wrap_page(i + 1, text)

    return all_text


def read_pdf_pages_detailed(pdf_path, dpi=300, lang="eng", verbose=True,
                            clean=False, punctuation=DEFAULT_PUNCTUATION):
    """Like :func:`read_pdf_pages`, but returns a
    :class:`~ocr_extractor.result.DocumentResult` with per-page confidence.

    Note this OCRs every page even when the PDF already carries a text layer.
    Extracting that layer instead would be exact and far cheaper — worth doing,
    but it is a separate change.
    """
    if verbose:
        print(f"Reading {pdf_path}...")

    rendered = convert_from_path(pdf_path, dpi=dpi)
    pages = []

    for i, page in enumerate(rendered, 1):
        if verbose:
            print(f"Processing page {i}...")
        pages.append(
            ocr_page(
                page, lang=lang, label=str(i), clean=clean,
                punctuation=punctuation,
            )
        )

    return DocumentResult(path=str(pdf_path), pages=tuple(pages))


__all__ = ["read_pdf_pages", "read_pdf_pages_detailed"]