# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - 2026-08-05

### Fixed
- **`clean_line` no longer strips non-English letters.** The allowlist was
  spelled out `a-zA-Z0-9`, so every accented character became a space: with
  `lang="spa"` Tesseract read *Cimentación* correctly and the cleaner returned
  *Cimentaci n*. It now keeps letters and digits from **every** alphabet
  (`str.isalnum` is Unicode-aware), which also covers French, German, Cyrillic
  and CJK. Dropping accents was never the intent for a package that advertises
  non-English language codes, so this is a fix, not a behaviour change —
  ASCII-only input is unaffected.
  Note the widening also admits **non-ASCII digits** (Arabic-Indic ٤٥٢١,
  Devanagari, fullwidth forms), where the old allowlist accepted `0-9` only.
  Anyone who was relying on `clean_line` to strip them can restore the previous
  behaviour with an explicit `punctuation` set plus their own filter.

### Added
- **`read_document_detailed()`** — same dispatch as `read_document`, but
  returns a `DocumentResult` carrying a **confidence per page** and a
  **bounding box per word**. Both come out of the same single Tesseract pass,
  at no extra cost, by calling `image_to_data` instead of `image_to_string`.
  This is what lets a pipeline decide on its own whether a page came out well
  enough to trust — route the poor ones to a human, or to a heavier model —
  instead of guessing from the text.
- `Word`, `PageResult` and `DocumentResult` in `ocr_extractor.result`.
  `PageResult.confidence` is `None` for formats read without OCR (DOCX, PPTX,
  XLSX): their text is exact, so confidence is not a meaningful question about
  them, and `None` says something different from `100`. A page that *was*
  OCR'd but yielded nothing scores `0.0` — that is an answer, and it is
  exactly the page somebody should look at.
- `DocumentResult.confidence` averages across OCR'd pages **weighted by word
  count**, so a title page holding four words neither drags down nor props up
  the verdict on a page holding four hundred.
- `ocr_page()` in `ocr_extractor.core` — OCR one PIL image into a `PageResult`.
  Rebuilds line breaks from the layout data, which matters for drawings whose
  title block is a stack of short lines.
- **Configurable cleaning.** `clean_line` and `clean_text` now take a
  `punctuation` argument (default `DEFAULT_PUNCTUATION`, unchanged). Technical
  documents need what English prose does not: `:` is a scale, `/` is a date,
  `,` is a decimal separator. `clean_line("Escala 1:50", punctuation=DEFAULT_PUNCTUATION + ":")`.
- `preprocess=False` on `ocr_page`, for images that are already binarised or
  where the denoiser eats thin strokes.
- Python 3.13 classifier.

### Changed
- `DocumentResult.text` and `DocumentResult.confidence` are cached. A
  thousand-page scan rebuilt a multi-megabyte string on every access before;
  the pages are frozen, so the value cannot go stale.
- The page-marker parser is now derived from the `PAGE_START`/`PAGE_END`
  constants instead of repeating them in a regex. A drifted copy would have
  failed silently — still emitting, still parsing as nothing — leaving every
  Office file as one unsplit page with no error anywhere.

### Notes
- `read_document`, `read_pdf` and the CLI are untouched. The detailed API
  defaults to `clean=False` — a caller asking for structure normally wants
  what Tesseract actually said.
- `read_document_detailed` on a PDF still OCRs every page, even one that
  already carries a text layer. Extracting that layer instead would be exact
  and far cheaper; it is a separate change.

## [0.3.0] - 2026-07-27

### Added
- Support for 15 office and image formats through a modular reader architecture
  (PDF, PNG, JPG, JPEG, BMP, WebP, HEIC, TIF, TIFF, DOCX, PPTX, XLSX, DOC, XLS, PPT).
- Legacy Office formats (`.doc`, `.xls`, `.ppt`) via headless LibreOffice
  conversion with a 180s per-file timeout.
- `ocr_extractor.readers.SUPPORTED_FORMATS` exported as the canonical list of
  supported input extensions.
- A standalone CLI (`ocr-extractor`) with a `--version` flag.

### Changed
- Package is now distributed as an installable Python module (`pip install
  ocr-extractor`) via `pyproject.toml` with the `hatchling` build backend.
- `read_document` dispatches by extension to a dedicated reader, instead of the
  previous monolithic branch.

## [0.2.0] - 2026-07-27

### Added
- Initial public packaging and installation entry point.

## [0.1.0] - 2026-07-27

### Added
- Initial release: PDF and image OCR via Tesseract, text extraction for DOCX,
  PPTX, and XLSX.
