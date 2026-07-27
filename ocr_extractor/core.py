"""Core OCR helpers: image preprocessing and text cleaning.

PDF reading lives in :mod:`ocr_extractor.readers.pdf`; the format-agnostic
entry point is :func:`ocr_extractor.read_document` (in
:mod:`ocr_extractor.dispatcher`). The ``read_pdf`` function here is a
backward-compatible alias kept for one release cycle.
"""

import re
import warnings

import cv2
import numpy as np
import pytesseract
from pdf2image import convert_from_path


def preprocess_image(image_pil):
    """Convert a PIL image to grayscale and apply denoising.

    Parameters
    ----------
    image_pil : PIL.Image.Image
        Input image (for example, a page rendered by ``pdf2image``).

    Returns
    -------
    numpy.ndarray
        Grayscale image ready for OCR.
    """
    img_cv = cv2.cvtColor(np.array(image_pil), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    return denoised


def clean_line(line):
    """Clean a single text line: drop short lines and symbol-only lines,
    and replace disallowed characters with spaces.

    Parameters
    ----------
    line : str
        The text line to clean.

    Returns
    -------
    str | None
        The cleaned line, or ``None`` if it should be discarded.
    """
    line = line.strip()
    if len(line) < 2:
        return None

    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 '-.!?")
    clean = "".join(c if c in allowed else " " for c in line)
    clean = re.sub(r"\s+", " ", clean).strip()

    if len(clean) < 2:
        return None

    symbol_pattern = r"^[\(\)\[\]\{\}\_\-\=\+\*\#\@\^\.\,\:\;\<\>\/\\\|\~]+$"
    if re.match(symbol_pattern, clean):
        return None

    return clean


def clean_text(text):
    """Apply :func:`clean_line` to every line of ``text`` and return the
    result keeping only the valid lines.

    Parameters
    ----------
    text : str
        Raw text produced by OCR.

    Returns
    -------
    str
        Cleaned text, with lines joined by ``\\n``.
    """
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        result = clean_line(line)
        if result:
            cleaned.append(result)
    return "\n".join(cleaned)


def _read_pdf_legacy(pdf_path, dpi=300, lang="eng", verbose=True):
    """Read a PDF, run OCR on each page, and return the cleaned text.

    Each page is wrapped between the markers
    ``=== PAGE N ===`` ... ``=== END PAGE N ===``.

    Parameters
    ----------
    pdf_path : str
        Path to the PDF file.
    dpi : int, optional
        Resolution (dots per inch) used to render each page.
        Defaults to ``300``.
    lang : str, optional
        Tesseract language code (e.g. ``"eng"``, ``"spa"``).
        Defaults to ``"eng"``.
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


def read_pdf(pdf_path, dpi=300, lang="eng", verbose=True):
    """Deprecated alias for :func:`ocr_extractor.read_document`.

    .. deprecated::
        Use :func:`ocr_extractor.read_document` instead. ``read_pdf`` will
        be removed in the next major release.
    """
    warnings.warn(
        "ocr_extractor.read_pdf is deprecated; use read_document instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return _read_pdf_legacy(pdf_path, dpi=dpi, lang=lang, verbose=verbose)


__all__ = [
    "preprocess_image",
    "clean_line",
    "clean_text",
    "read_pdf",
]