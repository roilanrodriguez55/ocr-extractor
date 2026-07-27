"""Tests for the core helpers: clean_line, clean_text, preprocess_image."""

import numpy as np
import pytest
from PIL import Image

from ocr_extractor.core import clean_line, clean_text, preprocess_image


class TestCleanLine:
    def test_short_line_is_dropped(self):
        assert clean_line("") is None
        assert clean_line("a") is None
        assert clean_line("  ") is None

    def test_keeps_normal_line(self):
        assert clean_line("Hello world") == "Hello world"

    def test_strips_whitespace(self):
        assert clean_line("  Hello world  ") == "Hello world"

    def test_replaces_disallowed_with_space(self):
        # The comma is NOT in the allowed set (current behavior, see README).
        result = clean_line("hello,world")
        assert "," not in result
        # Each disallowed char becomes a space; consecutive whitespace is collapsed.
        assert "hello world" == result

    def test_collapses_internal_whitespace(self):
        assert clean_line("hello    world") == "hello world"

    def test_symbol_only_line_is_dropped(self):
        # Lines containing only characters outside the allowed set are
        # reduced to whitespace and then dropped by the length check.
        assert clean_line("()") is None
        assert clean_line("[]{}") is None
        assert clean_line("=+*#@^,:;</\\|~") is None
        # Lines containing only characters that ARE in the allowed
        # punctuation set but also in the symbol-only regex are dropped
        # by the regex check.
        assert clean_line("--") is None
        assert clean_line("..") is None

    def test_punctuation_in_allowed_set(self):
        # Single punctuation characters that ARE allowed: ' - . ! ?
        assert clean_line("don't") == "don't"
        assert clean_line("well-known") == "well-known"
        assert clean_line("Hello!") == "Hello!"
        assert clean_line("Really?") == "Really?"

    def test_cleaned_short_line_is_dropped(self):
        # After replacement, only one letter remains → dropped.
        assert clean_line("a $$$") is None

    def test_preserves_numbers(self):
        assert clean_line("Page 42") == "Page 42"

    def test_preserves_mixed_case(self):
        assert clean_line("UPPERCASE lowercase") == "UPPERCASE lowercase"


class TestCleanText:
    def test_filters_per_line(self):
        text = "Hello world\n\nI\n\n(){}[]\nGoodbye"
        result = clean_text(text)
        # Lines with real content survive.
        assert "Hello world" in result
        assert "Goodbye" in result
        # Single-character lines are dropped (< 2 chars after strip).
        assert "\nI\n" not in result
        # Symbol-only lines are dropped.
        assert "(){}[]" not in result

    def test_empty_input(self):
        assert clean_text("") == ""

    def test_joins_with_newlines(self):
        text = "first line\nsecond line"
        result = clean_text(text)
        assert "\n" in result


class TestPreprocessImage:
    def test_pil_image_returns_grayscale_ndarray(self, tmp_workdir):
        img = Image.new("RGB", (200, 100), color=(255, 255, 255))
        out = preprocess_image(img)
        assert isinstance(out, np.ndarray)
        # Grayscale: single channel.
        assert out.ndim == 2
        assert out.shape == (100, 200)
        # White input stays white (denoising doesn't change it).
        assert out[0, 0] == 255