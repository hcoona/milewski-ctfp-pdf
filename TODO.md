# TODO

## Converting LaTeX to Asciidoc

[X] 3.2, 3.9, 3.12, 3.14 failed to render tikzcd diagrams correctly.
[ ] Handle \newterm correctly to help Asciidoctor build index.
[ ] Convert mathlatex to prebuilt images for epub generation.

## Future

1. Use tree-sitter-latex as frontend. I compared it with plasTeX and found tree-sitter-latex is better.
2. Use nanopass-framework to convert LaTeX AST to Asciidoc AST.

### Comparison between tree-sitter-latex and plasTeX

**Methodology**: Evaluated parse tree quality using 4 objective criteria on 4 test files (preface.tex, category-the-essence-of-composition.tex, types-and-functions.tex, categories-great-and-small.tex):

1. **Information Density**: Ratio of meaningful nodes to total nodes (higher is better)
2. **Structural Clarity**: Average depth, max depth, depth standard deviation (ideal: 3-8 layers)
3. **Node Distribution**: Leaf/branch node ratio (ideal: 60-80% leaves)
4. **Text Content Efficiency**: Characters per node (measures information carrying capacity)

**Results** (Overall Score: V2 17 vs V3 7):

| Metric | tree-sitter-latex (V2) | plasTeX (V3) | Winner |
|--------|------------------------|--------------|--------|
| Information Density | 81.1% | 32.0% | **V2** |
| Structural Clarity | 3.4 layers avg | 2.4 layers avg | **V2** |
| Node Type Diversity | 48 types | 30 types | **V2** |
| Text Efficiency | 3.5 chars/node | 11.7 chars/node | **V3** |

**Key Findings**:
- V2 maintains high information density (73-86%) consistently across all files
- V3 suffers from character-level expansion: 99.5% nodes are `#text` in simple text files (preface.tex: 8,358 nodes vs V2's 1,805)
- V2 provides richer node types and clearer hierarchical structure, making it ideal for code analysis
- V3 excels at text content efficiency in complex documents but produces excessive noise nodes

**Conclusion**: tree-sitter-latex (V2) is significantly better for code analysis, structure extraction, and syntax checking due to higher information density, clearer structure, and richer node types. plasTeX (V3) is better suited for document conversion (LaTeX→HTML) where semantic understanding and character-level precision are required.

### Nanopass Conversion

Basically we need to do 2 kinds of conversion:

1. Backend-agnostic conversion, e.g. marcro expansion, parse tree to AST, etc.
2. Backend-specific conversion, e.g. AST to Asciidoc.

In each step, we can make it by introducing a new pass for transformation. We execute multiple passes to gradually transform the input to the desired output. It's easy to verify and test each pass and easy to add/remove passes.
