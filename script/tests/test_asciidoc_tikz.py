import unittest

from ctfp_latex_parser.nodes import Environment
from ctfp_latex_parser.parser import parse_text
from ctfp_latex_parser.renderers.asciidoc import AsciiDocRenderer


class AsciiDocTikzTests(unittest.TestCase):
    def setUp(self) -> None:
        self.renderer = AsciiDocRenderer()

    def test_single_tikz_figure(self) -> None:
        source = (
            "\\begin{figure}[H]\n"
            "  \\centering\n"
            "  \\begin{tikzcd}[column sep=large]\n"
            "    (\\cat{C}(c,d) \\otimes \\cat{C}(b,c)) \\otimes \\cat{C}(a,b)\n"
            "    \\arrow[r, \"\\circ\\otimes\\id\"]\n"
            "    \\arrow[dd, \"\\alpha\"]\n"
            "    & \\cat{C}(b,d) \\otimes \\cat{C}(a,b)\n"
            "    \\arrow[dr, \"\\circ\"] \\\n"
            "    & & \\cat{C}(a,d) \\\n"
            "    \\cat{C}(c,d) \\otimes (\\cat{C}(b,c) \\otimes \\cat{C}(a,b))\n"
            "    \\arrow[r, \"\\id\\otimes\\circ\"]\n"
            "    & \\cat{C}(c,d) \\otimes \\cat{C}(a,c)\n"
            "    \\arrow[ur, \"\\circ\"]\n"
            "  \\end{tikzcd}\n"
            "\\end{figure}\n"
        )
        environment = self._first_figure(parse_text(source))
        rendered = self.renderer._render_environment(environment)
        expected = (
            "[tikz,preamble=true]\n"
            "----\n"
            "\\usetikzlibrary{cd}\n"
            "~~~~\n"
            "\\begin{tikzcd}[column sep=large]\n"
            "  (\\cat{C}(c,d) \\otimes \\cat{C}(b,c)) \\otimes \\cat{C}(a,b)\n"
            "  \\arrow[r, \"\\circ\\otimes\\id\"]\n"
            "  \\arrow[dd, \"\\alpha\"]\n"
            "  & \\cat{C}(b,d) \\otimes \\cat{C}(a,b)\n"
            "  \\arrow[dr, \"\\circ\"] \\\n"
            "  & & \\cat{C}(a,d) \\\n"
            "  \\cat{C}(c,d) \\otimes (\\cat{C}(b,c) \\otimes \\cat{C}(a,b))\n"
            "  \\arrow[r, \"\\id\\otimes\\circ\"]\n"
            "  & \\cat{C}(c,d) \\otimes \\cat{C}(a,c)\n"
            "  \\arrow[ur, \"\\circ\"]\n"
            "\\end{tikzcd}\n"
            "----\n"
        )
        self.assertEqual(expected, rendered)

    def test_tikz_with_multiple_subfigures(self) -> None:
        source = (
            "\\begin{figure}[H]\n"
            "  \\centering\n\n"
            "  \\begin{subfigure}\n"
            "    \\centering\n"
            "    \\begin{tikzcd}[column sep=large, row sep=large]\n"
            "      L \\arrow[rd, equal] \\arrow[r, \"L \\circ \\eta\"]\n"
            "      & L \\circ R \\circ L \\arrow[d, \"\\varepsilon \\circ L\"] \\\n"
            "      & L\n"
            "    \\end{tikzcd}\n"
            "  \\end{subfigure}%\n"
            "  \\hspace{1cm}\n"
            "  \\begin{subfigure}\n"
            "    \\centering\n"
            "    \\begin{tikzcd}[column sep=large, row sep=large]\n"
            "      R \\arrow[rd, equal] \\arrow[r, \"\\eta \\circ R\"]\n"
            "      & R \\circ L \\circ R \\arrow[d, \"R \\circ \\varepsilon\"] \\\n"
            "      & R\n"
            "    \\end{tikzcd}\n"
            "  \\end{subfigure}\n"
            "\\end{figure}\n"
        )
        environment = self._first_figure(parse_text(source))
        rendered = self.renderer._render_environment(environment)
        expected = (
            "[cols=\"^.^,^.^\",frame=\"none\",grid=\"none\"]\n"
            "|===\n"
            "a|\n"
            "[tikz,preamble=true]\n"
            "----\n"
            "\\usetikzlibrary{cd}\n"
            "~~~~\n"
            "\\begin{tikzcd}[column sep=large, row sep=large]\n"
            "  L \\arrow[rd, equal] \\arrow[r, \"L \\circ \\eta\"]\n"
            "  & L \\circ R \\circ L \\arrow[d, \"\\varepsilon \\circ L\"] \\\n"
            "  & L\n"
            "\\end{tikzcd}\n"
            "----\n"
            "a|\n"
            "[tikz,preamble=true]\n"
            "----\n"
            "\\usetikzlibrary{cd}\n"
            "~~~~\n"
            "\\begin{tikzcd}[column sep=large, row sep=large]\n"
            "  R \\arrow[rd, equal] \\arrow[r, \"\\eta \\circ R\"]\n"
            "  & R \\circ L \\circ R \\arrow[d, \"R \\circ \\varepsilon\"] \\\n"
            "  & R\n"
            "\\end{tikzcd}\n"
            "----\n"
            "|===\n"
        )
        self.assertEqual(expected, rendered)

    @staticmethod
    def _first_figure(nodes: list) -> Environment:
        for node in nodes:
            if isinstance(node, Environment) and node.name == "figure":
                return node
        raise AssertionError("No figure environment found")


if __name__ == "__main__":
    unittest.main()
