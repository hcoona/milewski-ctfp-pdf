import unittest
from pathlib import Path

from ctfp_latex_parser.renderers.asciidoc import AsciiDocRenderer
from ctfp_latex_parser.nodes import Document, Environment, Math
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
        expected_lines = [
            "[latexmath]",
            "++++",
            "\\begin{align*}",
            "  F & = m \\frac{dv}{dt} \\\\",
            "  v & = \\frac{dx}{dt}",
            "\\end{align*}",
            "++++",
            "",
        ]
        self.assertEqual(expected_lines, rendered.splitlines())

    def test_align_environment_keeps_macro_expansion(self) -> None:
        source = "\\begin{align} \\cat{C} &\\to \\cat{D} \\end{align}\n"
        environment = self._first_environment(parse_text(source))
        rendered = self.renderer._render_environment(environment)
        self.assertEqual(
            (
                "[latexmath]\n"
                "++++\n"
                "\\begin{align} \\mathbf{C} &\\to \\mathbf{D} \\end{align}\n"
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
                "[source]\n"
                "----\n"
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
        expected_lines = [
            "[latexmath]",
            "++++",
            "\\begin{gather*}",
            "  R \\circ L \\to I_{\\mathbf{D}} \\quad\\quad\\text{not necessarily} \\\\",
            "  I_{\\mathbf{C}} \\to L \\circ R \\quad\\quad\\text{not necessarily}",
            "\\end{gather*}",
            "++++",
            "",
        ]
        self.assertEqual(expected_lines, rendered.splitlines())

    def test_gather_environment_in_list_preserves_spacing(self) -> None:
        source = (
            "\\begin{enumerate}\n"
            "  \\tightlist\n"
            "  \\item\n"
            "        Derive the naturality square for $\\psi$, the transformation\n"
            "        between the two (contravariant) functors:\n"
            "        \\begin{gather*}\n"
            "          a \\to \\cat{C}(L a, b) \\\\\n"
            "          a \\to \\cat{D}(a, R b)\n"
            "        \\end{gather*}\n"
            "  \\item\n"
            "        Derive the counit $\\varepsilon$ starting from the hom-sets isomorphism in\n"
            "        the second definition of the adjunction.\n"
            "\\end{enumerate}\n"
        )
        document_nodes = parse_text(source)
        document = Document(path=Path("dummy.tex"), children=document_nodes)
        rendered = self.renderer.render_document(document)
        expected_lines = [
            ". Derive the naturality square for latexmath:[\\psi], the transformation",
            "between the two (contravariant) functors:",
            "+",
            "[latexmath]",
            "++++",
            "\\begin{gather*}",
            "  a \\to \\mathbf{C}(L a, b) \\\\",
            "  a \\to \\mathbf{D}(a, R b)",
            "\\end{gather*}",
            "++++",
            ". Derive the counit latexmath:[\\varepsilon] starting from the hom-sets isomorphism in",
            "the second definition of the adjunction.",
        ]
        self.assertEqual(expected_lines, rendered.splitlines())

    @staticmethod
    def _first_environment(nodes: list) -> Environment:
        for node in nodes:
            if isinstance(node, Environment):
                return node
        raise AssertionError("No environment node found")


if __name__ == "__main__":
    unittest.main()
