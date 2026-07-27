"""Tests for the legacy Office reader (.doc, .xls, .ppt via LibreOffice).

LibreOffice (``soffice``) is not assumed to be installed in CI; we
mock ``subprocess.run`` so the tests are deterministic. A separate
integration test (skipped by default) runs an actual conversion when
``soffice`` is available.
"""

from unittest import mock

import pytest

from ocr_extractor.readers.legacy import read_legacy_office


# ---------- subprocess mock helpers -----------------------------------------


def _fake_convert_run(*args, **kwargs):
    """Pretend ``soffice --convert-to`` ran successfully.

    The side effect: create a fake converted file in the requested
    outdir so ``_convert_with_libreoffice`` finds it.
    """
    cmd = args[0]
    outdir = cmd[cmd.index("--outdir") + 1]
    target_format = cmd[cmd.index("--convert-to") + 1]
    # input file is the last positional arg
    input_path = cmd[-1]
    from pathlib import Path

    converted = Path(outdir) / (Path(input_path).stem + "." + target_format)
    converted.write_text("converted content")

    fake_result = mock.MagicMock()
    fake_result.returncode = 0
    fake_result.stderr = b""
    return fake_result


# ---------- tests ----------------------------------------------------------


class TestReadLegacyOffice:
    def test_dispatches_doc_to_docx_reader(self, tmp_workdir):
        path = tmp_workdir / "doc.doc"
        path.write_bytes(b"fake doc")

        with mock.patch(
            "ocr_extractor.readers.legacy.subprocess.run",
            side_effect=_fake_convert_run,
        ), mock.patch(
            "ocr_extractor.readers.docx.read_docx",
            return_value="DOCX-CONTENT",
        ) as docx_spy:
            result = read_legacy_office(path, verbose=False)

        assert result == "DOCX-CONTENT"
        docx_spy.assert_called_once()

    def test_dispatches_xls_to_xlsx_reader(self, tmp_workdir):
        path = tmp_workdir / "sheet.xls"
        path.write_bytes(b"fake xls")

        with mock.patch(
            "ocr_extractor.readers.legacy.subprocess.run",
            side_effect=_fake_convert_run,
        ), mock.patch(
            "ocr_extractor.readers.xlsx.read_xlsx",
            return_value="XLSX-CONTENT",
        ) as xlsx_spy:
            result = read_legacy_office(path, verbose=False)

        assert result == "XLSX-CONTENT"
        xlsx_spy.assert_called_once()

    def test_dispatches_ppt_to_pptx_reader(self, tmp_workdir):
        path = tmp_workdir / "deck.ppt"
        path.write_bytes(b"fake ppt")

        with mock.patch(
            "ocr_extractor.readers.legacy.subprocess.run",
            side_effect=_fake_convert_run,
        ), mock.patch(
            "ocr_extractor.readers.pptx.read_pptx",
            return_value="PPTX-CONTENT",
        ) as pptx_spy:
            result = read_legacy_office(path, verbose=False)

        assert result == "PPTX-CONTENT"
        pptx_spy.assert_called_once()

    def test_soffice_not_installed_raises_clear_error(self, tmp_workdir):
        path = tmp_workdir / "doc.doc"
        path.write_bytes(b"fake doc")

        with mock.patch(
            "ocr_extractor.readers.legacy.subprocess.run",
            side_effect=FileNotFoundError("soffice"),
        ):
            with pytest.raises(RuntimeError) as exc_info:
                read_legacy_office(path, verbose=False)

        msg = str(exc_info.value)
        # Error mentions the missing tool and how to install it.
        assert "soffice" in msg.lower()
        assert "install" in msg.lower()
        # At least one concrete install hint is present.
        assert any(
            hint in msg
            for hint in ("apt-get install libreoffice", "brew install", "dnf install")
        )

    def test_soffice_timeout_raises_runtime_error(self, tmp_workdir):
        import subprocess as sp

        path = tmp_workdir / "doc.doc"
        path.write_bytes(b"fake doc")

        with mock.patch(
            "ocr_extractor.readers.legacy.subprocess.run",
            side_effect=sp.TimeoutExpired(cmd=["soffice"], timeout=180),
        ):
            with pytest.raises(RuntimeError, match="timed out"):
                read_legacy_office(path, verbose=False)

    def test_soffice_nonzero_exit_raises_runtime_error(self, tmp_workdir):
        path = tmp_workdir / "doc.doc"
        path.write_bytes(b"fake doc")

        fake_result = mock.MagicMock()
        fake_result.returncode = 1
        fake_result.stderr = b"some error from soffice"

        with mock.patch(
            "ocr_extractor.readers.legacy.subprocess.run",
            return_value=fake_result,
        ):
            with pytest.raises(RuntimeError) as exc_info:
                read_legacy_office(path, verbose=False)

        msg = str(exc_info.value)
        assert "exit code 1" in msg
        assert "some error from soffice" in msg

    def test_missing_converted_file_raises_runtime_error(self, tmp_workdir):
        # Simulate soffice succeeding but NOT writing the expected file.
        fake_result = mock.MagicMock()
        fake_result.returncode = 0
        fake_result.stderr = b""

        path = tmp_workdir / "doc.doc"
        path.write_bytes(b"fake doc")

        with mock.patch(
            "ocr_extractor.readers.legacy.subprocess.run",
            return_value=fake_result,
        ):
            with pytest.raises(RuntimeError, match="not.*produced"):
                read_legacy_office(path, verbose=False)

    def test_unsupported_legacy_extension_raises(self, tmp_workdir):
        path = tmp_workdir / "doc.xyz"
        path.write_bytes(b"x")
        with pytest.raises(ValueError, match="unsupported legacy extension"):
            read_legacy_office(path, verbose=False)

    def test_missing_input_file_raises(self, tmp_workdir):
        with pytest.raises(FileNotFoundError):
            read_legacy_office(tmp_workdir / "nope.doc", verbose=False)

    def test_soffice_invocation_flags(self, tmp_workdir):
        """The exact command must include headless and convert-to."""
        path = tmp_workdir / "doc.doc"
        path.write_bytes(b"fake doc")

        with mock.patch(
            "ocr_extractor.readers.legacy.subprocess.run",
            side_effect=_fake_convert_run,
        ) as run_spy, mock.patch(
            "ocr_extractor.readers.docx.read_docx",
            return_value="",
        ):
            read_legacy_office(path, verbose=False)

        run_spy.assert_called_once()
        cmd = run_spy.call_args[0][0]
        assert cmd[0] == "soffice"
        assert "--headless" in cmd
        assert "--convert-to" in cmd
        assert "docx" in cmd
        assert "--outdir" in cmd
        assert str(path) in cmd

    def test_tempdir_is_cleaned_up(self, tmp_workdir):
        """The temporary directory used for conversion must be cleaned up."""
        path = tmp_workdir / "doc.doc"
        path.write_bytes(b"fake doc")

        created_dirs = []

        import tempfile as tf

        original_mkdtemp = tf.TemporaryDirectory

        def tracking_mkdtemp(*args, **kwargs):
            d = original_mkdtemp(*args, **kwargs)
            created_dirs.append(d.name)
            return d

        with mock.patch(
            "ocr_extractor.readers.legacy.subprocess.run",
            side_effect=_fake_convert_run,
        ), mock.patch(
            "ocr_extractor.readers.docx.read_docx",
            return_value="",
        ), mock.patch(
            "ocr_extractor.readers.legacy.tempfile.TemporaryDirectory",
            side_effect=tracking_mkdtemp,
        ):
            read_legacy_office(path, verbose=False)

        assert len(created_dirs) == 1
        # The temp dir must have been cleaned up.
        from pathlib import Path
        assert not Path(created_dirs[0]).exists()


# ---------- helper ---------------------------------------------------------


def _fake_convert_run_and_create(*args, **kwargs):
    """Deprecated alias for :func:`_fake_convert_run` (kept for backward
    compatibility with older tests; new tests should use the primary
    helper).
    """
    return _fake_convert_run(*args, **kwargs)