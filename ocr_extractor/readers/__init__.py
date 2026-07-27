"""Reader registry and supported format list.

Each entry maps a lowercase file extension to the name of the reader that
handles it. The dispatcher uses this table to route ``read_document`` calls
to the appropriate reader module.
"""

from pathlib import Path

# Extensions → reader name. The reader module exposes a ``read_<name>``
# function (or a generic ``read_legacy_office`` for the legacy trio).
EXTENSION_READERS = {
    # OCR-based readers
    ".pdf": "pdf",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".bmp": "image",
    ".webp": "image",
    ".heic": "image",
    ".tif": "tiff",
    ".tiff": "tiff",
    # Text-extraction readers
    ".docx": "docx",
    ".pptx": "pptx",
    ".xlsx": "xlsx",
    # Legacy Office (OLE binary) — converted via LibreOffice
    ".doc": "legacy",
    ".xls": "legacy",
    ".ppt": "legacy",
}

# Convenience: human-readable list of supported extensions.
SUPPORTED_FORMATS = sorted(EXTENSION_READERS.keys())


def get_reader_name(path):
    """Return the reader name for ``path`` based on its extension.

    Parameters
    ----------
    path : str or pathlib.Path
        Path to the input file.

    Returns
    -------
    str or None
        The reader name (for example ``"pdf"``) or ``None`` if the
        extension is not registered.
    """
    ext = Path(path).suffix.lower()
    return EXTENSION_READERS.get(ext)


__all__ = ["EXTENSION_READERS", "SUPPORTED_FORMATS", "get_reader_name"]