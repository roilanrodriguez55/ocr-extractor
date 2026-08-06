"""Structured results: words, pages and documents.

These types are what :func:`ocr_extractor.read_document_detailed` returns.
They exist for callers that need more than a blob of text — chiefly a
**confidence** figure, which is what lets a pipeline decide by itself whether a
page came out well enough to trust.

:func:`ocr_extractor.read_document` still returns a plain string and is
unchanged.
"""

from dataclasses import dataclass, field
from typing import Optional, Tuple

PAGE_START = "=== PAGE {label} ==="
PAGE_END = "=== END PAGE {label} ==="


@dataclass(frozen=True)
class Word:
    """One recognised word and where it sits on the page.

    The box is in pixels of the image that was OCR'd, with the origin at the
    top-left. It is what makes it possible to crop a region — a drawing's title
    block, a stamp, a table cell — instead of treating the page as one blob.
    """

    text: str
    confidence: float
    left: int
    top: int
    width: int
    height: int

    @property
    def right(self):
        return self.left + self.width

    @property
    def bottom(self):
        return self.top + self.height


@dataclass(frozen=True)
class PageResult:
    """One page (or slide, or worksheet) of a document.

    ``confidence`` is ``None`` when the text did **not** come from OCR — a
    DOCX, a PPTX, a spreadsheet. That is deliberately not the same as ``100``:
    those texts are exact, so asking how confident the reader was is not a
    meaningful question, and a caller routing low-confidence pages to a human
    should skip them rather than treat them as a perfect score.

    A page that WAS OCR'd but yielded nothing gets ``0.0``, not ``None`` — that
    is precisely the page somebody needs to look at.
    """

    label: str
    text: str
    words: Tuple[Word, ...] = field(default_factory=tuple)
    confidence: Optional[float] = None

    @property
    def is_ocr(self):
        """True when this page went through OCR (and so has a confidence)."""
        return self.confidence is not None

    @property
    def word_count(self):
        """Recognised words. Falls back to whitespace splitting for readers
        that produce text without word boxes."""
        return len(self.words) if self.words else len(self.text.split())


@dataclass(frozen=True)
class DocumentResult:
    """Every page of one file, plus the aggregate figures over them."""

    path: str
    pages: Tuple[PageResult, ...] = field(default_factory=tuple)

    @property
    def text(self):
        """The pages as one string.

        Multi-page documents get the same ``=== PAGE N ===`` markers
        :func:`read_document` produces; a single page is returned bare, also
        matching it. The two entry points therefore agree on output.
        """
        if len(self.pages) == 1:
            return self.pages[0].text

        out = ""
        for page in self.pages:
            out += PAGE_START.format(label=page.label) + "\n\n"
            out += page.text + "\n\n"
            out += PAGE_END.format(label=page.label) + "\n\n"
        return out

    @property
    def confidence(self):
        """Mean confidence across the OCR'd pages, weighted by word count.

        Weighted rather than a flat average because a title page holding four
        words should not drag down — or prop up — the verdict on a page holding
        four hundred. ``None`` when no page went through OCR.
        """
        ocr_pages = [p for p in self.pages if p.is_ocr]
        if not ocr_pages:
            return None

        total_words = sum(p.word_count for p in ocr_pages)
        if total_words == 0:
            # Every page was OCR'd and every one came back empty. That is a
            # real answer -- zero -- not a missing one.
            return 0.0

        weighted = sum(p.confidence * p.word_count for p in ocr_pages)
        return weighted / total_words

    @property
    def word_count(self):
        return sum(p.word_count for p in self.pages)

    @property
    def is_ocr(self):
        """True when any page needed OCR."""
        return any(p.is_ocr for p in self.pages)


__all__ = ["Word", "PageResult", "DocumentResult", "PAGE_START", "PAGE_END"]
