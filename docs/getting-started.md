# Getting started

This page covers installing `ocr-extractor`, its system dependencies, and running your first extraction.

## Requirements

- **Python** 3.8 or newer (3.13 is supported, classifiers list 3.8 – 3.13).
- **Tesseract OCR** 4.x or 5.x. Required for any OCR-based reader (PDF, PNG, JPG, BMP, WebP, HEIC, TIFF, legacy Office).
- **LibreOffice** (`soffice` on `PATH`). Required only for legacy Office formats (`.doc`, `.xls`, `.ppt`). The modern Office formats and image formats work without it.
- **Poppler**. Required transitively by `pdf2image` to render PDF pages. On Debian/Ubuntu this is `poppler-utils`; on macOS install via Homebrew.

## Install the Python package

From PyPI:

```bash
pip install ocr-extractor
```

From a source checkout (editable install, useful while developing):

```bash
git clone https://github.com/roilanrodriguez55/ocr-extractor
cd ocr-extractor
pip install -e .
```

For HEIC / HEIF image support, add the optional extra:

```bash
pip install "ocr-extractor[heic]"
```

For local development (pulls in `pytest` and `build`):

```bash
pip install "ocr-extractor[dev]"
```

## Install Tesseract

The Python wrapper `pytesseract` only knows how to call Tesseract; the binary itself has to be on `PATH` (or pointed to via the `TESSDATA_PREFIX` / `pytesseract.tesseract_cmd` settings).

| Platform | Command |
|---|---|
| Debian / Ubuntu | `sudo apt-get install tesseract-ocr` |
| Fedora / RHEL | `sudo dnf install tesseract` |
| macOS (Homebrew) | `brew install tesseract` |
| Windows | Installer from [the Tesseract GitHub releases](https://github.com/UB-Mannheim/tesseract/wiki). |

To OCR non-English text, install the corresponding language packs. For Spanish + English:

```bash
sudo apt-get install tesseract-ocr-spa tesseract-ocr-eng
```

The full list of available packs is searchable as `tesseract-ocr-<lang>` in your package manager.

## Install LibreOffice (only for legacy Office)

If you need to read `.doc`, `.xls`, or `.ppt`, LibreOffice must be on `PATH` so `soffice --headless --convert-to <modern>` can run. Without it, the legacy reader raises a clear `RuntimeError` with installation instructions.

| Platform | Command |
|---|---|
| Debian / Ubuntu | `sudo apt-get install libreoffice` |
| Fedora | `sudo dnf install libreoffice` |
| macOS | `brew install --cask libreoffice` |

DOCX, PPTX, and XLSX do **not** require LibreOffice.

## Quick start — read a document as text

```python
from ocr_extractor import read_document

text = read_document("report.pdf", lang="eng")
print(text)
```

For a Spanish document with English fall-back for code-switching:

```python
text = read_document("plano.pdf", lang="spa+eng")
```

For a multi-frame TIFF, each frame becomes one marker block:

```
=== PAGE 1 ===
... text of frame 1 ...
=== END PAGE 1 ===

=== PAGE 2 ===
... text of frame 2 ...
=== END PAGE 2 ===
```

A single-page image (PNG, JPG, etc.) returns bare text with no markers.

## Quick start — get confidence and word boxes

When the calling pipeline needs to *decide* whether a page came out well enough to trust, ask for the structured result:

```python
from ocr_extractor import read_document_detailed

doc = read_document_detailed("plano.pdf", lang="spa+eng")

print(f"Overall confidence: {doc.confidence:.1f}")
for page in doc.pages:
    print(f"--- Page {page.label} (confidence={page.confidence}) ---")
    print(page.text)
    for word in page.words:
        if word.confidence < 60:
            print(f"  LOW: {word.text!r} at ({word.left},{word.top})")
```

If `doc.confidence` falls below the threshold you care about, route the document to a human reviewer or a heavier OCR model.

See [API reference / DocumentResult](api.md#documentresult) for the full shape, including the `None` vs `0.0` semantics for confidence.

## CLI

The package installs a console script:

```bash
ocr-extractor document.pdf -o output.txt --lang spa
ocr-extractor scan.tiff -o output.txt
ocr-extractor report.docx -o output.txt
ocr-extractor --help
ocr-extractor --version
```

The default output filename is `texto_limpio.txt` (this is intentional Spanish-default behaviour inherited from earlier releases).

## Verifying the install

A 30-second sanity check that everything is wired up:

```python
from ocr_extractor import __version__, read_document, SUPPORTED_FORMATS

print(__version__)         # e.g. "0.3.2"
print(SUPPORTED_FORMATS)   # tuple of supported extensions
```

If Tesseract is missing, the first call to a PDF or image reader will raise a clear `TesseractNotFoundError` from `pytesseract` — point it at the binary with `pytesseract.tesseract_cmd = "/path/to/tesseract"` or fix the `PATH`.

## Next steps

- [Supported formats](supported-formats.md) — which extensions map to which reader.
- [API reference](api.md) — every public symbol, with parameters and examples.
- [Architecture](architecture.md) — how the dispatcher and readers fit together.
