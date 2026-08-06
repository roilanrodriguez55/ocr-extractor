# Supported formats

`ocr-extractor` handles 15 input extensions across two pipelines: **OCR-based** (text comes from Tesseract) and **text-extraction** (text is read directly from the structured file).

## Format matrix

| Extension | Reader module | Pipeline | Marker format | Extra dependency |
|---|---|---|---|---|
| `.pdf` | `readers/pdf.py` | OCR (Tesseract via `pdf2image`) | `=== PAGE N ===` / `=== END PAGE N ===` | poppler (transitive via `pdf2image`) |
| `.png` | `readers/images.py` | OCR | none (single page) | Tesseract |
| `.jpg`, `.jpeg` | `readers/images.py` | OCR | none | Tesseract |
| `.bmp` | `readers/images.py` | OCR | none | Tesseract |
| `.webp` | `readers/images.py` | OCR | none | Tesseract |
| `.heic`, `.heif` | `readers/images.py` | OCR | none | `pillow-heif` (install via `ocr-extractor[heic]`) |
| `.tif`, `.tiff` | `readers/images.py` | OCR | one `=== PAGE N ===` block per frame | Tesseract |
| `.docx` | `readers/docx.py` | Text extraction | none (paragraphs and rows) | `python-docx` |
| `.pptx` | `readers/pptx.py` | Text extraction | one `=== PAGE N ===` block per slide | `python-pptx` |
| `.xlsx` | `readers/xlsx.py` | Text extraction | one `=== PAGE <sheet name> ===` block per worksheet | `openpyxl` |
| `.doc` | `readers/legacy.py` | LibreOffice → DOCX → text | matches DOCX | `soffice` (LibreOffice) |
| `.xls` | `readers/legacy.py` | LibreOffice → XLSX → text | matches XLSX | `soffice` (LibreOffice) |
| `.ppt` | `readers/legacy.py` | LibreOffice → PPTX → text | matches PPTX | `soffice` (LibreOffice) |

The canonical list of supported extensions is exposed at runtime:

```python
from ocr_extractor import SUPPORTED_FORMATS
print(SUPPORTED_FORMATS)
# ('.bmp', '.doc', '.docx', '.heic', '.heif', '.jpeg', '.jpg', '.pdf',
#  '.png', '.ppt', '.pptx', '.tif', '.tiff', '.webp', '.xls', '.xlsx')
```

Detection is purely extension-based: the dispatcher looks at `Path(path).suffix.lower()` and looks it up in `ocr_extractor.readers.EXTENSION_READERS`. Anything else raises `ValueError` with the full list of supported extensions in the message.

## Marker format

The text-extraction pipeline emits a marker block per logical unit (PDF page, TIFF frame, PPTX slide, XLSX worksheet, or legacy-Office-converted equivalent):

```
=== PAGE <label> ===

<text>

=== END PAGE <label> ===
```

`<label>` is numeric for ordered units (PDF, TIFF, PPTX) and the unit's name for unordered ones (XLSX worksheets):

```
=== PAGE 1 ===
...
=== END PAGE 1 ===

=== PAGE Costes ===
...
=== END PAGE Costes ===
```

Single-page documents (PNG, JPG, DOCX, etc.) return the body bare, with no markers — matching the legacy behaviour of `read_document`.

`DocumentResult.text` reproduces this format exactly, so `read_document(path)` and `read_document_detailed(path).text` return the same string for the same input.

## OCR vs text extraction — what changes for the caller

| Concern | OCR-based (PDF, images, legacy) | Text-extraction (DOCX, PPTX, XLSX) |
|---|---|---|
| Speed | Slow (Tesseract per page) | Fast (no image work) |
| Output cleanliness | Noisy; `clean_line` filters aggressively | Already clean |
| Per-page confidence | Available (`PageResult.confidence` is a `float`) | Not available (`PageResult.confidence is None`) |
| Per-word boxes | Available | Not available |
| `read_document_detailed(..., clean=True)` | Useful — strips noise | Mostly a no-op — text is already clean |
| `lang` parameter | Drives Tesseract | Ignored |

`PageResult.confidence` is intentionally `None` for the text-extraction readers: their text is exact, so "how confident was the reader" is not a meaningful question about them. A caller routing low scores to a human should `skip()` these pages rather than rank them top.

See [API reference / PageResult](api.md#pageresult) for the full semantics.

## Dependencies that matter at runtime

The package declares its Python dependencies in `pyproject.toml`; system-level tools are documented in [Getting started](getting-started.md#install-tesseract).

| Tool | Needed for | What happens if missing |
|---|---|---|
| Tesseract | PDF, all image formats, legacy Office | `pytesseract.TesseractNotFoundError` from the OCR readers. |
| `soffice` (LibreOffice) | `.doc`, `.xls`, `.ppt` only | `RuntimeError` from the legacy reader, with installation instructions. |
| Poppler | PDF only | `pdf2image.exceptions.PDFInfoNotInstalledError` (or equivalent) when reading a PDF. |
| `pillow-heif` | `.heic`, `.heif` only | Pillow raises `UnidentifiedImageError`. Optional — install via `pip install "ocr-extractor[heic]"`. |

## Format-specific notes

### PDF

Each page is rendered to a Pillow image with `pdf2image.convert_from_path(path, dpi=dpi)` at 300 DPI by default. The image goes through `preprocess_image` (grayscale + `cv2.fastNlMeansDenoising`) and then Tesseract. The DPI parameter is honoured; raise it for small text, lower it for large drawings if you hit memory limits.

### TIFF

Iterated with `PIL.ImageSequence.Iterator`. Each frame is forced to RGB before preprocessing. Single-frame TIFFs are read identically to PNG/JPG.

### HEIC / HEIF

Pillow does not open HEIC out of the box. The image reader registers `pillow_heif.register_heif_opener()` lazily on first use — if the package is missing, the import silently does nothing and Pillow raises `UnidentifiedImageError` later.

### DOCX

Walked in document order. Paragraphs emit one line each (after whitespace cleanup); tables emit one line per row, cells joined with ` | ` so the tabular structure survives in plain text. Empty rows and empty paragraphs are dropped.

### PPTX

Each slide is one marker block. The reader walks every shape on the slide; shapes with a `text_frame` contribute one line per paragraph, shapes with a `table` contribute one line per row. Slides with no text-bearing shapes still emit an empty marker block.

### XLSX

Each worksheet is one marker block labelled with the sheet name. Rows are emitted as ` | col1 | col2 | col3 ` (with leading and trailing pipes stripped, so empty leading/trailing cells collapse cleanly). The workbook is opened with `read_only=True, data_only=True` — formulas are replaced by their last-computed values, and memory use stays low even on large workbooks.

### Legacy Office (`.doc`, `.xls`, `.ppt`)

The legacy reader shells out to `soffice --headless --convert-to <modern>` in a temporary directory, with a 180-second timeout. The converted file is then handed to the matching modern reader. The original stem is sanitised to `[A-Za-z0-9_-]+` to keep the resulting filename portable across shells.
