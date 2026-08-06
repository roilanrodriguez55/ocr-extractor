# OCR Extractor

Extract text from office documents and images. PDF and image files are
processed via OCR (Tesseract + OpenCV). Modern Office files
(`.docx`/`.pptx`/`.xlsx`) are read directly. Legacy Office files
(`.doc`/`.xls`/`.ppt`) are converted via LibreOffice headless.

**`ocr-extractor` is distributed as an installable Python package.** You
can use it as a dependency in other projects (`pip install ocr-extractor`),
run it from the command line (`ocr-extractor file.pdf`), or import it as a
library (`from ocr_extractor import read_document`).

## 📋 Table of contents

- [Features](#-features)
- [Requirements](#-requirements)
- [Installation](#-installation)
  - [As a dependency in another project](#as-a-dependency-in-another-project)
  - [Editable install from the repository](#editable-install-from-the-repository)
  - [Dependencies only (without cloning)](#dependencies-only-without-cloning)
- [Usage](#usage)
  - [From the CLI](#from-the-cli)
  - [As a library (API)](#as-a-library-api)
  - [Backward-compatible `app.py` wrapper](#backward-compatible-apppy-wrapper)
- [Project structure](#-project-structure)
- [Code description](#-code-description)
- [Output](#-output)
- [Customization](#-customization)
- [Troubleshooting](#-troubleshooting)
- [Publishing the package](#-publishing-the-package)
- [Documentation](#-documentation)
- [License](#-license)

## 📚 Documentation

Detailed documentation lives under [`docs/`](docs/):

| Document | Purpose |
|---|---|
| [Getting started](docs/getting-started.md) | Install the package, install Tesseract and LibreOffice, run the first extraction. |
| [Supported formats](docs/supported-formats.md) | Which extensions are supported, which reader handles each, and which dependencies they pull in. |
| [API reference](docs/api.md) | Every public symbol: parameters, return types, and examples. |
| [Architecture](docs/architecture.md) | How the dispatcher routes by extension, how `ocr_page` produces structured output, how confidence is computed. |
| [Release process](docs/release-process.md) | How to cut a release: version bump, tag, PyPI publish, GitHub Release, verification, troubleshooting. |

## ✨ Features

- **Multi-format support**: PDF, images (PNG/JPG/TIFF/BMP/WEBP/HEIC),
  modern Office (DOCX/PPTX/XLSX), and legacy Office (DOC/XLS/PPT via
  LibreOffice) — all through a single `read_document` entry point.
- **PDF → Image conversion**: each page of the PDF is rendered to a
  high-resolution image (300 DPI by default) using `pdf2image`.
- **Image preprocessing**: grayscale conversion and noise removal with
  `OpenCV` (`fastNlMeansDenoising`) to improve OCR accuracy.
- **Multi-page TIFF support**: each frame of a multi-page TIFF becomes
  its own `=== PAGE N ===` block, useful for scanner output.
- **Tesseract OCR**: text extraction via `pytesseract` with a configurable
  language (`eng` by default).
- **Text cleaning**: filtering of short lines, disallowed characters, and
  symbol-only lines (applied only to OCR-based formats).
- **Page markers**: PDF, TIFF, PPTX, and XLSX output is wrapped between
  `=== PAGE N ===` / `=== END PAGE N ===` markers so each page/slide/sheet
  is identifiable.
- **Public API + CLI**: installable as a dependency, invokable as the
  `ocr-extractor` command, or importable as a Python library.

## 🛠 Requirements

- **Python 3.8+**
- **Tesseract OCR** installed on the system (not installed via `pip`):
  ```bash
  # Debian / Ubuntu
  sudo apt-get install tesseract-ocr

  # Fedora
  sudo dnf install tesseract

  # macOS (Homebrew)
  brew install tesseract
  ```
- **Poppler** (required by `pdf2image`):
  ```bash
  # Debian / Ubuntu
  sudo apt-get install poppler-utils

  # Fedora
  sudo dnf install poppler-utils

  # macOS
  brew install poppler
  ```
- **LibreOffice** — required only for legacy Office files (`.doc`,
  `.xls`, `.ppt`):
  ```bash
  # Debian / Ubuntu
  sudo apt-get install libreoffice

  # Fedora
  sudo dnf install libreoffice

  # macOS
  brew install --cask libreoffice
  ```
- **Tesseract language packs** (optional). The default is `eng`; install
  others as needed, for example:
  ```bash
  sudo apt-get install tesseract-ocr-spa   # Spanish
  sudo apt-get install tesseract-ocr-deu   # German
  ```
- **pillow-heif** (optional) — required for HEIC/HEIF images from iPhones:
  ```bash
  pip install ocr-extractor[heic]
  ```

## 📦 Installation

### As a dependency in another project

Once published to PyPI (or your private index):

```bash
pip install ocr-extractor
```

This installs the library and puts the `ocr-extractor` command on your
`PATH`. Python dependencies are resolved automatically (Tesseract,
Poppler, and LibreOffice remain system-level requirements).

To pin or constrain the version in `pyproject.toml` / `requirements.txt`:

```text
# requirements.txt
ocr-extractor>=0.4.0
```

For HEIC/HEIF support (iPhone photos), install the `[heic]` extra:

```bash
pip install ocr-extractor[heic]
```

### Editable install from the repository

Recommended during development. Clone the repo and, inside the virtual
environment where you want to use it:

```bash
git clone https://github.com/roilanrodriguez55/ocr-extractor.git
cd ocr-extractor
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

`pip install -e .` registers the package in editable mode: any change in
`ocr_extractor/` is picked up without reinstalling. The `dev` extra adds
`pytest` and `build` for tests and for producing sdist/wheel artifacts.

### Dependencies only (without cloning)

If you don't want to install this project and only need the API from your
own code, install the Python dependencies directly:

```bash
pip install pytesseract pdf2image opencv-python-headless numpy Pillow \
            python-docx python-pptx openpyxl
```

> 💡 If your platform supports it, you can also use `opencv-python` instead
> of `opencv-python-headless` (the headless variant avoids GUI
> dependencies).

## Usage

There are three ways to invoke the OCR, in order of recommendation:

### From the CLI

After `pip install ocr-extractor` (or `pip install -e .`):

```bash
# Basic usage: writes texto_limpio.txt next to the input
ocr-extractor file.pdf
ocr-extractor scan.tiff                  # multi-page TIFF
ocr-extractor report.docx                # no OCR — direct text extraction
ocr-extractor presentation.pptx          # one marker block per slide
ocr-extractor spreadsheet.xlsx           # one marker block per sheet

# Customize output, resolution, and language (OCR formats only)
ocr-extractor file.pdf -o output.txt --dpi 300 --lang spa

# Quiet mode (no progress messages)
ocr-extractor file.pdf -q

# Help and version
ocr-extractor --help
ocr-extractor --version
```

Available arguments:

| Argument | Description | Default |
|---|---|---|
| `input` | Path to the input file (positional, required) | — |
| `-o`, `--output` | Path to the output text file | `texto_limpio.txt` |
| `--dpi` | Rendering resolution in DPI (OCR formats only) | `300` |
| `--lang` | Tesseract language code (`eng`, `spa`, …) | `eng` |
| `-q`, `--quiet` | Suppress progress messages | off |
| `--version` | Print version and exit | — |

### As a library (API)

```python
from ocr_extractor import read_document

# Format is detected by extension. Same call works for any supported format.
text = read_document("file.pdf", dpi=300, lang="eng")
text = read_document("scan.tiff")
text = read_document("report.docx")
text = read_document("presentation.pptx")
text = read_document("spreadsheet.xlsx")
text = read_document("legacy.doc")   # requires LibreOffice

# You can also use the intermediate steps directly
from ocr_extractor import preprocess_image, clean_text
from pdf2image import convert_from_path

pages = convert_from_path("file.pdf", dpi=300)
gray = preprocess_image(pages[0])  # numpy.ndarray ready for OCR
```

Functions exposed from `ocr_extractor`:

- `read_document(path, *, dpi=300, lang="eng", verbose=True) -> str`
- `read_document_detailed(path, *, dpi=300, lang="eng", verbose=True, clean=False, punctuation=DEFAULT_PUNCTUATION) -> DocumentResult`
- `ocr_page(image_pil, *, lang="eng", label="1", clean=False, preprocess=True) -> PageResult`
- `preprocess_image(image_pil) -> numpy.ndarray`
- `clean_line(line, punctuation=DEFAULT_PUNCTUATION) -> str | None`
- `clean_text(text, punctuation=DEFAULT_PUNCTUATION) -> str`
- `read_pdf(pdf_path, dpi=300, lang="eng", verbose=True) -> str` *(deprecated, will be removed in the next major release)*
- `DocumentResult`, `PageResult`, `Word` — the structured result types
- `DEFAULT_PUNCTUATION` — characters `clean_line` keeps besides letters and digits
- `SUPPORTED_FORMATS` — tuple of all supported extensions
- `__version__` — string, e.g. `"0.4.0"`

### Confidence: deciding whether a page is good enough

`read_document` gives you text. When something downstream has to *decide*
whether that text can be trusted — send it to a human, retry with a better
model, index it as-is — use `read_document_detailed`. It runs the same single
Tesseract pass and additionally returns a confidence per page and a bounding
box per word.

```python
from ocr_extractor import read_document_detailed

doc = read_document_detailed("plano.pdf", lang="spa+eng")

doc.confidence          # 0-100, weighted by word count across OCR'd pages
doc.pages[0].text       # text, with line breaks preserved
doc.pages[0].word_count
doc.pages[0].words[0]   # Word(text=..., confidence=..., left=..., top=..., width=..., height=...)

if doc.confidence < 70:
    escalate(doc)       # handwriting, a bad scan, a blank sheet
```

**`confidence is None` means the text did not come from OCR** — a DOCX, PPTX
or XLSX is read exactly, so how confident the reader was is not a meaningful
question. That is deliberately different from `100`. A page that *was* OCR'd
and yielded nothing scores `0.0`, because that is an answer, and it is exactly
the page somebody should look at.

The word boxes make it possible to work on a region instead of the whole page
— an engineering drawing's title block, a stamp, a table cell — which is
usually far more accurate than OCR'ing a whole A0 sheet at once.

### Cleaning is optional, and configurable

`read_document` cleans its output; `read_document_detailed` does not, because
a caller asking for structure normally wants what Tesseract actually said.

Cleaning keeps letters and digits from **every** alphabet, plus
`DEFAULT_PUNCTUATION` (`` '-.!? ``). Technical documents often need more:

```python
from ocr_extractor import clean_line, DEFAULT_PUNCTUATION

clean_line("Escala 1:50")                                    # 'Escala 1 50'
clean_line("Escala 1:50", punctuation=DEFAULT_PUNCTUATION + ":/,")  # 'Escala 1:50'
```

### Backward-compatible `app.py` wrapper

`app.py` is kept for backward compatibility: instead of duplicating logic,
it now delegates to the package. It still works as before:

```bash
python app.py file.pdf -o output.txt
```

Internally it calls `ocr_extractor.cli.main`, so it accepts the same
arguments as the CLI (run `ocr-extractor --help` to see them all).

## 📁 Project structure

```
ocr-extractor/
├── pyproject.toml              # Metadata, deps, entry point (built via hatchling)
├── MANIFEST.in                 # Includes README.md in the sdist
├── .gitignore                  # Standard Python ignores
├── README.md                   # This file
├── SUPPORTED_FORMATS.md        # Format inventory with priorities
├── app.py                      # Thin wrapper that delegates to ocr_extractor.cli
└── ocr_extractor/              # Python package (what gets distributed)
    ├── __init__.py             # Public API + __version__ + SUPPORTED_FORMATS
    ├── core.py                 # preprocess_image, clean_line, clean_text, deprecated read_pdf
    ├── dispatcher.py           # read_document (format detection + routing)
    ├── cli.py                  # argparse + main() (CLI entry point)
    └── readers/                # One module per format family
        ├── __init__.py         # EXTENSION_READERS map + get_reader_name
        ├── pdf.py              # OCR via pdf2image + Tesseract
        ├── images.py           # OCR for PNG/JPG/BMP/WEBP/HEIC (single page) and TIFF (multi-page)
        ├── docx.py             # python-docx: paragraphs + tables
        ├── pptx.py             # python-pptx: shapes + tables
        ├── xlsx.py             # openpyxl: worksheets as pages
        └── legacy.py           # .doc/.xls/.ppt → LibreOffice → modern reader
```

## 🔍 Code description

### `ocr_extractor.dispatcher.read_document(path, *, dpi=300, lang="eng", verbose=True)`
Format-agnostic entry point. Detects the file extension, picks the
right reader from `ocr_extractor.readers.EXTENSION_READERS`, and
returns its output. Raises `FileNotFoundError` for missing files and
`ValueError` for unsupported extensions.

### `ocr_extractor.core.preprocess_image(image_pil)`
Converts a PIL image to an OpenCV array, turns it grayscale, and applies
a denoising filter (`cv2.fastNlMeansDenoising`) with the parameters
`h=10`, `templateWindowSize=7`, and `searchWindowSize=21`. Returns the
grayscale image ready for OCR.

### `ocr_extractor.core.clean_line(line)`
Cleans a single text line:
- Discards lines shorter than 2 characters.
- Replaces any character not in `a-zA-Z0-9 '-.!?` with a space (note:
  the comma is **not** allowed — see "Customization" below).
- Collapses multiple spaces into one.
- Discards lines that contain only symbols (`()[]{}_-=+*#@^.,:;<>/\|~`).

### `ocr_extractor.core.clean_text(text)`
Applies `clean_line` to every line of the text and keeps only the lines
that pass the filter. Returns the cleaned text joined with newlines.

### `ocr_extractor.readers.pdf.read_pdf_pages(pdf_path, dpi=300, lang="eng", verbose=True)`
Iterates over every page of the PDF:
1. Renders each page to an image with `convert_from_path(pdf_path, dpi=dpi)`.
2. Preprocesses the image with `preprocess_image`.
3. Extracts the text with `pytesseract.image_to_string(..., lang=lang)`.
4. Cleans the text with `clean_text`.
5. Wraps the result between the markers
   `=== PAGE N ===` … `=== END PAGE N ===`.

### `ocr_extractor.readers.images.read_image(path, *, dpi, lang, verbose)`
Opens a single-page image (PNG, JPG, BMP, WEBP, HEIC) with Pillow,
runs it through `preprocess_image` and `pytesseract.image_to_string`,
and returns the cleaned text without page markers. HEIC requires
`pillow-heif` (install via `pip install ocr-extractor[heic]`).

### `ocr_extractor.readers.images.read_tiff(path, *, dpi, lang, verbose)`
Iterates over every frame of a multi-page TIFF. Each frame is OCR'd
and wrapped in `=== PAGE N ===` / `=== END PAGE N ===` markers, just
like the PDF reader.

### `ocr_extractor.readers.docx.read_docx(path, *, dpi, lang, verbose)`
Walks the document body in order, emitting one line per non-empty
paragraph and one line per table row (cells joined with ` | `). DOCX
files are not paginated, so no page markers are emitted.

### `ocr_extractor.readers.pptx.read_pptx(path, *, dpi, lang, verbose)`
Iterates over slides, extracting text from every shape that has a
`text_frame` and from tables. Each slide becomes one `=== PAGE N ===`
marker block.

### `ocr_extractor.readers.xlsx.read_xlsx(path, *, dpi, lang, verbose)`
Opens the workbook with `openpyxl` (`read_only=True`, `data_only=True`),
iterates every worksheet, and emits one `=== PAGE <sheet name> ===`
block per sheet. Rows become ` | col1 | col2 | col3`.

### `ocr_extractor.readers.legacy.read_legacy_office(path, *, dpi, lang, verbose)`
Shells out to `soffice --headless --convert-to <modern>` to convert
`.doc`/`.xls`/`.ppt` to `.docx`/`.xlsx`/`.pptx`, then delegates to the
corresponding modern reader. Raises `RuntimeError` with installation
instructions if LibreOffice is not installed on the system.

### `ocr_extractor.cli.main(argv=None)`
Entry point registered in `pyproject.toml` as
`ocr-extractor = "ocr_extractor.cli:main"`. Parses arguments with
`argparse`, validates that the input file exists, calls `read_document`,
and writes the result to the output file. All errors are caught at the
top level; the process exits with `0` on success, `1` on error.

### `app.py` (wrapper)
A few lines that import `ocr_extractor.cli.main` and call it when the
file is executed. It exists only to avoid breaking callers that still
run `python app.py file.pdf`.

## 📤 Output

`texto_limpio.txt` (or the file passed with `-o`) contains the extracted
text with this structure:

```
=== PAGE 1 ===

<cleaned text of page 1>

=== END PAGE 1 ===

=== PAGE 2 ===

<cleaned text of page 2>

=== END PAGE 2 ===
```

> ℹ️ OCR quality depends on the PDF's resolution, the typeface used, and
> the presence of images or watermarks. Low-resolution scanned documents
> will produce more recognition errors.

## ⚙️ Customization

- **Change input / output / language / DPI**: use the CLI arguments
  (`-o`, `--lang`, `--dpi`) or the `read_document` parameters from the
  API:
  ```python
  from ocr_extractor import read_document
  text = read_document("file.pdf", dpi=400, lang="spa")
  ```
- **Adjust the resolution**: higher `dpi` (400–600) gives better results
  on low-quality documents, at the cost of more memory and time.
- **Loosen the character filter**: extend the `allowed` set inside
  `ocr_extractor.core.clean_line` to allow additional characters (for
  example, `,áéíóúÁÉÍÓÚñÑ¿¡`). Since it lives inside `ocr_extractor/`,
  rerun `pip install -e .` after a change so the installed CLI picks it up.

## 🧪 Troubleshooting

| Problem | Likely cause | Solution |
|---|---|---|
| `ModuleNotFoundError: No module named 'ocr_extractor'` | The package isn't installed in the active Python | `pip install -e .` (editable) or `pip install ocr-extractor` |
| `ocr-extractor: command not found` | The `PATH` doesn't include the venv's scripts | Activate the virtualenv or use `python -m ocr_extractor.cli` |
| `TesseractNotFoundError` | The Tesseract binary is not on the `PATH` | Install Tesseract or set `pytesseract.pytesseract.tesseract_cmd` to the absolute path of the binary |
| `pdf2image` fails with a Poppler error | Poppler is not installed | Install `poppler-utils` (Linux) or `brew install poppler` (macOS) |
| Extracted text is empty | Image-based PDF with very low resolution | Raise `--dpi` or improve the source PDF |
| Accented characters / ñ are lost | `clean_line` only allows ASCII | Extend the `allowed` set with `áéíóúÁÉÍÓÚñÑ¿¡` |
| `unsupported file extension '.xyz'` | The format isn't supported | Check `ocr_extractor.SUPPORTED_FORMATS` for the supported list |
| LibreOffice error on `.doc`/`.xls`/`.ppt` | `soffice` is not on the `PATH` | Install LibreOffice (see Requirements) |
| `cannot identify image file '.heic'` | `pillow-heif` is not installed | `pip install ocr-extractor[heic]` |
| `DeprecationWarning: ocr_extractor.read_pdf is deprecated` | Code still imports the old `read_pdf` | Switch to `from ocr_extractor import read_document` |
| Encoding errors in the `.txt` | File opened without UTF-8 | The CLI uses `encoding="utf-8"`; if you write manually, use the same encoding |
| Slow on long PDFs | 300 DPI rendering + per-page OCR | Lower `--dpi` or process the PDF in batches |

## 🚀 Publishing the package

To build an sdist and a wheel locally (requires the `dev` extra):

```bash
pip install -e ".[dev]"
python -m build
ls dist/   # should show ocr_extractor-0.4.0.tar.gz and *.whl
```

To publish to PyPI (use the token you have in `~/.pypirc` or env vars):

```bash
python -m pip install --upgrade twine
python -m twine upload dist/*
```

> ⚠️ Before publishing, add a `LICENSE` file and fill in the `license`
> and `authors` fields in `pyproject.toml`; PyPI requires them.

## 📝 License

This project is distributed for educational purposes. **No `LICENSE` file
is included at the moment.** Feel free to adapt it to your needs; if you
plan to redistribute it, add an explicit license.
