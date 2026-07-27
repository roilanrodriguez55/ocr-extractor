"""Tests for the PDF reader.

The PDF reader orchestrates pdf2image → preprocess_image → pytesseract →
clean_text, wrapping the result in ``=== PAGE N ===`` / ``=== END PAGE N
===`` markers. We mock pdf2image and pytesseract to keep tests fast and
deterministic; the heavy lifting is covered by the unit tests in
``test_core.py``.
"""

import warnings
from unittest import mock

import pytest

from ocr_extractor.readers.pdf import read_pdf_pages


# A single page worth of fake OCR output — long enough to survive the
# line-length filter and containing real words.
_FAKE_OCR_1 = "Hello world from page one.\nThis is a sample line."
_FAKE_OCR_2 = "Second page contents here.\nAnother readable line."


def _fake_pdf_pages():
    """Yield two mock PIL images."""
    from PIL import Image

    return [Image.new("RGB", (100, 50), color=(255, 255, 255))] * 2


class TestReadPdfPages:
    def test_markers_around_each_page(self):
        with mock.patch(
            "ocr_extractor.readers.pdf.convert_from_path",
            return_value=_fake_pdf_pages(),
        ), mock.patch(
            "ocr_extractor.readers.pdf.pytesseract.image_to_string",
            side_effect=[_FAKE_OCR_1, _FAKE_OCR_2],
        ):
            out = read_pdf_pages("dummy.pdf", dpi=150, lang="eng", verbose=False)

        # Two pages, two markers each.
        assert "=== PAGE 1 ===" in out
        assert "=== END PAGE 1 ===" in out
        assert "=== PAGE 2 ===" in out
        assert "=== END PAGE 2 ===" in out

        # Order: page 1 opens before page 2.
        assert out.index("=== PAGE 1 ===") < out.index("=== PAGE 2 ===")

    def test_each_page_text_present(self):
        with mock.patch(
            "ocr_extractor.readers.pdf.convert_from_path",
            return_value=_fake_pdf_pages(),
        ), mock.patch(
            "ocr_extractor.readers.pdf.pytesseract.image_to_string",
            side_effect=[_FAKE_OCR_1, _FAKE_OCR_2],
        ):
            out = read_pdf_pages("dummy.pdf", verbose=False)

        assert "Hello world" in out
        assert "page one" in out
        assert "Second page" in out

    def test_verbose_flag_is_optional(self, capsys):
        with mock.patch(
            "ocr_extractor.readers.pdf.convert_from_path",
            return_value=_fake_pdf_pages(),
        ), mock.patch(
            "ocr_extractor.readers.pdf.pytesseract.image_to_string",
            return_value=_FAKE_OCR_1,  # same OCR output for every call
        ):
            read_pdf_pages("dummy.pdf", verbose=False)
            captured = capsys.readouterr()
            # No progress when verbose=False.
            assert "Processing page" not in captured.out

            read_pdf_pages("dummy.pdf", verbose=True)
            captured = capsys.readouterr()
            assert "Processing page 1" in captured.out
            assert "Processing page 2" in captured.out

    def test_output_identical_to_legacy_read_pdf(self):
        """The new reader must produce byte-identical output to the
        deprecated ``core.read_pdf`` wrapper (excluding the DeprecationWarning).
        """
        from ocr_extractor.core import _read_pdf_legacy

        with mock.patch(
            "ocr_extractor.readers.pdf.convert_from_path",
            return_value=_fake_pdf_pages(),
        ), mock.patch(
            "ocr_extractor.readers.pdf.pytesseract.image_to_string",
            side_effect=[_FAKE_OCR_1, _FAKE_OCR_2],
        ):
            new_out = read_pdf_pages("dummy.pdf", verbose=False)

        with mock.patch(
            "ocr_extractor.core.convert_from_path",
            return_value=_fake_pdf_pages(),
        ), mock.patch(
            "ocr_extractor.core.pytesseract.image_to_string",
            side_effect=[_FAKE_OCR_1, _FAKE_OCR_2],
        ):
            legacy_out = _read_pdf_legacy("dummy.pdf", verbose=False)

        assert new_out == legacy_out


class TestDeprecatedReadPdf:
    def test_emits_deprecation_warning(self):
        with mock.patch(
            "ocr_extractor.core.convert_from_path",
            return_value=_fake_pdf_pages(),
        ), mock.patch(
            "ocr_extractor.core.pytesseract.image_to_string",
            side_effect=[_FAKE_OCR_1, _FAKE_OCR_2],
        ):
            from ocr_extractor.core import read_pdf
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                read_pdf("dummy.pdf", verbose=False)

        assert any(
            issubclass(w.category, DeprecationWarning)
            and "read_pdf" in str(w.message)
            for w in caught
        )

    def test_still_returns_valid_text(self):
        from ocr_extractor.core import read_pdf

        with mock.patch(
            "ocr_extractor.core.convert_from_path",
            return_value=_fake_pdf_pages(),
        ), mock.patch(
            "ocr_extractor.core.pytesseract.image_to_string",
            side_effect=[_FAKE_OCR_1, _FAKE_OCR_2],
        ):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                out = read_pdf("dummy.pdf", verbose=False)

        assert "=== PAGE 1 ===" in out
        assert "Hello world" in out