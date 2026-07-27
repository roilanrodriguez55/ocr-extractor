"""DOCX reader — extract text directly from Word 2007+ files.

Unlike PDF/image inputs, DOCX text is already structured and clean. We
therefore skip the OCR pipeline and apply only a light cleanup
(collapse whitespace, drop empty paragraphs). Tables are extracted in
document order alongside paragraphs.
"""

import re

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph


def _light_clean(text):
    """Collapse internal whitespace and strip the edges."""
    return re.sub(r"\s+", " ", text).strip()


def _format_row(row):
    """Format a table row as ``" | col1 | col2 | col3"``.

    Leading and trailing pipes (which result from empty edge cells) are
    stripped so an entirely-empty row reduces to ``""`` and can be
    dropped by the caller.
    """
    cells = [_light_clean(cell.text) for cell in row.cells]
    line = " | " + " | ".join(cells)
    return line.strip(" |")


def _iter_block_items(parent):
    """Yield paragraphs and tables in document order.

    Adapted from the python-docx recipe for preserving order between
    blocks of different types.
    """
    parent_elm = parent.element.body
    for child in parent_elm.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, parent)
        elif child.tag == qn("w:tbl"):
            yield Table(child, parent)


def read_docx(path, *, dpi=300, lang="eng", verbose=True):
    """Extract text from a ``.docx`` file.

    Walks the document body in order, emitting one line per non-empty
    paragraph and one line per table row (cells joined with `` | ``).
    No page markers are emitted because Word documents are paginated
    dynamically at render time.

    Parameters
    ----------
    path : str or pathlib.Path
        Path to the ``.docx`` file.
    dpi : int, optional
        Unused; kept for signature uniformity. Defaults to ``300``.
    lang : str, optional
        Unused; kept for signature uniformity. Defaults to ``"eng"``.
    verbose : bool, optional
        If ``True``, print a single progress line. Defaults to
        ``True``.

    Returns
    -------
    str
        Extracted text, one paragraph or row per line.
    """
    if verbose:
        print(f"Reading {path}...")

    doc = Document(path)
    lines = []

    for block in _iter_block_items(doc):
        if isinstance(block, Paragraph):
            text = _light_clean(block.text)
            if text:
                lines.append(text)
        elif isinstance(block, Table):
            for row in block.rows:
                row_text = _format_row(row)
                # Drop rows that are entirely empty.
                if row_text:
                    lines.append(row_text)

    return "\n".join(lines)


__all__ = ["read_docx"]