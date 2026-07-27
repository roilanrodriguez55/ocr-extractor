"""Tests for the format dispatcher and reader registry."""

import pytest

from ocr_extractor import read_document
from ocr_extractor.readers import (
    EXTENSION_READERS,
    SUPPORTED_FORMATS,
    get_reader_name,
)


class TestRegistry:
    def test_supported_formats_is_sorted(self):
        assert SUPPORTED_FORMATS == sorted(SUPPORTED_FORMATS)

    def test_all_expected_extensions_registered(self):
        expected = {
            ".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".webp", ".heic",
            ".tif", ".tiff", ".docx", ".pptx", ".xlsx", ".doc", ".xls", ".ppt",
        ".heic", ".tif", ".tiff",
        }
        assert set(EXTENSION_READERS.keys()) == expected

    def test_get_reader_name_known_extensions(self):
        assert get_reader_name("a.pdf") == "pdf"
        assert get_reader_name("a.PNG") == "image"  # case-insensitive
        assert get_reader_name("a.docx") == "docx"
        assert get_reader_name("a.DOC") == "legacy"
        assert get_reader_name("a.tiff") == "tiff"
        assert get_reader_name("a.xlsx") == "xlsx"

    def test_get_reader_name_unknown_extension(self):
        assert get_reader_name("a.txt") is None
        assert get_reader_name("a.zip") is None
        assert get_reader_name("a") is None


class TestReadDocumentDispatch:
    def test_missing_file_raises(self, tmp_workdir):
        with pytest.raises(FileNotFoundError):
            read_document(tmp_workdir / "does-not-exist.pdf")

    def test_unsupported_extension_raises(self, tmp_workdir):
        fake = tmp_workdir / "foo.txt"
        fake.write_text("hello")
        with pytest.raises(ValueError, match="unsupported file extension"):
            read_document(fake)

    def test_pdf_dispatches_to_pdf_reader(self, tmp_workdir):
        # Create an empty .pdf file; the dispatcher will resolve the reader
        # name without needing the file content to be a real PDF for this
        # check. We mock the actual OCR call.
        from unittest import mock

        fake_pdf = tmp_workdir / "doc.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4\n")

        with mock.patch(
            "ocr_extractor.readers.pdf.convert_from_path",
            return_value=[],
        ):
            out = read_document(fake_pdf, verbose=False)

        # Empty PDF → empty markers but no crash.
        assert out == ""

    def test_image_extension_resolves_to_image_reader(self, tmp_workdir):
        # Verify the dispatch table picks the image reader for the
        # common image extensions. The actual reader implementation is
        # covered in tests/test_images.py (added in step 2).
        from PIL import Image

        for ext in (".png", ".jpg", ".jpeg", ".bmp", ".webp"):
            fake = tmp_workdir / f"img{ext}"
            Image.new("RGB", (10, 10), color=(255, 255, 255)).save(fake)
            assert get_reader_name(fake) == "image"

        # Multi-page TIFF has its own reader.
        for ext in (".tif", ".tiff"):
            fake = tmp_workdir / f"img{ext}"
            assert get_reader_name(fake) == "tiff"