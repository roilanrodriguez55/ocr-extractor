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

from ocr_extractor.result import wrap_page


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


#: Punctuation kept by :func:`clean_line` on top of letters and digits.
#: Everything else becomes a space. Widen it for technical documents, where
#: ``:`` (scales), ``/`` (dates) and ``,`` (decimals) carry meaning:
#: ``clean_line(line, punctuation=DEFAULT_PUNCTUATION + ":/,")``.
DEFAULT_PUNCTUATION = " '-.!?"


def clean_line(line, punctuation=DEFAULT_PUNCTUATION):
    """Clean a single text line: drop short lines and symbol-only lines,
    and replace disallowed characters with spaces.

    Letters and digits are kept for **every** alphabet, not just ASCII. The
    previous allowlist was spelled out A–Z, which silently turned every
    accented character into a space: with ``lang="spa"`` Tesseract would read
    *Cimentación* correctly and this function would hand back *Cimentaci n*.
    Since dropping accents was never the intent for a package that advertises
    non-English language codes, that is treated as a fix rather than a
    behaviour change.

    Parameters
    ----------
    line : str
        The text line to clean.
    punctuation : str, optional
        Characters to keep alongside letters and digits. Defaults to
        :data:`DEFAULT_PUNCTUATION`.

    Returns
    -------
    str | None
        The cleaned line, or ``None`` if it should be discarded.
    """
    line = line.strip()
    if len(line) < 2:
        return None

    allowed = set(punctuation)
    # ``str.isalnum`` is Unicode-aware, so this keeps á, ñ, ü, ç, Cyrillic,
    # CJK and everything else Tesseract can be asked to read.
    clean = "".join(c if (c.isalnum() or c in allowed) else " " for c in line)
    clean = re.sub(r"\s+", " ", clean).strip()

    if len(clean) < 2:
        return None

    symbol_pattern = r"^[\(\)\[\]\{\}\_\-\=\+\*\#\@\^\.\,\:\;\<\>\/\\\|\~]+$"
    if re.match(symbol_pattern, clean):
        return None

    return clean


def clean_text(text, punctuation=DEFAULT_PUNCTUATION):
    """Apply :func:`clean_line` to every line of ``text`` and return the
    result keeping only the valid lines.

    Parameters
    ----------
    text : str
        Raw text produced by OCR.
    punctuation : str, optional
        Passed through to :func:`clean_line`.

    Returns
    -------
    str
        Cleaned text, with lines joined by ``\\n``.
    """
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        result = clean_line(line, punctuation=punctuation)
        if result:
            cleaned.append(result)
    return "\n".join(cleaned)


def ocr_page(image_pil, *, lang="eng", label="1", clean=False,
             punctuation=DEFAULT_PUNCTUATION, preprocess=True):
    """OCR one image and return a :class:`~ocr_extractor.result.PageResult`.

    Uses ``pytesseract.image_to_data`` rather than ``image_to_string``: the
    same Tesseract pass costs the same and additionally yields a confidence
    and a bounding box per word. That is what lets a caller decide on its own
    whether the page came out well enough to trust, instead of having to guess
    from the text.

    Parameters
    ----------
    image_pil : PIL.Image.Image
        The page to read.
    lang : str, optional
        Tesseract language code (``"eng"``, ``"spa"``, ``"spa+eng"``).
    label : str, optional
        Page label carried into the result (``"1"``, ``"Sheet1"``, ...).
    clean : bool, optional
        Run :func:`clean_text` over the result. Defaults to ``False`` here,
        the opposite of :func:`ocr_extractor.read_document` — a caller asking
        for structured output usually wants what Tesseract actually said.
    punctuation : str, optional
        Passed to :func:`clean_text` when ``clean`` is true.
    preprocess : bool, optional
        Apply :func:`preprocess_image` first. Turn it off for images that are
        already binarised, or when the denoiser is eating thin strokes.

    Returns
    -------
    ocr_extractor.result.PageResult
    """
    from ocr_extractor.result import PageResult, Word

    image = preprocess_image(image_pil) if preprocess else np.array(image_pil)
    data = pytesseract.image_to_data(
        image, lang=lang, output_type=pytesseract.Output.DICT,
    )

    words = []
    # Tesseract emits a row per layout element -- block, paragraph, line -- and
    # marks those with conf == -1. Only rows carrying actual text are words.
    for i, raw in enumerate(data["text"]):
        text = raw.strip()
        confidence = float(data["conf"][i])
        if not text or confidence < 0:
            continue
        words.append(
            Word(
                text=text,
                confidence=confidence,
                left=int(data["left"][i]),
                top=int(data["top"][i]),
                width=int(data["width"][i]),
                height=int(data["height"][i]),
            )
        )

    text = _text_from_data(data)
    if clean:
        text = clean_text(text, punctuation=punctuation)

    # 0.0 rather than None for a page that yielded nothing: it WAS OCR'd, and
    # it is exactly the page somebody should look at.
    mean = sum(w.confidence for w in words) / len(words) if words else 0.0

    return PageResult(
        label=str(label), text=text, words=tuple(words), confidence=mean,
    )


def _text_from_data(data):
    """Rebuild the page text from an ``image_to_data`` dict, keeping lines.

    Grouping by (block, paragraph, line) restores the line breaks that
    ``image_to_string`` gives for free. They matter: a drawing's title block is
    a stack of short lines, and flattening it into one run destroys the only
    structure it had.
    """
    lines = {}
    order = []
    for i, raw in enumerate(data["text"]):
        text = raw.strip()
        if not text or float(data["conf"][i]) < 0:
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        if key not in lines:
            lines[key] = []
            order.append(key)
        lines[key].append(text)

    return "\n".join(" ".join(lines[key]) for key in order)


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

        all_text += wrap_page(i + 1, text)

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
    "DEFAULT_PUNCTUATION",
    "preprocess_image",
    "clean_line",
    "clean_text",
    "ocr_page",
    "read_pdf",
]