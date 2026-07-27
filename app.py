"""Thin wrapper that delegates to the ``ocr_extractor`` package.

Kept for backward compatibility: ``python app.py <path.pdf>`` still works.
For new code, prefer the installed ``ocr-extractor`` command or the
``from ocr_extractor import read_pdf`` API.
"""

from ocr_extractor.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
