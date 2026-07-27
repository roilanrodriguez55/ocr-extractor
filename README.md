# OCR Extractor

Extract text from PDF files via OCR (Optical Character Recognition). It
converts each page of the PDF to an image, preprocesses it to improve
quality, and runs Tesseract to produce clean text.

**`ocr-extractor` is distributed as an installable Python package.** You
can use it as a dependency in other projects (`pip install ocr-extractor`),
run it from the command line (`ocr-extractor file.pdf`), or import it as a
library (`from ocr_extractor import read_pdf`).

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
- [License](#-license)

## ✨ Features

- **PDF → Image conversion**: each page of the PDF is rendered to a
  high-resolution image (300 DPI by default) using `pdf2image`.
- **Image preprocessing**: grayscale conversion and noise removal with
  `OpenCV` (`fastNlMeansDenoising`) to improve OCR accuracy.
- **Tesseract OCR**: text extraction via `pytesseract` with a configurable
  language (`eng` by default).
- **Text cleaning**: filtering of short lines, disallowed characters, and
  symbol-only lines.
- **Page markers**: the resulting text is wrapped between
  `=== PAGE N ===` / `=== END PAGE N ===` markers so each page is
  identifiable.
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
- **Tesseract language packs** (optional). The default is `eng`; install
  others as needed, for example:
  ```bash
  sudo apt-get install tesseract-ocr-spa   # Spanish
  sudo apt-get install tesseract-ocr-deu   # German
  ```

## 📦 Installation

### As a dependency in another project

Once published to PyPI (or your private index):

```bash
pip install ocr-extractor
```

This installs the library and puts the `ocr-extractor` command on your
`PATH`. Python dependencies are resolved automatically (Tesseract and
Poppler remain system-level requirements).

To pin or constrain the version in `pyproject.toml` / `requirements.txt`:

```text
# requirements.txt
ocr-extractor>=0.1.0
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
pip install pytesseract pdf2image opencv-python-headless numpy Pillow
```

> 💡 If your platform supports it, you can also use `opencv-python` instead
> of `opencv-python-headless` (the headless variant avoids GUI
> dependencies).

## Usage

There are three ways to invoke the OCR, in order of recommendation:

### From the CLI

After `pip install ocr-extractor` (or `pip install -e .`):

```bash
# Basic usage: writes texto_limpio.txt next to the PDF
ocr-extractor file.pdf

# Customize output, resolution, and language
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
| `pdf` | Path to the input PDF (positional, required) | — |
| `-o`, `--output` | Path to the output text file | `texto_limpio.txt` |
| `--dpi` | Rendering resolution in DPI | `300` |
| `--lang` | Tesseract language code (`eng`, `spa`, …) | `eng` |
| `-q`, `--quiet` | Suppress progress messages | off |
| `--version` | Print version and exit | — |

### As a library (API)

```python
from ocr_extractor import read_pdf

# Process a PDF and get the text as a string
text = read_pdf("file.pdf", dpi=300, lang="eng")

# You can also use the intermediate steps directly
from ocr_extractor import preprocess_image, clean_text
from pdf2image import convert_from_path

pages = convert_from_path("file.pdf", dpi=300)
gray = preprocess_image(pages[0])  # numpy.ndarray ready for OCR
```

Functions exposed from `ocr_extractor`:

- `preprocess_image(image_pil) -> numpy.ndarray`
- `clean_line(line) -> str | None`
- `clean_text(text) -> str`
- `read_pdf(pdf_path, dpi=300, lang="eng", verbose=True) -> str`
- `__version__` (string, e.g. `"0.1.0"`)

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
├── app.py                      # Thin wrapper that delegates to ocr_extractor.cli
└── ocr_extractor/              # Python package (what gets distributed)
    ├── __init__.py             # Public API + __version__
    ├── core.py                 # preprocess_image, clean_line, clean_text, read_pdf
    └── cli.py                  # argparse + main() (CLI entry point)
```

## 🔍 Code description

### `ocr_extractor.core.preprocess_image(image_pil)`
Converts a PIL image to an OpenCV array, turns it grayscale, and applies
a denoising filter (`cv2.fastNlMeansDenoising`) with the parameters
`h=10`, `templateWindowSize=7`, and `searchWindowSize=21`. Returns the
grayscale image ready for OCR.

### `ocr_extractor.core.clean_line(line)`
Cleans a single text line:
- Discards lines shorter than 2 characters.
- Replaces any character not in `a-zA-Z0-9 '-,.!?'` with a space.
- Collapses multiple spaces into one.
- Discards lines that contain only symbols (`()[]{}_-=+*#@^.,:;<>/\|~`).

### `ocr_extractor.core.clean_text(text)`
Applies `clean_line` to every line of the text and keeps only the lines
that pass the filter. Returns the cleaned text joined with newlines.

### `ocr_extractor.core.read_pdf(pdf_path, dpi=300, lang="eng", verbose=True)`
Iterates over every page of the PDF:
1. Renders each page to an image with `convert_from_path(pdf_path, dpi=dpi)`.
2. Preprocesses the image with `preprocess_image`.
3. Extracts the text with `pytesseract.image_to_string(..., lang=lang)`.
4. Cleans the text with `clean_text`.
5. Wraps the result between the markers
   `=== PAGE N ===` … `=== END PAGE N ===`.

### `ocr_extractor.cli.main(argv=None)`
Entry point registered in `pyproject.toml` as
`ocr-extractor = "ocr_extractor.cli:main"`. Parses arguments with
`argparse`, validates that the PDF exists, calls `read_pdf`, and writes
the result to the output file. Returns the process exit code (`0` for
success, `1` on error).

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
  (`--input`, `-o`, `--lang`, `--dpi`) or the `read_pdf` parameters from
  the API:
  ```python
  from ocr_extractor import read_pdf
  text = read_pdf("file.pdf", dpi=400, lang="spa")
  ```
- **Adjust the resolution**: higher `dpi` (400–600) gives better results
  on low-quality documents, at the cost of more memory and time.
- **Loosen the character filter**: extend the `allowed` set inside
  `ocr_extractor.core.clean_line` to allow additional characters (for
  example, `áéíóúÁÉÍÓÚñÑ¿¡`). Since it lives inside `ocr_extractor/`,
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
| Encoding errors in the `.txt` | File opened without UTF-8 | The CLI uses `encoding="utf-8"`; if you write manually, use the same encoding |
| Slow on long PDFs | 300 DPI rendering + per-page OCR | Lower `--dpi` or process the PDF in batches |

## 🚀 Publishing the package

To build an sdist and a wheel locally (requires the `dev` extra):

```bash
pip install -e ".[dev]"
python -m build
ls dist/   # should show ocr_extractor-0.1.0.tar.gz and *.whl
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
