"""Document dispatcher.

Detects the input format by extension and routes to the appropriate
reader. All readers expose a ``read_<format>`` function with the same
signature: ``(path, *, dpi, lang, verbose) -> str``.
"""

from pathlib import Path

from ocr_extractor.readers import EXTENSION_READERS, get_reader_name


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


__all__ = ["read_document"]