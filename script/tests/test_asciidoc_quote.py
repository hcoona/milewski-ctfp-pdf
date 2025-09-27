import unittest
from pathlib import Path

from ctfp_latex_parser.parser import parse_text
from ctfp_latex_parser.nodes import Document
from ctfp_latex_parser.renderers.asciidoc import AsciiDocRenderer


class AsciiDocQuoteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.renderer = AsciiDocRenderer()

    def test_quote_environment_converted_to_block(self) -> None:
        source = (
            "The exponential $b^a$, or the function object $a \\Rightarrow b$, can be\n"
            "defined using a \\hyperref[function-types]{universal\n"
            "  construction}. This construction, if it exists for all pairs of objects,\n"
            "can be seen as an adjunction. Again, the trick is to concentrate on the\n"
            "statement:\n\n"
            "\\begin{quote}\n"
            "  For any other object $z$ with a morphism $g \\Colon z\\times{}a \\to b$\n"
            "  there is a unique morphism $h \\Colon z \\to (a \\Rightarrow b)$\n"
            "\\end{quote}\n"
            "This statement establishes a mapping between hom-sets.\n"
        )
        document = Document(path=Path("sample.tex"), children=parse_text(source))
        rendered = self.renderer.render_document(document)
        expected = (
            "The exponential latexmath:[b^a], or the function object latexmath:[a \\Rightarrow b], can be\n"
            "defined using a function-typesuniversal\n"
            "  construction. This construction, if it exists for all pairs of objects,\n"
            "can be seen as an adjunction. Again, the trick is to concentrate on the\n"
            "statement:\n\n"
            "[quote]\n"
            "____\n"
            "For any other object latexmath:[z] with a morphism latexmath:[g ∷ z\\times{}a \\to b]\n"
            "there is a unique morphism latexmath:[h ∷ z \\to (a \\Rightarrow b)]\n"
            "____\n\n\n"
            "This statement establishes a mapping between hom-sets.\n"
        )
        self.assertEqual(expected, rendered)


if __name__ == "__main__":
    unittest.main()
