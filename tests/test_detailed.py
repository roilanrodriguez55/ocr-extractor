"""Tests for the structured extraction path: ``ocr_page`` and
``read_document_detailed``.

The unit tests drive ``ocr_page`` with a hand-built ``image_to_data`` dict so
they run anywhere. The end-to-end ones need a real Tesseract and are skipped
without it.
"""

import shutil
from unittest import mock

import pytest
from PIL import Image, ImageDraw

from ocr_extractor import read_document, read_document_detailed
from ocr_extractor.core import ocr_page
from ocr_extractor.dispatcher import _pages_from_marked_text
from ocr_extractor.result import DocumentResult, PageResult

HAS_TESSERACT = shutil.which("tesseract") is not None
needs_tesseract = pytest.mark.skipif(
    not HAS_TESSERACT, reason="tesseract is not installed"
)


def _data(rows):
    """Build an ``image_to_data`` DICT from (text, conf, block, par, line) rows."""
    keys = ["text", "conf", "left", "top", "width", "height",
            "block_num", "par_num", "line_num"]
    out = {k: [] for k in keys}
    for i, (text, conf, block, par, line) in enumerate(rows):
        out["text"].append(text)
        out["conf"].append(conf)
        out["left"].append(i * 10)
        out["top"].append(0)
        out["width"].append(9)
        out["height"].append(5)
        out["block_num"].append(block)
        out["par_num"].append(par)
        out["line_num"].append(line)
    return out


def _blank():
    return Image.new("RGB", (60, 30), color="white")


class TestOcrPage:
    def test_layout_rows_are_not_words(self):
        # Tesseract emits a row per block/paragraph/line with conf == -1.
        # Counting those as words inflates the count and poisons the mean.
        data = _data([
            ("", -1, 1, 1, 1),
            ("PLANO", 95.0, 1, 1, 1),
            ("", -1, 1, 1, 2),
            ("REV", 85.0, 1, 1, 2),
        ])
        with mock.patch("pytesseract.image_to_data", return_value=data):
            page = ocr_page(_blank())

        assert [w.text for w in page.words] == ["PLANO", "REV"]
        assert page.confidence == 90.0

    def test_line_structure_survives(self):
        # A title block is a stack of short lines. Flattening it into one run
        # destroys the only structure it had.
        data = _data([
            ("ESCALA", 90.0, 1, 1, 1),
            ("1:50", 88.0, 1, 1, 1),
            ("REV", 91.0, 1, 1, 2),
            ("B", 87.0, 1, 1, 2),
        ])
        with mock.patch("pytesseract.image_to_data", return_value=data):
            page = ocr_page(_blank())

        assert page.text == "ESCALA 1:50\nREV B"

    def test_a_page_with_no_words_scores_zero_not_none(self):
        with mock.patch("pytesseract.image_to_data", return_value=_data([])):
            page = ocr_page(_blank())

        assert page.confidence == 0.0
        assert page.is_ocr is True
        assert page.words == ()

    def test_boxes_are_carried_through(self):
        data = _data([("CIMENTACIÓN", 93.0, 1, 1, 1)])
        with mock.patch("pytesseract.image_to_data", return_value=data):
            page = ocr_page(_blank())

        word = page.words[0]
        assert (word.left, word.top, word.width, word.height) == (0, 0, 9, 5)
        assert word.right == 9

    def test_raw_by_default_and_cleaned_on_request(self):
        # `clean` defaults to False here: a caller asking for structure wants
        # what Tesseract actually said.
        data = _data([("N°", 90.0, 1, 1, 1), ("4521", 92.0, 1, 1, 1)])
        with mock.patch("pytesseract.image_to_data", return_value=data):
            raw = ocr_page(_blank())
            cleaned = ocr_page(_blank(), clean=True)

        assert "°" in raw.text
        assert "°" not in cleaned.text

    def test_preprocess_can_be_skipped(self):
        data = _data([("X", 90.0, 1, 1, 1)])
        with mock.patch("pytesseract.image_to_data", return_value=data), \
                mock.patch("ocr_extractor.core.preprocess_image") as prep:
            ocr_page(_blank(), preprocess=False)

        prep.assert_not_called()


class TestMarkedTextSplitting:
    def test_numbered_pages(self):
        text = (
            "=== PAGE 1 ===\n\nfirst\n\n=== END PAGE 1 ===\n\n"
            "=== PAGE 2 ===\n\nsecond\n\n=== END PAGE 2 ===\n\n"
        )
        pages = _pages_from_marked_text(text)

        assert [p.label for p in pages] == ["1", "2"]
        assert [p.text for p in pages] == ["first", "second"]

    def test_named_pages(self):
        # Worksheets carry names, not numbers.
        text = "=== PAGE Costes ===\n\nrows\n\n=== END PAGE Costes ===\n\n"
        pages = _pages_from_marked_text(text)

        assert pages[0].label == "Costes"

    def test_unmarked_text_is_one_page(self):
        pages = _pages_from_marked_text("plain body")

        assert len(pages) == 1
        assert pages[0].text == "plain body"

    def test_split_pages_carry_no_confidence(self):
        pages = _pages_from_marked_text("body from a docx")
        assert pages[0].confidence is None

    def test_the_regex_stays_in_sync_with_the_marker_constants(self):
        # The parser is built from PAGE_START/PAGE_END rather than repeating
        # them, and this is what keeps that true. A drifted copy would fail
        # SILENTLY — still emitting, still parsing as nothing — so every Office
        # file would come back as one unsplit page with no error anywhere.
        emitted = DocumentResult(
            path='x.xlsx',
            pages=(
                PageResult(label='Costes', text='first'),
                PageResult(label='Plazos', text='second'),
            ),
        ).text

        parsed = _pages_from_marked_text(emitted)

        assert [p.label for p in parsed] == ['Costes', 'Plazos']
        assert [p.text for p in parsed] == ['first', 'second']

    def test_a_readers_own_output_parses(self):
        # The round-trip above only proves DocumentResult.text agrees with the
        # parser — both build on the constants. This proves the READERS do too.
        # They used to spell the markers out themselves, which left the
        # constants decorative for producers: changing them would have moved
        # the parser and not the five emitters, and every Office file would
        # have come back as one unsplit page with no error anywhere.
        from ocr_extractor.result import wrap_page

        emitted = wrap_page('Costes', 'first') + wrap_page(2, 'second')
        parsed = _pages_from_marked_text(emitted)

        assert [p.label for p in parsed] == ['Costes', '2']
        assert [p.text for p in parsed] == ['first', 'second']

    def test_a_label_cannot_swallow_a_block_boundary(self):
        # `[^=\n]+?` rather than `.+?`: labels are page numbers or worksheet
        # names, so constraining them stops the pattern spanning two blocks if
        # a body ever contains marker-like text.
        text = (
            '=== PAGE 1 ===\n\nbody one\n\n=== END PAGE 1 ===\n\n'
            '=== PAGE 2 ===\n\nbody two\n\n=== END PAGE 2 ===\n\n'
        )
        assert len(_pages_from_marked_text(text)) == 2


class TestDispatch:
    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            read_document_detailed(tmp_path / "nope.pdf")

    def test_unsupported_extension_raises(self, tmp_path):
        p = tmp_path / "notes.rtf"
        p.write_text("x")
        with pytest.raises(ValueError):
            read_document_detailed(p)

    def test_dpi_reaches_the_pdf_renderer(self, tmp_path):
        # dpi is the single biggest lever on OCR quality for a scanned plan.
        # Accepted at the API and dropped on the way down would be invisible:
        # the text still comes back, just worse.
        p = tmp_path / 'plan.pdf'
        p.write_bytes(b'%PDF-1.4 stub')

        with mock.patch(
            'ocr_extractor.readers.pdf.convert_from_path', return_value=[],
        ) as render:
            read_document_detailed(p, dpi=600, verbose=False)

        render.assert_called_once()
        assert render.call_args.kwargs['dpi'] == 600

    def test_office_files_report_no_confidence(self, tmp_path):
        # Their text is exact — there is nothing for a reviewer to check.
        p = tmp_path / "report.docx"
        p.write_text("x")
        with mock.patch(
            "ocr_extractor.dispatcher.read_document",
            return_value="=== PAGE 1 ===\n\nexact\n\n=== END PAGE 1 ===\n\n",
        ):
            doc = read_document_detailed(p, verbose=False)

        assert doc.confidence is None
        assert doc.is_ocr is False
        assert doc.pages[0].text == "exact"


@needs_tesseract
class TestAgainstRealTesseract:
    """Proves the shape assumed of ``image_to_data`` is the real one."""

    @staticmethod
    def _image_with(path, text):
        img = Image.new("RGB", (900, 220), color="white")
        draw = ImageDraw.Draw(img)
        draw.text((20, 90), text, fill="black")
        img.save(path)
        return path

    def test_confidence_and_words_come_back(self, tmp_path):
        p = self._image_with(tmp_path / "scan.png", "FOUNDATION PLAN REV B")
        doc = read_document_detailed(p, verbose=False)

        assert doc.is_ocr is True
        assert 0.0 <= doc.confidence <= 100.0
        assert doc.pages[0].words, "expected at least one word with a box"
        for word in doc.pages[0].words:
            assert word.width > 0 and word.height > 0

    def test_blank_page_is_flagged_by_a_zero_score(self, tmp_path):
        # The routing case: nothing readable, so it must not look confident.
        p = tmp_path / "blank.png"
        Image.new("RGB", (400, 200), color="white").save(p)

        doc = read_document_detailed(p, verbose=False)

        assert doc.confidence == 0.0

    def test_detailed_text_matches_read_document(self, tmp_path):
        # Same pass, same words — only the extra structure differs.
        p = self._image_with(tmp_path / "scan.png", "ARCHIVE")

        plain = read_document(p, verbose=False)
        detailed = read_document_detailed(p, verbose=False, clean=True)

        assert plain.split() == detailed.text.split()
