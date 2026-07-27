"""CLI entry point: ``ocr-extractor``.

Usage:

    ocr-extractor document.pdf -o output.txt --lang spa
    ocr-extractor scan.tiff -o output.txt
    ocr-extractor report.docx -o output.txt
    ocr-extractor --help
    ocr-extractor --version
"""

import argparse
import sys
from pathlib import Path

from ocr_extractor import __version__, read_document
from ocr_extractor.readers import SUPPORTED_FORMATS

_PROG = "ocr-extractor"
_DESCRIPTION = (
    "Extract text from office documents and images. "
    "PDFs and images go through OCR (Tesseract). "
    "DOCX/PPTX/XLSX have text extracted directly. "
    "Legacy .doc/.xls/.ppt are converted via LibreOffice."
)
_EPILOG = (
    "Examples:\n"
    "  ocr-extractor document.pdf\n"
    "  ocr-extractor document.pdf -o output.txt --dpi 300 --lang spa\n"
    "  ocr-extractor scan.tiff -o output.txt\n"
    "  ocr-extractor report.docx -o output.txt\n"
    "  ocr-extractor presentation.pptx -o output.txt\n"
    "  ocr-extractor spreadsheet.xlsx -o output.txt\n"
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
        "input",
        help=(
            "Path to the input file. Supported: "
            + ", ".join(SUPPORTED_FORMATS)
            + "."
        ),
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
        help=(
            "Rendering resolution in DPI for OCR-based formats "
            "(PDF, images, legacy). Ignored for text-extraction formats. "
            "Default: %(default)s."
        ),
    )
    parser.add_argument(
        "--lang",
        default="eng",
        help=(
            "Tesseract language code, e.g. 'eng', 'spa'. "
            "Only used by OCR-based formats. Default: %(default)s."
        ),
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress progress messages during processing.",
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

    input_path = Path(args.input)

    try:
        if not input_path.is_file():
            raise FileNotFoundError(
                f"file does not exist or is not readable: {input_path}"
            )

        text = read_document(
            str(input_path),
            dpi=args.dpi,
            lang=args.lang,
            verbose=not args.quiet,
        )

        output_path = Path(args.output)
        output_path.write_text(text, encoding="utf-8")
    except Exception as exc:  # noqa: BLE001 — top-level CLI boundary
        print(f"Error processing '{input_path}': {exc}", file=sys.stderr)
        return 1

    if not args.quiet:
        print(f"Done. Output written to {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())