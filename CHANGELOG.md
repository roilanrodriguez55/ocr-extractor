# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.1] - 2026-07-27

### Changed
- Republished to PyPI with a clean upload history. The v0.3.0 release on PyPI
  was re-uploaded after a manual deletion and PyPI rejected the filename for
  re-use, so the package version was bumped to give the build artefacts a
  fresh name on the index.

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
