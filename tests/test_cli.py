"""Tests for the CLI entry point."""

import sys
from unittest import mock

import pytest

from ocr_extractor.cli import _build_parser, main


class TestParser:
    def test_positional_is_named_input(self):
        parser = _build_parser()
        # The positional must be 'input', not 'pdf' (backward-compat break).
        # Inspect the action's dest.
        positional = [a for a in _build_parser()._actions if not a.option_strings]
        assert len(positional) == 1
        assert positional[0].dest == "input"

    def test_help_mentions_supported_formats(self):
        parser = _build_parser()
        # The help string lists the supported extensions.
        for ext in (".pdf", ".docx", ".png"):
            assert ext in parser.format_help()

    def test_version_flag(self, capsys):
        parser = _build_parser()
        with pytest.raises(SystemExit) as exc:
            parser.parse_args(["--version"])
        assert exc.value.code == 0
        captured = capsys.readouterr()
        assert "ocr-extractor" in captured.out


class TestMain:
    def test_missing_file_returns_1(self, tmp_workdir, capsys):
        rc = main([str(tmp_workdir / "nope.pdf")])
        assert rc == 1
        captured = capsys.readouterr()
        assert "Error" in captured.err
        assert "nope.pdf" in captured.err

    def test_pdf_runs_through_dispatcher(self, tmp_workdir):
        from PIL import Image

        pdf_path = tmp_workdir / "doc.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n")
        output = tmp_workdir / "out.txt"

        # Even an "empty" PDF should not crash the CLI.
        with mock.patch(
            "ocr_extractor.readers.pdf.convert_from_path",
            return_value=[Image.new("RGB", (100, 50), (255, 255, 255))],
        ), mock.patch(
            "ocr_extractor.readers.pdf.pytesseract.image_to_string",
            return_value="",
        ):
            rc = main([str(pdf_path), "-o", str(output), "-q"])

        assert rc == 0
        assert output.exists()
        # Empty page still gets the opening/closing markers.
        text = output.read_text(encoding="utf-8")
        assert "=== PAGE 1 ===" in text
        assert "=== END PAGE 1 ===" in text

    def test_quiet_flag(self, tmp_workdir, capsys):
        from PIL import Image

        pdf_path = tmp_workdir / "doc.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n")
        output = tmp_workdir / "out.txt"

        with mock.patch(
            "ocr_extractor.readers.pdf.convert_from_path",
            return_value=[Image.new("RGB", (100, 50), (255, 255, 255))],
        ), mock.patch(
            "ocr_extractor.readers.pdf.pytesseract.image_to_string",
            return_value="",
        ):
            main([str(pdf_path), "-o", str(output), "-q"])

        captured = capsys.readouterr()
        # -q suppresses the "Done." confirmation too.
        assert "Done" not in captured.out

    def test_write_failure_returns_1(self, tmp_workdir):
        """If the output path is not writable, CLI returns 1 cleanly."""
        from PIL import Image

        pdf_path = tmp_workdir / "doc.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n")
        # Point output at a path that lives under a non-existent directory.
        bad_output = tmp_workdir / "no-such-dir" / "out.txt"

        with mock.patch(
            "ocr_extractor.readers.pdf.convert_from_path",
            return_value=[Image.new("RGB", (100, 50), (255, 255, 255))],
        ), mock.patch(
            "ocr_extractor.readers.pdf.pytesseract.image_to_string",
            return_value="",
        ):
            rc = main([str(pdf_path), "-o", str(bad_output)])

        assert rc == 1