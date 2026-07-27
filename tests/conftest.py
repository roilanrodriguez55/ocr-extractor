"""Shared pytest fixtures for the ocr-extractor test suite."""

import sys
from pathlib import Path

import pytest

# Make the project root importable so tests can `import ocr_extractor`
# regardless of where pytest is invoked from.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def tmp_workdir(tmp_path):
    """A temporary working directory the test can write files into."""
    return tmp_path