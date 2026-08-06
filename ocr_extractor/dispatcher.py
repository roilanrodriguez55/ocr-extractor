"""Document dispatcher.

Detects the input format by extension and routes to the appropriate
reader. All readers expose a ``read_<format>`` function with the same
signature: ``(path, *, dpi, lang, verbose) -> str``.
"""

import re
from pathlib import Path

from ocr_extractor.core import DEFAULT_PUNCTUATION
from ocr_extractor.readers import EXTENSION_READERS, get_reader_name
from ocr_extractor.result import DocumentResult, PageResult

#: Matches the page markers the string readers emit. The label is not always a
#: number -- worksheets are named -- so it is captured as text.
_PAGE_BLOCK = re.compile(
    r"=== PAGE (?P<label>.+?) ===\n(?P<body>.*?)\n=== END PAGE (?P=label) ===",
    re.DOTALL,
)


def read_document(path, *, dpi=300, lang="eng", verbose=True):
    """Read any supported document and return its extracted text.

    Format detection is purely extension-based. The dispatch table lives
    in ``ocr_extractor.readers.EXTENSION_READERS``.

    Parameters
    ----------
    path : str or pathlib.Path
        Path to the input file (PDF, image, DOCX, ...).
    dpi : int, optional
        Rendering resolution in DPI. Only used by OCR-based readers
        (PDF, images, legacy). Defaults to ``300``.
    lang : str, optional
        Tesseract language code. Only used by OCR-based readers.
        Defaults to ``"eng"``.
    verbose : bool, optional
        If ``True``, print progress messages. Defaults to ``True``.

    Returns
    -------
    str
        Extracted text, with ``=== PAGE N ===`` / ``=== END PAGE N ===``
        markers for multi-page formats.

    Raises
    ------
    ValueError
        If the file extension is not in the supported list.
    FileNotFoundError
        If the file does not exist.
    """
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"file does not exist or is not readable: {p}")

    reader = get_reader_name(p)
    if reader is None:
        supported = ", ".join(sorted(EXTENSION_READERS.keys()))
        raise ValueError(
            f"unsupported file extension '{p.suffix}'. Supported: {supported}"
        )

    # Import lazily so each reader's third-party dependency is only needed
    # when actually processing that format.
    if reader == "pdf":
        from ocr_extractor.readers.pdf import read_pdf_pages
        return read_pdf_pages(str(p), dpi=dpi, lang=lang, verbose=verbose)
    if reader == "image":
        from ocr_extractor.readers.images import read_image
        return read_image(str(p), dpi=dpi, lang=lang, verbose=verbose)
    if reader == "tiff":
        from ocr_extractor.readers.images import read_tiff
        return read_tiff(str(p), dpi=dpi, lang=lang, verbose=verbose)
    if reader == "docx":
        from ocr_extractor.readers.docx import read_docx
        return read_docx(str(p), dpi=dpi, lang=lang, verbose=verbose)
    if reader == "pptx":
        from ocr_extractor.readers.pptx import read_pptx
        return read_pptx(str(p), dpi=dpi, lang=lang, verbose=verbose)
    if reader == "xlsx":
        from ocr_extractor.readers.xlsx import read_xlsx
        return read_xlsx(str(p), dpi=dpi, lang=lang, verbose=verbose)
    if reader == "legacy":
        from ocr_extractor.readers.legacy import read_legacy_office
        return read_legacy_office(str(p), dpi=dpi, lang=lang, verbose=verbose)

    # Should never reach here unless EXTENSION_READERS is misconfigured.
    raise ValueError(f"no reader implementation for '{reader}'")


def _pages_from_marked_text(text):
    """Split ``=== PAGE N ===`` blocks into pages with no confidence.

    Used for the readers that extract text directly (DOCX, PPTX, XLSX and the
    legacy trio). Their text is exact, so ``confidence`` stays ``None`` — see
    :class:`~ocr_extractor.result.PageResult` for why that is not ``100``.
    """
    blocks = list(_PAGE_BLOCK.finditer(text))
    if not blocks:
        return (PageResult(label="1", text=text.strip()),)

    return tuple(
        PageResult(label=m.group("label").strip(), text=m.group("body").strip())
        for m in blocks
    )


def read_document_detailed(path, *, dpi=300, lang="eng", verbose=True,
                           clean=False, punctuation=DEFAULT_PUNCTUATION):
    """Read any supported document and return a structured result.

    Same dispatch as :func:`read_document`, but the return value carries a
    **confidence** per page — and, for OCR'd pages, a box per word. That is
    what a pipeline needs to decide for itself whether a page came out well
    enough to trust, rather than guessing from the text.

    Note ``clean`` defaults to ``False`` here, the opposite of
    :func:`read_document`: a caller asking for structured output normally
    wants what Tesseract actually said, punctuation and accents included.

    Parameters
    ----------
    path : str or pathlib.Path
        Path to the input file.
    dpi : int, optional
        Rendering resolution for OCR-based readers. Defaults to ``300``.
    lang : str, optional
        Tesseract language code (``"spa+eng"`` for mixed Spanish/English).
    verbose : bool, optional
        Print progress messages. Defaults to ``True``.
    clean : bool, optional
        Run the text through :func:`ocr_extractor.clean_text`. Defaults to
        ``False``.
    punctuation : str, optional
        Characters :func:`ocr_extractor.clean_line` keeps when ``clean`` is on.

    Returns
    -------
    ocr_extractor.result.DocumentResult

    Raises
    ------
    ValueError
        If the file extension is not supported.
    FileNotFoundError
        If the file does not exist.

    Examples
    --------
    >>> doc = read_document_detailed("plano.pdf", lang="spa+eng")
    >>> doc.confidence < 60          # doctest: +SKIP
    True
    >>> [w.text for w in doc.pages[0].words[:3]]   # doctest: +SKIP
    ['PLANO', 'DE', 'CIMENTACIÓN']
    """
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"file does not exist or is not readable: {p}")

    reader = get_reader_name(p)
    if reader is None:
        supported = ", ".join(sorted(EXTENSION_READERS.keys()))
        raise ValueError(
            f"unsupported file extension '{p.suffix}'. Supported: {supported}"
        )

    if reader == "pdf":
        from ocr_extractor.readers.pdf import read_pdf_pages_detailed
        return read_pdf_pages_detailed(
            str(p), dpi=dpi, lang=lang, verbose=verbose,
            clean=clean, punctuation=punctuation,
        )
    if reader == "image":
        from ocr_extractor.readers.images import read_image_detailed
        return read_image_detailed(
            str(p), dpi=dpi, lang=lang, verbose=verbose,
            clean=clean, punctuation=punctuation,
        )
    if reader == "tiff":
        from ocr_extractor.readers.images import read_tiff_detailed
        return read_tiff_detailed(
            str(p), dpi=dpi, lang=lang, verbose=verbose,
            clean=clean, punctuation=punctuation,
        )

    # Text-extraction readers. Their output is exact, so there is no confidence
    # to report and no per-word boxes to build -- reuse the string reader and
    # split it on the markers it already emits.
    text = read_document(p, dpi=dpi, lang=lang, verbose=verbose)
    return DocumentResult(path=str(p), pages=_pages_from_marked_text(text))


__all__ = ["read_document", "read_document_detailed"]