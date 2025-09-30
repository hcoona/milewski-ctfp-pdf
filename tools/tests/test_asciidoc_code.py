"""Tests for AsciiDoc code rendering."""

import pytest

from ctfp_latex_parser import parse_text, Document
from ctfp_latex_parser.renderers.asciidoc import render_asciidoc_document
from pathlib import Path


def render_latex(latex: str) -> str:
    """Helper to render LaTeX to AsciiDoc."""
    nodes = parse_text(latex)
    document = Document(path=Path("test.tex"), children=nodes)
    return render_asciidoc_document(document)


def test_code_with_underscore():
    """Test that underscores in code are wrapped in pass:[] macro."""
    latex = r"\code{my_variable}"
    result = render_latex(latex)
    assert "`mypass:[_]variable`" in result


def test_code_with_ampersand():
    """Test that ampersands in code are wrapped in pass:[] macro."""
    latex = r"\code{foo & bar}"
    result = render_latex(latex)
    assert "`foo pass:[&] bar`" in result


def test_texttt_with_underscore():
    """Test that underscores in texttt are wrapped in pass:[] macro."""
    latex = r"\texttt{some_function}"
    result = render_latex(latex)
    assert "`somepass:[_]function`" in result


def test_code_with_both_underscore_and_ampersand():
    """Test code with both underscore and ampersand."""
    latex = r"\code{type_a & type_b}"
    result = render_latex(latex)
    assert "`typepass:[_]a pass:[&] typepass:[_]b`" in result


def test_code_with_multiple_underscores():
    """Test code with multiple underscores."""
    latex = r"\code{my_long_variable_name}"
    result = render_latex(latex)
    assert "`mypass:[_]longpass:[_]variablepass:[_]name`" in result


def test_code_with_pattern():
    """Test code with _|_ pattern."""
    latex = r"\code{_|_}"
    result = render_latex(latex)
    assert "`pass:[_]|pass:[_]`" in result
