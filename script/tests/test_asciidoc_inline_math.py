import unittest

from ctfp_latex_parser.renderers.asciidoc import AsciiDocRenderer
from ctfp_latex_parser.nodes import Environment, Math
from ctfp_latex_parser.parser import parse_text


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

    def test_align_environment_preserves_latex(self) -> None:
        source = (
            "\\begin{align*}\n"
            "  F & = m \\frac{dv}{dt} \\\\n"
            "  v & = \\frac{dx}{dt}\n"
            "\\end{align*}\n"
        )
        environment = self._first_environment(parse_text(source))
        rendered = self.renderer._render_environment(environment)
        self.assertEqual(
            (
                "[latexmath]\n++++\n"
                "\\begin{align*}\n"
                "F & = m \\frac{dv}{dt} \\\\n"
                "  v & = \\frac{dx}{dt}\n"
                "\\end{align*}\n\n"
                "++++\n\n"
            ),
            rendered,
        )

    def test_align_environment_keeps_macro_expansion(self) -> None:
        source = "\\begin{align} \\cat{C} &\\to \\cat{D} \\end{align}\n"
        environment = self._first_environment(parse_text(source))
        rendered = self.renderer._render_environment(environment)
        self.assertEqual(
            (
                "[latexmath]\n++++\n"
                "\\begin{align}\n"
                "\\mathbf{C} &\\to \\mathbf{D} \n"
                "\\end{align}\n\n"
                "++++\n\n"
            ),
            rendered,
        )

    def test_snipv_ensuremath_cong(self) -> None:
        source = (
            "\\begin{snipv}\n"
            "forall x. (a -> x) -> (b -> x) \\ensuremath{\\cong} b -> a\n"
            "\\end{snipv}\n"
        )
        environment = self._first_environment(parse_text(source))
        rendered = self.renderer._render_environment(environment)
        self.assertEqual(
            (
                "[source]\n----\n"
                "forall x. (a -> x) -> (b -> x) ≅ b -> a\n"
                "----\n\n"
            ),
            rendered,
        )

    def test_gather_environment_preserves_structure(self) -> None:
        source = (
            "\\begin{gather*}\n"
            "  R \\circ L \\to I_{\\cat{D}} \\quad\\quad\\text{not necessarily} \\\\\n"
            "  I_{\\cat{C}} \\to L \\circ R \\quad\\quad\\text{not necessarily}\n"
            "\\end{gather*}\n"
        )
        environment = self._first_environment(parse_text(source))
        rendered = self.renderer._render_environment(environment)
        self.assertEqual(
            (
                "[latexmath]\n++++\n"
                "\\begin{gather*}\n"
                "R \\circ L \\to I_{\\mathbf{D}} \\quad\\quad\\text{not necessarily} \\\\\n"
                "  I_{\\mathbf{C}} \\to L \\circ R \\quad\\quad\\text{not necessarily}\n"
                "\\end{gather*}\n\n"
                "++++\n\n"
            ),
            rendered,
        )

    @staticmethod
    def _first_environment(nodes: list) -> Environment:
        for node in nodes:
            if isinstance(node, Environment):
                return node
        raise AssertionError("No environment node found")


if __name__ == "__main__":
    unittest.main()
