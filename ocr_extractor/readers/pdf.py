"""PDF reader — OCR each page with Tesseract.

Extracted from the previous ``ocr_extractor.core.read_pdf`` without any
behavior change. Each page is rendered to an image with ``pdf2image``,
preprocessed with ``preprocess_image``, and OCR'd with Tesseract. The
result is wrapped in ``=== PAGE N ===`` / ``=== END PAGE N ===`` markers.
"""

from pdf2image import convert_from_path

from ocr_extractor.core import clean_text, preprocess_image
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

        all_text += "=== PAGE " + str(i + 1) + " ===\n\n"
        all_text += text + "\n\n"
        all_text += "=== END PAGE " + str(i + 1) + " ===\n\n"

    return all_text


__all__ = ["read_pdf_pages"]