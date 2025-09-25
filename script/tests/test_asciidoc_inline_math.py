import unittest

from ctfp_latex_parser.renderers.asciidoc import AsciiDocRenderer
from ctfp_latex_parser.nodes import Math


class AsciiDocInlineMathTests(unittest.TestCase):
    def setUp(self) -> None:
        self.renderer = AsciiDocRenderer()

    def _render_inline(self, content: str) -> str:
        node = Math(kind="inline", delimiter="$", content=content)
        return self.renderer._render_math(node)

    def test_square_brackets_converted(self) -> None:
        result = self._render_inline(r"\cat{{[}C, D{]}}")
        self.assertEqual(
            r"latexmath:[\mathbf{\lbrack C, D\rbrack}]",
            result,
        )

    def test_optional_argument_preserved(self) -> None:
        result = self._render_inline(r"\foo[bar]")
        self.assertEqual(r"latexmath:[\foo[bar]]", result)

    def test_function_application_brackets_escaped(self) -> None:
        result = self._render_inline(r"f[x]")
        self.assertEqual(r"latexmath:[f\lbrack x\rbrack]", result)

    def test_left_right_brackets_escaped(self) -> None:
        result = self._render_inline(r"\left[ x \right]")
        self.assertEqual(r"latexmath:[\left\lbrack x \right\rbrack]", result)


if __name__ == "__main__":
    unittest.main()
