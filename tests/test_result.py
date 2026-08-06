"""Tests for the structured result types.

The aggregate figures on ``DocumentResult`` are what a calling pipeline routes
on, so the distinctions they encode -- "not OCR" versus "OCR found nothing" --
are behaviour, not presentation.
"""

from ocr_extractor.result import DocumentResult, PageResult, Word


def _page(label, text, confidence=None, words=()):
    return PageResult(label=label, text=text, confidence=confidence, words=words)


class TestPageResult:
    def test_non_ocr_page_has_no_confidence(self):
        # A DOCX is exact text. "How confident were you?" is not a meaningful
        # question about it, and 100 would be a different claim than None.
        page = _page("1", "exact text")
        assert page.confidence is None
        assert page.is_ocr is False

    def test_ocr_page_that_found_nothing_scores_zero(self):
        # Zero is an answer; None is the absence of one. This page is exactly
        # the one a human should look at.
        page = _page("1", "", confidence=0.0)
        assert page.is_ocr is True
        assert page.word_count == 0

    def test_word_count_prefers_boxes(self):
        words = (Word("a", 90.0, 0, 0, 1, 1), Word("b", 80.0, 2, 0, 1, 1))
        page = _page("1", "a b c d e", confidence=85.0, words=words)
        assert page.word_count == 2

    def test_word_count_falls_back_to_splitting(self):
        assert _page("1", "one two three").word_count == 3


class TestWordGeometry:
    def test_right_and_bottom_are_derived(self):
        word = Word("REV", 96.0, left=10, top=20, width=30, height=8)
        assert word.right == 40
        assert word.bottom == 28


class TestDocumentConfidence:
    def test_none_when_nothing_was_ocred(self):
        doc = DocumentResult("a.docx", (_page("1", "x"), _page("2", "y")))
        assert doc.confidence is None
        assert doc.is_ocr is False

    def test_weighted_by_word_count(self):
        # A title page holding four words must not weigh the same as a body
        # page holding four hundred. Flat averaging would let it.
        light = _page("1", " ".join(["w"] * 10), confidence=20.0)
        heavy = _page("2", " ".join(["w"] * 90), confidence=90.0)
        doc = DocumentResult("a.pdf", (light, heavy))

        # (20*10 + 90*90) / 100 = 83.0 — not the flat 55.0.
        assert doc.confidence == 83.0

    def test_ignores_non_ocr_pages(self):
        ocr = _page("1", "w w", confidence=40.0)
        exact = _page("2", "w w w w w w w w")
        doc = DocumentResult("a.pdf", (ocr, exact))
        assert doc.confidence == 40.0

    def test_all_pages_empty_is_zero_not_none(self):
        doc = DocumentResult("a.pdf", (_page("1", "", 0.0), _page("2", "", 0.0)))
        assert doc.confidence == 0.0


class TestDocumentText:
    def test_single_page_has_no_markers(self):
        # Matches read_document, which returns a bare string for an image.
        doc = DocumentResult("a.png", (_page("1", "hello"),))
        assert doc.text == "hello"

    def test_multi_page_uses_the_same_markers_as_read_document(self):
        doc = DocumentResult("a.pdf", (_page("1", "one"), _page("2", "two")))
        text = doc.text

        assert "=== PAGE 1 ===" in text
        assert "=== END PAGE 1 ===" in text
        assert text.index("one") < text.index("=== PAGE 2 ===")

    def test_labels_need_not_be_numbers(self):
        # Worksheets are named, not numbered.
        doc = DocumentResult("a.xlsx", (_page("Costes", "x"), _page("Plazos", "y")))
        assert "=== PAGE Costes ===" in doc.text
