"""Tests for the image readers (single-page and multi-page TIFF).

The OCR pipeline itself (``preprocess_image`` +
``pytesseract.image_to_string`` + ``clean_text``) is covered by the
core tests and exercised end-to-end in the smoke tests against the
shipped ``documento.pdf``. Here we test the **orchestration** of the
image readers:

- The right files are opened.
- Multi-page TIFFs get one marker block per frame.
- Output is correctly assembled.
- Errors propagate cleanly.

A handful of light end-to-end tests verify OCR works on a real
synthetic image, but those tests assert only that *some* text survives,
not specific words.
"""

from unittest import mock

import pytest
from PIL import Image, ImageDraw, ImageSequence

from ocr_extractor.readers.images import read_image, read_tiff


# ---------- synthetic fixtures ----------------------------------------------


def _make_text_image(path, text, size=(800, 200)):
    """Create a white image with black text drawn on it. Saves to ``path``.

    Uses the default PIL font, which renders small but is sufficient for
    Tesseract to extract the text.
    """
    img = Image.new("RGB", size, color="white")
    draw = ImageDraw.Draw(img)
    draw.text((10, 80), text, fill="black")
    img.save(path)
    return path


# ---------- single-page images: orchestration -----------------------------


class TestReadImageOrchestration:
    """Verify the reader's structure (mocking the OCR pipeline)."""

    def test_returns_cleaned_text_without_markers(self, tmp_workdir):
        path = _make_text_image(tmp_workdir / "img.png", "anything")
        with mock.patch(
            "ocr_extractor.readers.images.pytesseract.image_to_string",
            return_value="Hello World",
        ):
            out = read_image(path, verbose=False)

        assert out == "Hello World"
        # Single page → no PAGE/END markers.
        assert "=== PAGE" not in out
        assert "=== END PAGE" not in out

    def test_opens_image_with_pillow(self, tmp_workdir):
        path = _make_text_image(tmp_workdir / "img.png", "anything")
        with mock.patch(
            "ocr_extractor.readers.images.Image.open",
            wraps=Image.open,
        ) as open_spy, mock.patch(
            "ocr_extractor.readers.images.pytesseract.image_to_string",
            return_value="",
        ):
            read_image(path, verbose=False)

        open_spy.assert_called_once()

    def test_clean_text_is_applied(self, tmp_workdir):
        # Lines that would be dropped by clean_text should not appear.
        path = _make_text_image(tmp_workdir / "img.png", "anything")
        with mock.patch(
            "ocr_extractor.readers.images.pytesseract.image_to_string",
            return_value="Real line\n()\nAnother line",
        ):
            out = read_image(path, verbose=False)

        assert "Real line" in out
        assert "Another line" in out
        # () is dropped by clean_text.
        assert "()" not in out

    def test_heic_triggers_heif_registration(self, tmp_workdir, monkeypatch):
        path = tmp_workdir / "img.heic"
        path.write_bytes(b"fake")
        called = []

        import ocr_extractor.readers.images as images_mod

        def fake_ensure():
            called.append(True)

        monkeypatch.setattr(images_mod, "_ensure_heif_support", fake_ensure)
        with mock.patch(
            "ocr_extractor.readers.images.Image.open",
            side_effect=OSError("cannot identify"),
        ):
            with pytest.raises(OSError):
                read_image(path, verbose=False)
        # The HEIC branch must have called _ensure_heif_support.
        assert called == [True]

    def test_non_heic_does_not_trigger_heif_registration(self, tmp_workdir, monkeypatch):
        path = _make_text_image(tmp_workdir / "img.png", "x")
        called = []

        import ocr_extractor.readers.images as images_mod

        def fake_ensure():
            called.append(True)

        monkeypatch.setattr(images_mod, "_ensure_heif_support", fake_ensure)
        with mock.patch(
            "ocr_extractor.readers.images.pytesseract.image_to_string",
            return_value="ok",
        ):
            read_image(path, verbose=False)
        # PNG should NOT trigger HEIF opener registration.
        assert called == []

    def test_verbose_prints_progress(self, tmp_workdir, capsys):
        path = _make_text_image(tmp_workdir / "img.png", "x")
        with mock.patch(
            "ocr_extractor.readers.images.pytesseract.image_to_string",
            return_value="",
        ):
            read_image(path, verbose=True)
        captured = capsys.readouterr()
        assert "Reading" in captured.out

    def test_missing_file_raises(self, tmp_workdir):
        with pytest.raises(FileNotFoundError):
            read_image(tmp_workdir / "no-such.png", verbose=False)


# ---------- single-page images: end-to-end smoke -------------------------


class TestReadImageEndToEnd:
    """Light end-to-end tests with real Tesseract on synthetic images."""

    def test_png_ocr_produces_some_text(self, tmp_workdir):
        path = _make_text_image(tmp_workdir / "img.png", "HELLO")
        text = read_image(path, verbose=False)
        # Tesseract is not pixel-perfect on synthetic text — we only
        # require that the pipeline ran and produced *some* non-empty
        # text without crashing.
        assert text
        assert isinstance(text, str)

    def test_jpg_ocr_produces_some_text(self, tmp_workdir):
        path = _make_text_image(tmp_workdir / "img.jpg", "HELLO")
        text = read_image(path, verbose=False)
        assert text
        assert isinstance(text, str)


# ---------- multi-page TIFF: orchestration --------------------------------


class TestReadTiffOrchestration:
    """Verify the multi-page TIFF reader assembles markers correctly."""

    def _make_multi_tiff(self, tmp_workdir, n_frames=3):
        """Build a multi-frame TIFF with ``n_frames`` frames."""
        frames = [
            _make_text_image(tmp_workdir / f"_frame_{i}.png", f"x")
            for i in range(1, n_frames + 1)
        ]
        tiff_path = tmp_workdir / "multi.tiff"
        imgs = [Image.open(f) for f in frames]
        imgs[0].save(
            tiff_path, save_all=True, append_images=imgs[1:], compression="raw"
        )
        return tiff_path

    def test_single_frame_one_marker_block(self, tmp_workdir):
        tiff_path = self._make_multi_tiff(tmp_workdir, n_frames=1)
        with mock.patch(
            "ocr_extractor.readers.images.pytesseract.image_to_string",
            return_value="hello world",
        ):
            out = read_tiff(tiff_path, verbose=False)

        assert "=== PAGE 1 ===" in out
        assert "=== END PAGE 1 ===" in out
        assert "hello world" in out
        assert "=== PAGE 2 ===" not in out

    def test_multi_frame_each_frame_marked(self, tmp_workdir):
        tiff_path = self._make_multi_tiff(tmp_workdir, n_frames=3)
        with mock.patch(
            "ocr_extractor.readers.images.pytesseract.image_to_string",
            return_value="text content",
        ):
            out = read_tiff(tiff_path, verbose=False)

        for i in (1, 2, 3):
            assert f"=== PAGE {i} ===" in out
            assert f"=== END PAGE {i} ===" in out

        # Markers are in order.
        assert out.index("PAGE 1") < out.index("PAGE 2") < out.index("PAGE 3")

    def test_clean_text_applied_per_frame(self, tmp_workdir):
        tiff_path = self._make_multi_tiff(tmp_workdir, n_frames=2)
        with mock.patch(
            "ocr_extractor.readers.images.pytesseract.image_to_string",
            return_value="Keep this\n()\nAlso keep this",
        ):
            out = read_tiff(tiff_path, verbose=False)

        # Symbol-only "()" dropped; real text survives.
        assert "()" not in out
        assert "Keep this" in out
        assert "Also keep this" in out

    def test_verbose_prints_per_frame(self, tmp_workdir, capsys):
        tiff_path = self._make_multi_tiff(tmp_workdir, n_frames=2)
        with mock.patch(
            "ocr_extractor.readers.images.pytesseract.image_to_string",
            return_value="",
        ):
            read_tiff(tiff_path, verbose=True)
        captured = capsys.readouterr()
        assert "Processing page 1" in captured.out
        assert "Processing page 2" in captured.out

    def test_palette_frame_converted_to_rgb(self, tmp_workdir):
        """Palette-mode TIFF frames must be converted to RGB before
        preprocessing (preprocess_image expects RGB-compatible input).
        """
        tiff_path = tmp_workdir / "palette.tiff"
        Image.new("P", (100, 50)).save(tiff_path)

        with mock.patch(
            "ocr_extractor.readers.images.preprocess_image",
            return_value=__import__("numpy").zeros((50, 100), dtype="uint8"),
        ) as preprocess_spy, mock.patch(
            "ocr_extractor.readers.images.pytesseract.image_to_string",
            return_value="",
        ):
            read_tiff(tiff_path, verbose=False)

        # preprocess_image should have been called with something RGB-like.
        preprocess_spy.assert_called_once()
        (called_arg,), _ = preprocess_spy.call_args
        # PIL Image has a .mode attribute.
        assert called_arg.mode == "RGB"

    def test_missing_file_raises(self, tmp_workdir):
        with pytest.raises(FileNotFoundError):
            read_tiff(tmp_workdir / "no-such.tiff", verbose=False)


# ---------- multi-page TIFF: end-to-end smoke ------------------------------


class TestReadTiffEndToEnd:
    """Light end-to-end tests with real Tesseract on synthetic TIFFs."""

    def test_multi_frame_tiff_ocr(self, tmp_workdir):
        frames = [
            _make_text_image(tmp_workdir / f"_e2e_{i}.png", f"HELLO WORLD {i}")
            for i in range(1, 4)
        ]
        tiff_path = tmp_workdir / "multi.tiff"
        imgs = [Image.open(f) for f in frames]
        imgs[0].save(tiff_path, save_all=True, append_images=imgs[1:])

        text = read_tiff(tiff_path, verbose=False)

        # Three page markers.
        assert text.count("=== PAGE") == 3
        assert text.count("=== END PAGE") == 3
        # OCR extracted at least one full word across all frames.
        assert "HELLO" in text or "WORLD" in text