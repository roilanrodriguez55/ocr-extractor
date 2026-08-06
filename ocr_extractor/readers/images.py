"""Image readers: single-page images and multi-page TIFFs.

Both use the same OCR pipeline as the PDF reader
(``preprocess_image`` → ``pytesseract.image_to_string`` → ``clean_text``).
The HEIC/HEIF opener is registered lazily via ``pillow-heif`` if it is
installed; missing wheels only break HEIC support.
"""

from pathlib import Path

import pytesseract
from PIL import Image, ImageSequence

from ocr_extractor.core import DEFAULT_PUNCTUATION, clean_text, ocr_page, preprocess_image
from ocr_extractor.result import DocumentResult, wrap_page


def _ensure_heif_support():
    """Register the HEIF/HEIC opener with Pillow if ``pillow-heif`` is
    installed. Silently does nothing when the package is not present.
    """
    try:
        from pillow_heif import register_heif_opener

        register_heif_opener()
    except ImportError:
        pass


def read_image(path, *, dpi=300, lang="eng", verbose=True):
    """OCR a single-page image (PNG, JPG, BMP, WEBP, HEIC).

    The image is opened with Pillow, preprocessed with
    :func:`ocr_extractor.preprocess_image`, and OCR'd with Tesseract.
    The cleaned text is returned **without** page markers (the image is a
    single page by definition).

    Parameters
    ----------
    path : str or pathlib.Path
        Path to the image file.
    dpi : int, optional
        Unused; kept for signature uniformity with the PDF reader.
        Defaults to ``300``.
    lang : str, optional
        Tesseract language code. Defaults to ``"eng"``.
    verbose : bool, optional
        If ``True``, print a single progress line. Defaults to ``True``.

    Returns
    -------
    str
        Extracted (cleaned) text.

    Raises
    ------
    FileNotFoundError
        If ``path`` does not exist.
    RuntimeError
        If the format cannot be opened by Pillow (for example, HEIC
        without ``pillow-heif`` installed).
    """
    p = Path(path)
    if p.suffix.lower() in (".heic", ".heif"):
        _ensure_heif_support()

    if verbose:
        print(f"Reading {p}...")

    img = Image.open(p)
    # Force materialization so downstream code can read pixels.
    img.load()
    img_processed = preprocess_image(img)
    text = pytesseract.image_to_string(img_processed, lang=lang)
    return clean_text(text)


def read_tiff(path, *, dpi=300, lang="eng", verbose=True):
    """OCR a multi-page TIFF.

    Each frame is wrapped in ``=== PAGE N ===`` / ``=== END PAGE N ===``
    markers, matching the format produced by :func:`read_pdf_pages`.

    Parameters
    ----------
    path : str or pathlib.Path
        Path to the TIFF file.
    dpi : int, optional
        Unused; kept for signature uniformity. Defaults to ``300``.
    lang : str, optional
        Tesseract language code. Defaults to ``"eng"``.
    verbose : bool, optional
        If ``True``, print a per-frame progress line. Defaults to
        ``True``.

    Returns
    -------
    str
        Extracted (cleaned) text with one marker block per frame.
    """
    if verbose:
        print(f"Reading {path}...")

    img = Image.open(path)
    all_text = ""

    for i, frame in enumerate(ImageSequence.Iterator(img), 1):
        if verbose:
            print(f"Processing page {i}...")

        # Multi-frame TIFFs sometimes carry palette/L modes; convert to
        # RGB so preprocess_image (which expects RGB-compatible input)
        # works uniformly.
        if frame.mode != "RGB":
            frame = frame.convert("RGB")

        img_processed = preprocess_image(frame)
        text = pytesseract.image_to_string(img_processed, lang=lang)
        text = clean_text(text)

        all_text += wrap_page(i, text)

    return all_text


def read_image_detailed(path, *, dpi=300, lang="eng", verbose=True,
                        clean=False, punctuation=DEFAULT_PUNCTUATION):
    """Like :func:`read_image`, but returns a
    :class:`~ocr_extractor.result.DocumentResult` carrying per-word
    confidences and boxes."""
    p = Path(path)
    if p.suffix.lower() in (".heic", ".heif"):
        _ensure_heif_support()

    if verbose:
        print(f"Reading {p}...")

    img = Image.open(p)
    img.load()
    page = ocr_page(
        img, lang=lang, label="1", clean=clean, punctuation=punctuation,
    )
    return DocumentResult(path=str(p), pages=(page,))


def read_tiff_detailed(path, *, dpi=300, lang="eng", verbose=True,
                       clean=False, punctuation=DEFAULT_PUNCTUATION):
    """Like :func:`read_tiff`, but returns a
    :class:`~ocr_extractor.result.DocumentResult`, one page per frame."""
    if verbose:
        print(f"Reading {path}...")

    img = Image.open(path)
    pages = []

    for i, frame in enumerate(ImageSequence.Iterator(img), 1):
        if verbose:
            print(f"Processing page {i}...")
        if frame.mode != "RGB":
            frame = frame.convert("RGB")
        pages.append(
            ocr_page(
                frame, lang=lang, label=str(i), clean=clean,
                punctuation=punctuation,
            )
        )

    return DocumentResult(path=str(path), pages=tuple(pages))


__all__ = ["read_image", "read_tiff", "read_image_detailed", "read_tiff_detailed"]