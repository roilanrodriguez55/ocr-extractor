"""Legacy Office reader — convert ``.doc``/``.xls``/``.ppt`` via
LibreOffice headless, then delegate to the modern reader.

The legacy binary formats (OLE Compound Document) are notoriously hard
to parse in pure Python. The most reliable approach across platforms is
to shell out to ``soffice --headless --convert-to <modern>`` and then
process the resulting file with the corresponding modern reader.

If LibreOffice is not installed on the system, this reader raises a
clear :class:`RuntimeError` explaining how to install it.
"""

import re
import subprocess
import tempfile
from pathlib import Path


# Mapping from legacy extension to the modern format LibreOffice produces.
_LEGACY_TO_MODERN = {
    ".doc": "docx",
    ".xls": "xlsx",
    ".ppt": "pptx",
}

# Map from modern extension back to the reader function that handles it.
_MODERN_READERS = {
    "docx": ("ocr_extractor.readers.docx", "read_docx"),
    "xlsx": ("ocr_extractor.readers.xlsx", "read_xlsx"),
    "pptx": ("ocr_extractor.readers.pptx", "read_pptx"),
}

_INSTALL_HINT = (
    "LibreOffice (the `soffice` command) is required to read legacy "
    "Office files (.doc, .xls, .ppt). Install it with one of:\n"
    "  - Debian/Ubuntu: sudo apt-get install libreoffice\n"
    "  - Fedora:        sudo dnf install libreoffice\n"
    "  - macOS:         brew install --cask libreoffice\n"
    "After installation, retry the command."
)


def _safe_name(stem):
    """Sanitize a stem so the converted filename is portable."""
    # LibreOffice names the output ``<stem>.<ext>``; restrict the stem
    # to alphanumerics, dash, and underscore to avoid surprises on shells
    # that interpret special characters.
    return re.sub(r"[^A-Za-z0-9_-]", "_", stem) or "file"


def _convert_with_libreoffice(path, target_dir, target_format):
    """Run ``soffice --headless --convert-to <target_format>`` on ``path``.

    Returns the path of the converted file inside ``target_dir``.

    Raises
    ------
    RuntimeError
        If ``soffice`` is not installed (with installation instructions)
        or if the conversion subprocess exits with a non-zero status.
    """
    cmd = [
        "soffice",
        "--headless",
        "--convert-to",
        target_format,
        "--outdir",
        str(target_dir),
        str(path),
    ]
    try:
        result = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            timeout=180,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"Could not run `soffice` to convert '{path.name}': "
            f"{exc}.\n\n{_INSTALL_HINT}"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"`soffice` conversion of '{path.name}' timed out after 180s."
        ) from exc

    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(
            f"`soffice` failed to convert '{path.name}' (exit code "
            f"{result.returncode}). Stderr: {stderr or '(empty)'}"
        )

    converted_name = _safe_name(path.stem) + "." + target_format
    converted_path = Path(target_dir) / converted_name
    if not converted_path.is_file():
        raise RuntimeError(
            f"`soffice` reported success but '{converted_path}' was not "
            f"produced. Output dir contents: "
            f"{sorted(p.name for p in Path(target_dir).iterdir())}"
        )
    return converted_path


def read_legacy_office(path, *, dpi=300, lang="eng", verbose=True):
    """Convert a legacy Office file via LibreOffice and read it.

    Parameters
    ----------
    path : str or pathlib.Path
        Path to a ``.doc``, ``.xls``, or ``.ppt`` file.
    dpi : int, optional
        Unused; passed through to the modern reader. Defaults to
        ``300``.
    lang : str, optional
        Unused; passed through to the modern reader. Defaults to
        ``"eng"``.
    verbose : bool, optional
        If ``True``, print progress messages. Defaults to ``True``.

    Returns
    -------
    str
        Extracted text, with markers matching the modern reader used.

    Raises
    ------
    FileNotFoundError
        If ``path`` does not exist.
    ValueError
        If the extension is not a known legacy Office format.
    RuntimeError
        If LibreOffice (``soffice``) is not installed or the conversion
        fails.
    """
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"file does not exist or is not readable: {p}")

    ext = p.suffix.lower()
    if ext not in _LEGACY_TO_MODERN:
        raise ValueError(
            f"unsupported legacy extension '{ext}'. "
            f"Supported: {', '.join(sorted(_LEGACY_TO_MODERN.keys()))}"
        )

    target_format = _LEGACY_TO_MODERN[ext]
    module_path, func_name = _MODERN_READERS[target_format]

    if verbose:
        print(f"Converting '{p.name}' to .{target_format} via LibreOffice...")

    with tempfile.TemporaryDirectory() as tmp:
        converted = _convert_with_libreoffice(p, Path(tmp), target_format)

        if verbose:
            print(f"Reading converted file...")

        # Import lazily so the modern reader is only loaded once we
        # actually have a converted file to feed it.
        import importlib

        module = importlib.import_module(module_path)
        reader = getattr(module, func_name)
        return reader(converted, dpi=dpi, lang=lang, verbose=verbose)


__all__ = ["read_legacy_office"]