# API reference

Every public symbol exported from the `ocr_extractor` package. The package surface is small on purpose — the dispatcher and the structured-result types are the main extension points.

## Table of contents

- [Entry points](#entry-points)
  - [`read_document`](#read_document)
  - [`read_document_detailed`](#read_document_detailed)
- [Per-image helpers](#per-image-helpers)
  - [`ocr_page`](#ocr_page)
  - [`preprocess_image`](#preprocess_image)
- [Text cleaning](#text-cleaning)
  - [`clean_line`](#clean_line)
  - [`clean_text`](#clean_text)
  - [`DEFAULT_PUNCTUATION`](#default_punctuation)
- [Structured result types](#structured-result-types)
  - [`Word`](#word)
  - [`PageResult`](#pageresult)
  - [`DocumentResult`](#documentresult)
- [Deprecations](#deprecations)
  - [`read_pdf`](#read_pdf)
- [Other exports](#other-exports)
  - [`SUPPORTED_FORMATS`](#supported_formats)
  - [`__version__`](#__version__)

---

## Entry points

### `read_document`

```python
ocr_extractor.read_document(path, *, dpi=300, lang="eng", verbose=True) -> str
```

Read any supported document and return its extracted text as a single string.

Format detection is purely extension-based — see [Supported formats](supported-formats.md). Multi-page inputs (PDF, TIFF, PPTX, XLSX) return the text wrapped in `=== PAGE N ===` / `=== END PAGE N ===` marker blocks; single-page inputs (PNG, JPG, DOCX) return bare text.

**Parameters**

| Name | Type | Default | Notes |
|---|---|---|---|
| `path` | `str` or `pathlib.Path` | — | Path to the input file. |
| `dpi` | `int` | `300` | Render resolution for OCR-based readers. Ignored by text-extraction readers. |
| `lang` | `str` | `"eng"` | Tesseract language code, e.g. `"spa"`, `"spa+eng"`. Ignored by text-extraction readers. |
| `verbose` | `bool` | `True` | Print progress messages. |

**Returns** `str` — the extracted text, with marker blocks for multi-page inputs.

**Raises** `FileNotFoundError` if the path does not exist; `ValueError` if the extension is not in the supported list.

**Example**

```python
from ocr_extractor import read_document

text = read_document("plano.pdf", lang="spa+eng", verbose=False)
```

### `read_document_detailed`

```python
ocr_extractor.read_document_detailed(
    path, *, dpi=300, lang="eng", verbose=True,
    clean=False, punctuation=DEFAULT_PUNCTUATION,
) -> DocumentResult
```

Same dispatch as `read_document`, but returns a structured `DocumentResult`. Per-page confidence is available for OCR'd pages; per-word bounding boxes are available for OCR'd pages.

The default for `clean` is **the opposite** of `read_document` (`False` here). A caller asking for structured output normally wants what Tesseract actually said, punctuation and accents included.

**Parameters**

| Name | Type | Default | Notes |
|---|---|---|---|
| `path` | `str` or `pathlib.Path` | — | Path to the input file. |
| `dpi` | `int` | `300` | Render resolution for OCR-based readers. |
| `lang` | `str` | `"eng"` | Tesseract language code. |
| `verbose` | `bool` | `True` | Print progress messages. |
| `clean` | `bool` | `False` | Apply `clean_text` to the page text. |
| `punctuation` | `str` | `DEFAULT_PUNCTUATION` | Characters `clean_line` keeps when `clean=True`. |

**Returns** [`DocumentResult`](#documentresult).

**Raises** Same as `read_document`.

**Example — routing low-quality pages to a human**

```python
from ocr_extractor import read_document_detailed

doc = read_document_detailed("scan.pdf", lang="eng")
if doc.confidence < 70:
    escalate_to_human_review(doc)
```

**Example — pulling out a title block**

```python
doc = read_document_detailed("drawing.png")
title_block_words = [
    w for w in doc.pages[0].words
    if 0 <= w.top < 200   # title block sits at the top
]
```

---

## Per-image helpers

### `ocr_page`

```python
ocr_extractor.ocr_page(
    image_pil, *, lang="eng", label="1", clean=False,
    punctuation=DEFAULT_PUNCTUATION, preprocess=True,
) -> PageResult
```

OCR a single Pillow image and return a `PageResult`. Uses `pytesseract.image_to_data` instead of `image_to_string`: the same Tesseract pass at the same cost, plus a confidence and bounding box per word.

**Parameters**

| Name | Type | Default | Notes |
|---|---|---|---|
| `image_pil` | `PIL.Image.Image` | — | The page to read. |
| `lang` | `str` | `"eng"` | Tesseract language code. |
| `label` | `str` | `"1"` | Page label carried into the result. |
| `clean` | `bool` | `False` | Apply `clean_text` to the page text. |
| `punctuation` | `str` | `DEFAULT_PUNCTUATION` | Passed to `clean_text` when `clean=True`. |
| `preprocess` | `bool` | `True` | Apply `preprocess_image` first. Turn off for already-binarised images or when the denoiser is eating thin strokes. |

**Returns** [`PageResult`](#pageresult).

**Example**

```python
from PIL import Image
from ocr_extractor import ocr_page

img = Image.open("page.png")
page = ocr_page(img, lang="eng", label="scan-1")
```

### `preprocess_image`

```python
ocr_extractor.preprocess_image(image_pil) -> numpy.ndarray
```

Convert a Pillow image to grayscale and apply `cv2.fastNlMeansDenoising`. Returns the image as a NumPy array suitable for direct input to `pytesseract`.

**Parameters**

| Name | Type | Notes |
|---|---|---|
| `image_pil` | `PIL.Image.Image` | Input image. RGB or convertible to RGB. |

**Returns** `numpy.ndarray` — a 2D grayscale array (`shape == (H, W)`, `dtype == uint8`).

**Example**

```python
import pytesseract
from PIL import Image
from ocr_extractor import preprocess_image

gray = preprocess_image(Image.open("scan.png"))
text = pytesseract.image_to_string(gray, lang="eng")
```

---

## Text cleaning

### `clean_line`

```python
ocr_extractor.clean_line(line, punctuation=DEFAULT_PUNCTUATION) -> str | None
```

Clean a single text line: drop short lines and symbol-only lines, replace disallowed characters with spaces, collapse runs of whitespace.

**Unicode-aware since 0.3.2.** Letters and digits from **every** alphabet (`str.isalnum()`) are kept, so Spanish, French, German, Cyrillic, CJK and other alphabets pass through unchanged. ASCII-only input produces byte-for-byte identical output to earlier releases.

**Parameters**

| Name | Type | Default | Notes |
|---|---|---|---|
| `line` | `str` | — | The text line to clean. |
| `punctuation` | `str` | `DEFAULT_PUNCTUATION` | Extra characters to keep alongside letters and digits. |

**Returns** `str | None` — the cleaned line, or `None` if the line should be discarded (length under 2 after cleaning, or symbol-only).

**Example**

```python
from ocr_extractor import clean_line, DEFAULT_PUNCTUATION

clean_line("Cimentación")                              # 'Cimentación'
clean_line("Escala 1:50")                              # 'Escala 1 50'
clean_line("Escala 1:50", punctuation=DEFAULT_PUNCTUATION + ":/,")  # 'Escala 1:50'
```

### `clean_text`

```python
ocr_extractor.clean_text(text, punctuation=DEFAULT_PUNCTUATION) -> str
```

Apply `clean_line` to every line of `text` and return the result, keeping only the lines that pass.

**Parameters**

| Name | Type | Default | Notes |
|---|---|---|---|
| `text` | `str` | — | Raw text produced by OCR. |
| `punctuation` | `str` | `DEFAULT_PUNCTUATION` | Passed through to `clean_line`. |

**Returns** `str` — the cleaned lines joined by `\n`.

### `DEFAULT_PUNCTUATION`

```python
DEFAULT_PUNCTUATION = " '-.!?"
```

Characters `clean_line` keeps alongside letters and digits. Everything else becomes a space.

Technical documents often need more — `:` for scales, `/` for dates, `,` for decimals. Widen it by concatenation:

```python
clean_line("Escala 1:50", punctuation=DEFAULT_PUNCTUATION + ":/,")
```

---

## Structured result types

All three types live in `ocr_extractor.result` and are re-exported from the top-level package. They are `@dataclass(frozen=True)`, so they are hashable and immutable.

### `Word`

One recognised word and where it sits on the page.

**Fields**

| Field | Type | Notes |
|---|---|---|
| `text` | `str` | The word as Tesseract read it. |
| `confidence` | `float` | Tesseract's confidence for this word (0–100). |
| `left` | `int` | X coordinate of the left edge, in pixels. |
| `top` | `int` | Y coordinate of the top edge, in pixels. |
| `width` | `int` | Width of the box, in pixels. |
| `height` | `int` | Height of the box, in pixels. |

**Properties**

| Name | Type | Notes |
|---|---|---|
| `right` | `int` | `left + width`. Useful for cropping. |
| `bottom` | `int` | `top + height`. Useful for cropping. |

The origin is at the top-left of the image that was OCR'd. Boxes are inclusive of `left`/`top`, exclusive of `right`/`bottom` (standard image-pixel convention).

**Example**

```python
word = Word("CIMENTACIÓN", confidence=93.0, left=10, top=20, width=80, height=12)
assert word.right == 90
assert word.bottom == 32
```

### `PageResult`

One page (or slide, or worksheet) of a document.

**Fields**

| Field | Type | Default | Notes |
|---|---|---|---|
| `label` | `str` | — | Page label: `"1"`, `"Sheet1"`, `"Costes"`, etc. |
| `text` | `str` | — | Page text. Line breaks preserved. |
| `words` | `Tuple[Word, ...]` | `()` | Empty for text-extraction readers. |
| `confidence` | `Optional[float]` | `None` | `None` for text-extraction readers; `0.0` for an OCR'd page that yielded nothing. |

**Properties**

| Name | Type | Notes |
|---|---|---|
| `is_ocr` | `bool` | `True` when the page went through OCR (i.e. `confidence is not None`). |
| `word_count` | `int` | Number of recognised words. Falls back to `len(text.split())` for text-extraction readers. |

**The `None` vs `0.0` distinction matters.** A caller routing low-confidence pages to a human must:

- **skip** pages with `confidence is None` (exact text — nothing to review);
- **flag** pages with `confidence == 0.0` (OCR ran and found nothing — that's the page somebody needs to look at).

### `DocumentResult`

Every page of one file, plus the aggregate figures over them.

**Fields**

| Field | Type | Default | Notes |
|---|---|---|---|
| `path` | `str` | — | The original input path. |
| `pages` | `Tuple[PageResult, ...]` | `()` | All pages, in order. |

**Properties**

| Name | Type | Notes |
|---|---|---|
| `text` | `str` | All pages joined in the same marker format `read_document` emits. Single-page inputs return bare text. |
| `confidence` | `Optional[float]` | Mean confidence across OCR'd pages, **weighted by word count**. `None` if no page was OCR'd; `0.0` if every OCR'd page came back empty. |
| `word_count` | `int` | Total words across all pages. |
| `is_ocr` | `bool` | `True` if any page needed OCR. |

**Why weighted, not flat?** A title page holding four words should not drag down — or prop up — the verdict on a body page holding four hundred.

**`text` is byte-for-byte equivalent** to what `read_document` would return for the same input. This is locked in by the test `tests/test_detailed.py::TestAgainstRealTesseract::test_detailed_text_matches_read_document`.

---

## Deprecations

### `read_pdf`

```python
ocr_extractor.read_pdf(pdf_path, dpi=300, lang="eng", verbose=True) -> str
```

Deprecated since 0.3.0. Emits a `DeprecationWarning` and delegates to the dispatcher.

Use [`read_document`](#read_document) instead. `read_pdf` will be removed in the next major release.

---

## Other exports

### `SUPPORTED_FORMATS`

```python
SUPPORTED_FORMATS: tuple[str, ...]
```

Sorted tuple of every extension the dispatcher accepts. Useful for validating user input in a UI layer:

```python
from pathlib import Path
from ocr_extractor import SUPPORTED_FORMATS

def is_supported(path):
    return Path(path).suffix.lower() in SUPPORTED_FORMATS
```

### `__version__`

```python
__version__: str
```

The package version, kept in sync with `pyproject.toml`. Read this rather than importing from `importlib.metadata` so the source and the runtime agree.

```python
import ocr_extractor
print(ocr_extractor.__version__)
```
