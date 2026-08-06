# Architecture

This page explains how the package is wired together: how a call to `read_document` or `read_document_detailed` ends up running a specific reader, how the structured result is built, and where the confidence number comes from.

## Module map

```
ocr_extractor/
├── __init__.py          # public re-exports
├── cli.py               # `ocr-extractor` console script
├── core.py              # image preprocessing, text cleaning, ocr_page
├── dispatcher.py        # read_document, read_document_detailed
├── result.py            # Word, PageResult, DocumentResult
└── readers/
    ├── __init__.py      # EXTENSION_READERS, SUPPORTED_FORMATS, get_reader_name
    ├── pdf.py           # read_pdf_pages, read_pdf_pages_detailed
    ├── images.py        # read_image, read_tiff (+ detailed variants)
    ├── docx.py          # read_docx
    ├── pptx.py          # read_pptx
    ├── xlsx.py          # read_xlsx
    └── legacy.py        # read_legacy_office
```

The two layers are deliberately separate:

- **`core.py`** holds helpers that don't know anything about file format: image preprocessing, the text cleaner, and `ocr_page` (which takes a Pillow image and returns a `PageResult`).
- **`readers/`** holds one module per format family. Each module exposes two functions for OCR-based formats — `read_<format>` (string) and `read_<format>_detailed` (`DocumentResult`) — and one for text-extraction formats (`read_<format>` only).
- **`dispatcher.py`** is the only place that knows how to route by extension. The reader modules don't import each other.

## Dispatch

The dispatch table is in `ocr_extractor/readers/__init__.py`:

```python
EXTENSION_READERS = {
    ".pdf":   "pdf",
    ".png":   "image",
    ".jpg":   "image",
    ".jpeg":  "image",
    ".bmp":   "image",
    ".webp":  "image",
    ".heic":  "image",
    ".tif":   "tiff",
    ".tiff":  "tiff",
    ".docx":  "docx",
    ".pptx":  "pptx",
    ".xlsx":  "xlsx",
    ".doc":   "legacy",
    ".xls":   "legacy",
    ".ppt":   "legacy",
}
```

`get_reader_name(path)` does `Path(path).suffix.lower()` and looks the result up. The dispatcher matches the returned name against a chain of `if reader == "..."` blocks, each lazily importing the matching reader module.

The lazy import matters: each reader pulls in a heavyweight dependency (`pdf2image` and Poppler for PDF, `python-docx` for DOCX, `openpyxl` for XLSX, LibreOffice for legacy). Importing the dispatcher is cheap; importing `readers/pdf.py` is not.

### `read_document` flow

```
read_document(path, ...)
        │
        ▼
Path(path).is_file()  ─── no ──▶ FileNotFoundError
        │ yes
        ▼
get_reader_name(path)  ─── None ──▶ ValueError (lists supported extensions)
        │ found
        ▼
reader name → import + call reader
        │
        ▼
string, possibly with === PAGE N === markers
```

For OCR-based readers (`pdf`, `image`, `tiff`), the dispatcher calls `read_<format>` which renders pages, preprocesses them, runs Tesseract, and joins the per-page text.

For text-extraction readers (`docx`, `pptx`, `xlsx`), the reader walks the structured document and emits one line per paragraph / row, with marker blocks for multi-unit formats.

For legacy readers (`.doc`, `.xls`, `.ppt`), the reader shells out to `soffice`, converts to the modern format in a temp directory, and then calls the corresponding modern reader on the result.

### `read_document_detailed` flow

The structured path splits into two cases:

1. **OCR-based readers** (`pdf`, `image`, `tiff`). Dispatcher calls the matching `read_<format>_detailed` function, which loops over pages/frames and hands each to `ocr_page` (from `core.py`). Each call returns one `PageResult`; the reader collects them into a `DocumentResult`.

2. **Text-extraction readers** (`docx`, `pptx`, `xlsx`, `legacy`). These already return a plain string with marker blocks. The dispatcher calls `read_document` (the plain-string path) and then `_pages_from_marked_text(text)` splits the string back into `PageResult` objects with `confidence=None`.

```
read_document_detailed(path, ...)
        │
        ▼
get_reader_name(path)
        │
        ├─── "pdf" ─────────▶ read_pdf_pages_detailed
        │                         │
        │                         ├─ convert_from_path(path, dpi=dpi)
        │                         ├─ for each page: ocr_page(...) → PageResult
        │                         └─ DocumentResult(path, pages=tuple)
        │
        ├─── "image" ───────▶ read_image_detailed → ocr_page(...) → DocumentResult
        ├─── "tiff" ────────▶ read_tiff_detailed  → ocr_page(...) per frame
        │
        └─── "docx"/"pptx"/"xlsx"/"legacy"
                                  │
                                  ▼
                              read_document(path) → text
                                  │
                                  ▼
                              _pages_from_marked_text(text)
                                  │
                                  ▼
                              DocumentResult(path, pages=tuple)
```

## `ocr_page` — the structured-output core

`ocr_page(image_pil, ...)` is the function that turns one Pillow image into a `PageResult`. It does so with `pytesseract.image_to_data`:

```python
data = pytesseract.image_to_data(image, lang=lang, output_type=pytesseract.Output.DICT)
```

`image_to_data` returns one dict per column. Every element of `data["text"]` is a row in Tesseract's layout tree — block, paragraph, line, *and* word — marked with a confidence and a box. The **layout** rows (block, paragraph, line) carry `conf == -1`; the **word** rows carry `conf >= 0` and actual text.

Two iterations use the dict:

1. **Build `words`.** Walk `data["text"]`, skip rows with empty text or `conf < 0`, and emit one `Word(text, confidence, left, top, width, height)` per remaining row.

2. **Rebuild `text`.** Group the surviving rows by `(block_num, par_num, line_num)`, preserving insertion order, and join each group with spaces and groups with `\n`. The result has the same line structure `image_to_string` would have produced — which matters for drawings where the title block is a stack of short lines and flattening it would destroy the only structure it had.

The page's mean confidence is the mean of `Word.confidence` over the words collected. A page that was OCR'd but yielded zero words scores **`0.0`**, not `None` — zero is an answer, and it's exactly the page somebody should look at.

## Confidence aggregation

`DocumentResult.confidence` computes a weighted mean across OCR'd pages:

```python
ocr_pages = [p for p in self.pages if p.is_ocr]
total_words = sum(p.word_count for p in ocr_pages)
weighted = sum(p.confidence * p.word_count for p in ocr_pages)
return weighted / total_words
```

The weighting is by `word_count`, not by page count. A title page with four words does not outweigh — or get outweighed by — a body page with four hundred. The two special cases:

- **No OCR pages** → returns `None` (a DOCX-only document).
- **All OCR pages empty** → returns `0.0` (every page ran through Tesseract and found nothing — that's an answer, not a missing one).

## The marker format

PDF, TIFF, PPTX, XLSX, and the legacy Office readers all emit blocks of the form:

```
=== PAGE <label> ===

<body>

=== END PAGE <label> ===
```

`<label>` is numeric (`"1"`, `"2"`, ...) for ordered units and the unit's name (`"Costes"`, `"Sheet1"`, ...) for unordered ones.

`DocumentResult.text` reproduces this format, and `_pages_from_marked_text` parses it back. The two paths are round-trip-compatible for the same input — verified by the integration test `test_detailed_text_matches_read_document`.

Single-page inputs (PNG, JPG, DOCX, ...) intentionally emit **no markers** — both `read_document` and `DocumentResult.text` return the body bare. A pipeline that expects to split on markers should check `len(doc.pages) == 1` first or handle the no-marker case.

## Why two paths, not one

`read_document` and `read_document_detailed` share the same dispatcher and the same readers. The two paths are kept separate for three reasons:

1. **Backward compatibility.** Every release since 0.1.0 has returned a `str` from `read_document`. The detailed API is additive; existing callers keep their existing call signature.

2. **Defaults differ.** `read_document` cleans aggressively (the output is meant to be human-readable); `read_document_detailed` does not clean by default (the caller asking for word boxes wants what Tesseract actually said). Same default for both would be wrong for one or the other.

3. **The structured output is genuinely richer.** Confidence, word boxes, label, page-level metadata — none of which fits in a `str`. A parallel function is cleaner than overloading the existing one with optional return types.

The two paths cost the same per page: both call `image_to_data` once under the hood. The "extra" structure was always computed by Tesseract; `read_document` was discarding it.

## Where extensions live

Adding a new format is intentionally a small change:

1. Add `readers/<format>.py` with a `read_<format>` function.
2. Add the extension to `EXTENSION_READERS` in `readers/__init__.py`.
3. Add a `reader == "<format>"` branch to both `read_document` and `read_document_detailed` in `dispatcher.py`.
4. For an OCR-based format, also expose `read_<format>_detailed` and call it from the dispatcher's detailed branch.

Tests live under `tests/` and run with `pytest`. End-to-end tests that require Tesseract are marked with `pytest.mark.skipif(not shutil.which("tesseract"))` so the unit tests run anywhere.
