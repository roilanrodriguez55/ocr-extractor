"""CLI entry point: ``ocr-extractor``.

Usage:

    ocr-extractor document.pdf -o output.txt --lang spa
    ocr-extractor --help
    ocr-extractor --version
"""

import argparse
import sys
from pathlib import Path

from ocr_extractor import __version__, read_pdf

_PROG = "ocr-extractor"
_DESCRIPTION = (
    "Extract text from PDFs via OCR (Tesseract). "
    "Renders each page to an image, preprocesses it, and writes the cleaned text."
)
_EPILOG = (
    "Examples:\n"
    "  ocr-extractor document.pdf\n"
    "  ocr-extractor document.pdf -o output.txt --dpi 300 --lang spa\n"
    "  ocr-extractor document.pdf -q"
)


def _build_parser():
    parser = argparse.ArgumentParser(
        prog=_PROG,
        description=_DESCRIPTION,
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "pdf",
        help="Path to the input PDF file.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="texto_limpio.txt",
        help="Path to the output text file (default: %(default)s).",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="Rendering resolution in DPI (default: %(default)s).",
    )
    parser.add_argument(
        "--lang",
        default="eng",
        help="Tesseract language code, e.g. 'eng', 'spa' (default: %(default)s).",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress progress messages during OCR.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{_PROG} {__version__}",
    )
    return parser


def main(argv=None):
    """Executable entry point registered in ``pyproject.toml``."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    pdf_path = Path(args.pdf)
    if not pdf_path.is_file():
        parser.error(f"file does not exist or is not readable: {pdf_path}")

    try:
        text = read_pdf(
            str(pdf_path),
            dpi=args.dpi,
            lang=args.lang,
            verbose=not args.quiet,
        )
    except Exception as exc:  # noqa: BLE001 — top-level CLI boundary
        print(f"Error processing '{pdf_path}': {exc}", file=sys.stderr)
        return 1

    output_path = Path(args.output)
    output_path.write_text(text, encoding="utf-8")

    if not args.quiet:
        print(f"Done. Output written to {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
