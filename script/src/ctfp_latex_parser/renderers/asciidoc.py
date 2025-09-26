from __future__ import annotations

import re
import textwrap

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from ..nodes import (
    Argument,
    Command,
    Comment,
    Document,
    Environment,
    Group,
    Math,
    Node,
    Text,
)


@dataclass
class _ListItem:
    nodes: list[Node]


class AsciiDocRenderer:
    _BLOCK_DELIMITERS = {"----", "++++", "....", "____", "****"}
    _DOUBLE_QUOTE_PATTERN = re.compile(r"``([^`]*?)''")
    _CODE_SPAN_PATTERN = re.compile(r"(``?)([^`]*?)(\1)")
    _LATEXMATH_SPAN_PATTERN = re.compile(r"(latexmath:\[)(.*?)(?<!\\)(\])", re.DOTALL)
    _INLINE_BRACKET_ESCAPING_COMMANDS: frozenset[str] = frozenset(
        {
            "left",
            "right",
            "middle",
            "big",
            "Big",
            "bigg",
            "Bigg",
            "bigl",
            "Bigl",
            "bigr",
            "Bigr",
            "biggl",
            "Biggl",
            "biggr",
            "Biggr",
        }
    )
    _INLINE_LBRACK_LETTER_PATTERN = re.compile(r"\\lbrack(?=[A-Za-z])")
    _MATH_BLOCK_ENVIRONMENTS: frozenset[str] = frozenset(
        {
            "align",
            "align*",
            "equation",
            "equation*",
            "gather",
            "gather*",
        }
    )
    _TIKZ_ENVIRONMENTS: frozenset[str] = frozenset({"tikzcd", "tikzpicture"})
    _ENSUREMATH_INLINE_REPLACEMENTS: dict[str, str] = {
        r"\cong": "≅",
        r"\Colon": "∷",
    }
    _SNIPPET_LANGUAGES: tuple[tuple[str, str], ...] = (
        ("haskell", "hs"),
        ("ocaml", "ml"),
        ("reason", "re"),
        ("scala", "scala"),
    )
    _MATH_SIMPLE_MACROS: dict[str, str] = {
        "Set": r"\cat{Set}",
        "Rel": r"\cat{Rel}",
        "Cat": r"\cat{Cat}",
        "id": r"\mathbf{id}",
        "Ran": r"\mathbf{Ran}",
        "Lan": r"\mathbf{Lan}",
        "Hask": r"\mathbf{Hask}",
        "Fop": r"\cat{F}^{\mathit{op}}",
    }
    _MATH_SIMPLE_MACRO_PATTERNS: dict[str, re.Pattern[str]] = {
        name: re.compile(rf"\\{name}(?=\b|[^a-zA-Z])")
        for name in _MATH_SIMPLE_MACROS
    }
    _RE_CAT = re.compile(r"\\cat\s*\{([^{}]*)\}")
    _RE_IDARROW = re.compile(r"\\idarrow(?:\[(.*?)\])?")
    _RE_LIM = re.compile(r"\\Lim(?:\[(.*?)\])?")
    _RE_FOP = re.compile(r"\\Fop\b")
    _FIGURE_ALLOWED_TIKZ_COMMANDS: frozenset[str] = frozenset(
        {"centering", "label", "hfill", "hspace", "vspace"}
    )
    _FIGURE_ALLOWED_TIKZ_ENVIRONMENTS: frozenset[str] = frozenset({"center"})

    def __init__(self, *, expand_snippet_languages: Sequence[str] | None = None) -> None:
        self._current_document: Document | None = None
        allowed_languages = {language for language, _ in self._SNIPPET_LANGUAGES}
        self._expand_snippet_languages: set[str] = {"haskell"}
        self._list_depth = 0
        self._math_block_depth = 0
        if expand_snippet_languages:
            for raw_language in expand_snippet_languages:
                language = raw_language.strip().lower()
                if language in allowed_languages:
                    self._expand_snippet_languages.add(language)

    def render_document(self, document: Document) -> str:
        self._current_document = document
        body = self._render_nodes(document.children).strip()
        if not body:
            return "\n"
        return f"{body}\n"

    def render_documents(self, documents: Sequence[Document]) -> str:
        rendered = [self.render_document(document).rstrip() for document in documents]
        if not rendered:
            return ""
        return "\n\n////\n\n".join(rendered) + "\n"

    def _render_nodes(self, nodes: Sequence[Node], *, inline: bool = False) -> str:
        node_list = list(nodes)
        chunks: list[str] = []
        for index, node in enumerate(node_list):
            rendered = self._render_node(node, inline=inline)
            if isinstance(node, Command) and node.name in {"texttt", "code"}:
                if self._should_use_double_backticks(node_list, index):
                    rendered = self._ensure_double_backticks(rendered)
            chunks.append(rendered)
        return "".join(chunks)

    def _should_use_double_backticks(self, nodes: Sequence[Node], index: int) -> bool:
        if index + 1 >= len(nodes):
            return False
        next_node = nodes[index + 1]
        if isinstance(next_node, Text):
            content = next_node.content
            if not content:
                return False
            ch = content[0]
            if ch.isspace():
                return False
            if ch == "'":
                return len(content) > 1 and content[1].isalnum()
            return ch.isalnum()
        return False

    def _ensure_double_backticks(self, rendered: str) -> str:
        if rendered.startswith("``") and rendered.endswith("``"):
            return rendered
        if rendered.startswith("`") and rendered.endswith("`"):
            return f"``{rendered[1:-1]}``"
        return rendered

    def _escape_text(self, text: str) -> str:
        text = self._DOUBLE_QUOTE_PATTERN.sub(lambda match: f'"{match.group(1)}"', text)
        text = text.replace("``", '"').replace("''", '"')
        text = text.replace("C++", "{cpp}")
        text = text.replace("---", "--")
        return text.replace(r"\#", "#")

    def _escape_table_cell_code_pipes(self, cell: str) -> str:
        def escape_code(match: re.Match[str]) -> str:
            opening, content, closing = match.groups()
            escaped = re.sub(r"(?<!\\)\|", r"\\|", content)
            return f"{opening}{escaped}{closing}"

        def escape_math(match: re.Match[str]) -> str:
            opening, content, closing = match.groups()
            escaped = re.sub(r"(?<!\\)\|", r"\\|", content)
            return f"{opening}{escaped}{closing}"

        cell = self._CODE_SPAN_PATTERN.sub(escape_code, cell)
        cell = self._LATEXMATH_SPAN_PATTERN.sub(escape_math, cell)
        return cell

    def _render_node(self, node: Node, *, inline: bool) -> str:
        if isinstance(node, Text):
            return self._escape_text(node.content)
        if isinstance(node, Comment):
            return ""
        if isinstance(node, Group):
            return self._render_nodes(node.children, inline=inline)
        if isinstance(node, Command):
            return self._render_command(node, inline=inline)
        if isinstance(node, Environment):
            return self._render_environment(node)
        if isinstance(node, Math):
            return self._render_math(node)
        return ""

    def _render_command(self, command: Command, *, inline: bool) -> str:
        name = command.name
        if name == "\\":
            if self._math_block_depth > 0:
                return "\\\\\n"
            return "\n"
        if name == "#":
            return "#"
        if name == "par":
            return "\n\n"
        if name == "&":
            return "&"
        if name in {"_", "textunderscore"}:
            return "_"
        if name in {"textbf", "newterm"}:
            text = self._argument(command, 0, kind="required")
            return f"*{text}*"
        if name in {"emph", "textit"}:
            text = self._argument(command, 0, kind="required")
            return f"_{text}_"
        if name in {"texttt", "code"}:
            text = self._argument(command, 0, kind="required")
            return f"`{text}`"
        if name == "section":
            title = self._argument(command, 0, kind="required")
            return f"\n\n== {title}\n\n"
        if name == "subsection":
            title = self._argument(command, 0, kind="required")
            return f"\n\n=== {title}\n\n"
        if name == "subsubsection":
            title = self._argument(command, 0, kind="required")
            return f"\n\n==== {title}\n\n"
        if name == "paragraph":
            title = self._argument(command, 0, kind="required")
            return f"\n\n===== {title}\n\n"
        if name == "footnote":
            text = self._argument(command, 0, kind="required")
            return f"footnote:[{text}]"
        if name in {"href", "urlref"}:
            url = self._argument(command, 0, kind="required")
            label = self._argument(command, 1, kind="required") or url
            return f"link:{url}[{label}]"
        if name == "url":
            url = self._argument(command, 0, kind="required")
            return f"link:{url}[{url}]"
        if name == "label":
            label = self._argument(command, 0, kind="required")
            return f"[[{label}]]\n"
        if name == "ref":
            label = self._argument(command, 0, kind="required")
            return f"<<{label}>>"
        if name == "src":
            target = self._argument(command, 0, kind="required")
            suffix = self._argument(command, 0, kind="optional")
            if not target:
                return ""
            snippet = self._render_snippet_includes(target, suffix)
            if snippet is not None:
                return snippet
            return f"xref:{target}[]"
        if name == "ensuremath":
            expr = self._argument(command, 0, kind="required")
            if inline:
                replacement = self._ENSUREMATH_INLINE_REPLACEMENTS.get(expr)
                if replacement is not None:
                    return replacement
            return f"latexmath:[{self._expand_math_macros(expr)}]"
        if name == "ldots":
            return "..."
        if name == "lettrine":
            lead = self._argument(command, 0, kind="required", strip=False)
            rest = self._argument(command, 1, kind="required", strip=False)
            if not rest:
                return lead
            if rest[0].isspace():
                return f"{lead}{rest}"
            rest_lower = rest.lstrip().lower()
            if lead == "A" and rest_lower.startswith("t "):
                return f"{lead}{rest}"
            if lead == "I" and rest_lower.startswith(("n", "f", "t")):
                return f"{lead}{rest}"
            return f"{lead} {rest}"
        if name == "centering":
            return ""
        if name == "hfill":
            return ""
        if name == "noindent":
            return ""
        if name in {"raggedright", "strut"}:
            return ""
        if name == "includegraphics":
            if command.arguments:
                path_text = self._render_nodes(command.arguments[-1].children, inline=True).strip()
                if path_text:
                    base_dir = self._current_document.path.parent if self._current_document else Path()
                    resolved_image = self._resolve_resource_path(base_dir, path_text)
                    return f"image::{resolved_image}[]"
            return ""
        if name == "tightlist":
            return ""
        if command.arguments:
            return "".join(self._render_argument(command, arg) for arg in command.arguments)
        return f"\\{name}"

    def _render_environment(self, environment: Environment) -> str:
        name = environment.name
        if name in {"enumerate", "itemize"}:
            numbered = name == "enumerate"
            return self._render_list(environment.children, numbered=numbered)
        if name in {"snip", "snipv", "verbatim", "Verbatim", "minted"}:
            language = self._argument(environment, 0, kind="required")
            body = self._render_code_block(environment.children)
            header = f"[source,{language}]" if language else "[source]"
            return f"{header}\n----\n{body}\n----\n\n"
        if name == "figure":
            return self._render_figure(environment)
        if name == "longtable":
            return self._render_longtable(environment)
        if name in self._MATH_BLOCK_ENVIRONMENTS:
            return self._render_math_environment(environment)
        return self._render_nodes(environment.children)

    def _render_code_block(self, nodes: Sequence[Node]) -> str:
        return self._render_code_nodes(nodes).rstrip("\n")

    def _render_code_nodes(self, nodes: Sequence[Node]) -> str:
        parts: list[str] = []
        for node in nodes:
            if isinstance(node, Text):
                parts.append(node.content)
            elif isinstance(node, Group):
                parts.append("{" + self._render_code_nodes(node.children) + "}")
            elif isinstance(node, Command):
                if node.name == "\\":
                    parts.append("\n")
                else:
                    parts.append(self._render_command(node, inline=True))
            elif isinstance(node, Environment):
                parts.append(self._render_code_nodes(node.children))
            elif isinstance(node, Math):
                parts.append(node.content)
        return "".join(parts)

    def _render_tikz_figure(self, environment: Environment) -> str:
        libraries: set[str] = set()
        self._nodes_contain_tikz(environment.children, libraries=libraries)
        sorted_libraries = sorted(libraries)
        table_rendered = self._render_tikz_subfigure_table(environment, sorted_libraries)
        if table_rendered is not None:
            return table_rendered
        single_block = self._extract_single_tikz_block(environment, sorted_libraries)
        if single_block is not None:
            return single_block + "\n"
        latex_source = self._render_environment_to_latex(environment).rstrip("\n") + "\n"
        block = self._format_tikz_block(latex_source, sorted_libraries)
        return block + "\n"

    def _format_tikz_block(
        self,
        latex_source: str,
        libraries: Sequence[str],
        caption: str | None = None,
    ) -> str:
        lines: list[str] = []
        if caption:
            lines.append(f".{self._normalize_caption(caption)}")
        lines.append("[tikz,preamble=true]")
        lines.append("----")
        for library in libraries:
            lines.append(f"\\usetikzlibrary{{{library}}}")
        lines.append("~~~~")
        expanded = self._expand_math_macros(latex_source)
        lines.append(self._normalize_tikz_latex(expanded))
        lines.append("----")
        return "\n".join(lines)

    def _normalize_tikz_latex(self, latex_source: str) -> str:
        stripped = latex_source.rstrip("\n")
        if not stripped:
            return stripped
        lines = stripped.split("\n")
        if len(lines) == 1:
            return lines[0].lstrip(" \t")
        closing_index = len(lines) - 1
        lines[closing_index] = lines[closing_index].lstrip(" \t")
        body_indices = range(1, closing_index)
        indent_levels: list[int] = []
        for index in body_indices:
            line = lines[index]
            if not line.strip():
                continue
            indent = len(line) - len(line.lstrip(" \t"))
            indent_levels.append(indent)
        excess_indent = 0
        if indent_levels:
            minimal_indent = min(indent_levels)
            if minimal_indent > 2:
                excess_indent = minimal_indent - 2
        if excess_indent > 0:
            for index in body_indices:
                line = lines[index]
                if not line:
                    continue
                removal = min(excess_indent, len(line) - len(line.lstrip(" \t")))
                if removal > 0:
                    lines[index] = line[removal:]
        return "\n".join(lines)

    def _render_tikz_subfigure_table(
        self,
        environment: Environment,
        libraries: Sequence[str],
    ) -> str | None:
        subfigure_blocks: list[str] = []
        caption: str | None = None
        for node in environment.children:
            if isinstance(node, Comment):
                continue
            if isinstance(node, Command):
                if node.name == "caption":
                    caption = self._argument(node, 0, kind="required")
                    continue
                if node.name in {"centering", "hspace"}:
                    continue
            if isinstance(node, Environment) and node.name == "subfigure":
                block = self._extract_tikz_subfigure_block(node, libraries)
                if block is None:
                    return None
                subfigure_blocks.append(block)
                continue
            if isinstance(node, Text) and not node.content.strip():
                continue
            return None
        if len(subfigure_blocks) < 2:
            return None
        cols_spec = ",".join(["^.^"] * len(subfigure_blocks))
        lines: list[str] = []
        if caption:
            lines.append(f".{self._normalize_caption(caption)}")
        lines.append(f'[cols="{cols_spec}",frame="none",grid="none"]')
        lines.append("|===")
        for block in subfigure_blocks:
            lines.append("a|")
            lines.append(block)
        lines.append("|===")
        lines.append("")
        return "\n".join(lines)

    def _extract_tikz_subfigure_block(
        self,
        subfigure: Environment,
        libraries: Sequence[str],
    ) -> str | None:
        caption: str | None = None
        tikz_env: Environment | None = None
        for node in subfigure.children:
            if isinstance(node, Comment):
                continue
            if isinstance(node, Text):
                if node.content.strip():
                    return None
                continue
            if isinstance(node, Command):
                if node.name == "caption":
                    caption = self._argument(node, 0, kind="required")
                    continue
                if node.name in {"centering", "label", "hfill", "hspace"}:
                    continue
            if isinstance(node, Environment) and node.name in self._TIKZ_ENVIRONMENTS:
                if tikz_env is not None:
                    return None
                tikz_env = node
                continue
            if isinstance(node, Environment):
                return None
            if isinstance(node, Command):
                return None
            return None
        if tikz_env is None:
            return None
        latex_source = self._render_environment_to_latex(tikz_env).rstrip("\n") + "\n"
        return self._format_tikz_block(latex_source, libraries, caption)

    def _extract_single_tikz_block(
        self,
        environment: Environment,
        libraries: Sequence[str],
    ) -> str | None:
        caption: str | None = None
        tikz_env: Environment | None = None

        def visit(nodes: Sequence[Node]) -> bool:
            nonlocal caption, tikz_env
            for node in nodes:
                if isinstance(node, Comment):
                    continue
                if isinstance(node, Text):
                    if node.content.strip():
                        return False
                    continue
                if isinstance(node, Command):
                    if node.name == "caption":
                        caption = self._argument(node, 0, kind="required")
                        continue
                    if node.name in self._FIGURE_ALLOWED_TIKZ_COMMANDS:
                        continue
                    return False
                if isinstance(node, Environment):
                    if node.name in self._TIKZ_ENVIRONMENTS:
                        if tikz_env is not None:
                            return False
                        tikz_env = node
                        continue
                    if node.name == "subfigure":
                        return False
                    if node.name in self._FIGURE_ALLOWED_TIKZ_ENVIRONMENTS:
                        if not visit(node.children):
                            return False
                        continue
                    return False
                else:
                    return False
            return True

        if not visit(environment.children):
            return None
        if tikz_env is None:
            return None
        latex_source = self._render_environment_to_latex(tikz_env).rstrip("\n") + "\n"
        return self._format_tikz_block(latex_source, libraries, caption)

    def _figure_contains_tikz(self, environment: Environment) -> bool:
        return self._nodes_contain_tikz(environment.children)

    def _nodes_contain_tikz(self, nodes: Sequence[Node], *, libraries: set[str] | None = None) -> bool:
        found = False
        for node in nodes:
            if isinstance(node, Environment):
                if node.name in self._TIKZ_ENVIRONMENTS:
                    found = True
                    if libraries is not None and node.name == "tikzcd":
                        libraries.add("cd")
                if self._nodes_contain_tikz(node.children, libraries=libraries):
                    found = True
        return found

    def _render_environment_to_latex(self, environment: Environment) -> str:
        header_parts = [f"\\begin{{{environment.name}}}"]
        for argument in environment.arguments:
            header_parts.append(self._render_argument_to_latex(argument))
        body = self._render_nodes_to_latex(environment.children)
        closing_indent = ""
        if body:
            if body.startswith("\n"):
                closing_indent = self._infer_latex_body_indent(body[1:])
            elif body[0] in {" ", "\t"}:
                closing_indent = self._infer_latex_body_indent(body)
                body = "\n" + body
            else:
                closing_indent = self._infer_latex_body_indent(body)
                prefix = "\n" + closing_indent if closing_indent else "\n"
                body = prefix + body
            body = re.sub(r"[ \t]+\n", "\n", body)
            body = body.rstrip()
        result = "".join(header_parts) + body
        if not body.endswith("\n"):
            result += "\n"
        if closing_indent:
            result += f"{closing_indent}\\end{{{environment.name}}}\n"
        else:
            result += f"\\end{{{environment.name}}}\n"
        return result

    def _infer_latex_body_indent(self, body: str) -> str:
        for line in body.splitlines():
            if not line:
                continue
            indent_chars: list[str] = []
            for char in line:
                if char in {" ", "\t"}:
                    indent_chars.append(char)
                else:
                    break
            if indent_chars:
                return "".join(indent_chars)
        return ""

    def _render_nodes_to_latex(self, nodes: Sequence[Node]) -> str:
        return "".join(self._render_node_to_latex(node) for node in nodes)

    def _render_node_to_latex(self, node: Node) -> str:
        if isinstance(node, Text):
            return node.content
        if isinstance(node, Comment):
            return f"%{node.content}"
        if isinstance(node, Group):
            inner = self._render_nodes_to_latex(node.children)
            if node.kind == "brace":
                return "{" + inner + "}"
            return "[" + inner + "]"
        if isinstance(node, Command):
            parts = ["\\", node.name]
            if node.star:
                parts.append("*")
            for argument in node.arguments:
                parts.append(self._render_argument_to_latex(argument))
            return "".join(parts)
        if isinstance(node, Environment):
            return self._render_environment_to_latex(node)
        if isinstance(node, Math):
            return self._render_math_to_latex(node)
        return ""

    def _render_argument_to_latex(self, argument: Argument) -> str:
        if argument.kind == "optional":
            return "[" + self._render_nodes_to_latex(argument.children) + "]"
        return "{" + self._render_nodes_to_latex(argument.children) + "}"

    def _render_math_to_latex(self, math: Math) -> str:
        delimiter = math.delimiter
        if delimiter in {"$", "$$"}:
            return f"{delimiter}{math.content}{delimiter}"
        if delimiter == "\\(...\\)":
            return f"\\({math.content}\\)"
        if delimiter == "\\[...\\]":
            return f"\\[{math.content}\\]"
        return math.content

    def _render_math(self, math: Math) -> str:
        raw_content = math.content
        if math.kind == "inline":
            normalized = self._escape_inline_math_square_brackets(raw_content)
            expanded = self._expand_math_macros(normalized).strip()
            escaped = self._escape_inline_math_square_brackets(expanded)
            return f"latexmath:[{escaped}]"
        content = self._expand_math_macros(raw_content).strip()
        return f"[latexmath]\n++++\n{content}\n++++\n\n"

    def _expand_math_macros(self, content: str) -> str:
        def replace_cat(match: re.Match[str]) -> str:
            argument = match.group(1)
            return rf"\mathbf{{{argument}}}"

        def replace_idarrow(match: re.Match[str]) -> str:
            argument = match.group(1)
            if argument:
                return rf"\mathbf{{id}}_{{{argument}}}"
            return r"\mathbf{id}"

        def replace_lim(match: re.Match[str]) -> str:
            argument = match.group(1)
            if argument:
                return rf"\mathbf{{Lim}}{{{argument}}}"
            return r"\mathbf{Lim}"

        def replace_fop(_: re.Match[str]) -> str:
            return r"\mathbf{F}^{\mathit{op}}"

        expanded = content
        for name, replacement in self._MATH_SIMPLE_MACROS.items():
            pattern = self._MATH_SIMPLE_MACRO_PATTERNS[name]
            expanded = pattern.sub(lambda _: replacement, expanded)
        expanded = self._RE_CAT.sub(replace_cat, expanded)
        expanded = self._RE_IDARROW.sub(replace_idarrow, expanded)
        expanded = self._RE_LIM.sub(replace_lim, expanded)
        expanded = self._RE_FOP.sub(replace_fop, expanded)
        expanded = expanded.replace(r"\symbf", r"\mathbf")
        expanded = expanded.replace(r"\Colon", "∷")
        return expanded

    def _escape_inline_math_square_brackets(self, content: str) -> str:
        if not content:
            return content

        result: list[str] = []
        index = 0
        optional_argument_depth = 0
        last_command_name: str | None = None
        command_just_parsed = False

        while index < len(content):
            char = content[index]

            if char == "\\":
                result.append(char)
                index += 1
                if index < len(content):
                    if content[index].isalpha():
                        start = index
                        while index < len(content) and content[index].isalpha():
                            result.append(content[index])
                            index += 1
                        last_command_name = content[start:index]
                    else:
                        result.append(content[index])
                        index += 1
                        last_command_name = None
                command_just_parsed = True
                continue

            if char == "[":
                if optional_argument_depth == 0 and (
                    not command_just_parsed
                    or (last_command_name in self._INLINE_BRACKET_ESCAPING_COMMANDS)
                ):
                    result.append(r"\lbrack")
                    next_index = index + 1
                    if next_index < len(content) and content[next_index].isalpha():
                        result.append(" ")
                else:
                    result.append(char)
                    optional_argument_depth += 1
                command_just_parsed = False
                last_command_name = None
                index += 1
                continue

            if char == "]":
                if optional_argument_depth > 0:
                    optional_argument_depth -= 1
                    result.append(char)
                else:
                    result.append(r"\rbrack")
                command_just_parsed = False
                last_command_name = None
                index += 1
                continue

            result.append(char)
            if not char.isspace():
                command_just_parsed = False
                last_command_name = None
            index += 1

        escaped = "".join(result)
        escaped = escaped.replace("{\\lbrack}", "\\lbrack")
        escaped = escaped.replace("{\\rbrack}", "\\rbrack")
        escaped = self._INLINE_LBRACK_LETTER_PATTERN.sub("\\\\lbrack ", escaped)
        return escaped

    def _render_math_environment(self, environment: Environment) -> str:
        self._math_block_depth += 1
        try:
            latex = self._render_environment_as_latex(environment)
        finally:
            self._math_block_depth -= 1
        expanded = self._expand_math_macros(latex)
        if not expanded.endswith("\n"):
            expanded += "\n"
        return f"[latexmath]\n++++\n{expanded}\n++++\n\n"

    def _render_environment_as_latex(self, environment: Environment) -> str:
        parts: list[str] = ["\\begin{", environment.name, "}"]
        for argument in environment.arguments:
            if argument.kind == "optional":
                parts.append("[")
                parts.append(self._render_nodes_as_latex(argument.children))
                parts.append("]")
            else:
                parts.append("{")
                parts.append(self._render_nodes_as_latex(argument.children))
                parts.append("}")
        children_latex = self._render_nodes_as_latex(environment.children)
        if children_latex:
            if not children_latex.startswith("\n"):
                children_latex = "\n" + children_latex
            if not children_latex.endswith("\n"):
                children_latex += "\n"
            parts.append(children_latex)
        parts.append("\\end{")
        parts.append(environment.name)
        parts.append("}")
        return "".join(parts)

    def _render_command_as_latex(self, command: Command) -> str:
        if command.name in {"", "\n"}:
            return "\\\\\n"
        parts: list[str] = ["\\", command.name]
        if command.star:
            parts.append("*")
        for argument in command.arguments:
            if argument.kind == "optional":
                parts.append("[")
                parts.append(self._render_nodes_as_latex(argument.children))
                parts.append("]")
            else:
                parts.append("{")
                parts.append(self._render_nodes_as_latex(argument.children))
                parts.append("}")
        return "".join(parts)

    def _render_math_as_latex(self, math: Math) -> str:
        delimiter = math.delimiter
        if delimiter == "$$" or delimiter == "$":
            return f"{delimiter}{math.content}{delimiter}"
        if delimiter == "\\[...\\]":
            return f"\\[{math.content}\\]"
        if delimiter == "\\(...\\)":
            return f"\\({math.content}\\)"
        return math.content

    def _render_nodes_as_latex(self, nodes: Sequence[Node]) -> str:
        parts: list[str] = []
        for node in nodes:
            if isinstance(node, Text):
                parts.append(node.content)
                continue
            if isinstance(node, Comment):
                parts.append(f"%{node.content}")
                continue
            if isinstance(node, Group):
                if node.kind == "brace":
                    parts.append("{")
                    parts.append(self._render_nodes_as_latex(node.children))
                    parts.append("}")
                else:
                    parts.append("[")
                    parts.append(self._render_nodes_as_latex(node.children))
                    parts.append("]")
                continue
            if isinstance(node, Command):
                parts.append(self._render_command_as_latex(node))
                continue
            if isinstance(node, Environment):
                parts.append(self._render_environment_as_latex(node))
                continue
            if isinstance(node, Math):
                parts.append(self._render_math_as_latex(node))
        return "".join(parts)

    def _render_list(self, children: Sequence[Node], *, numbered: bool) -> str:
        self._list_depth += 1
        try:
            items: list[_ListItem] = []
            current: list[Node] = []
            for node in children:
                if isinstance(node, Command) and node.name == "item":
                    if current:
                        items.append(_ListItem(nodes=current))
                    current = []
                    continue
                current.append(node)
            if current:
                items.append(_ListItem(nodes=current))
            lines: list[str] = []
            counter = 0
            for item in items:
                rendered = self._render_nodes(item.nodes).strip()
                if not rendered:
                    continue
                blocks = self._split_list_item_blocks(rendered)
                if not blocks:
                    continue
                counter += 1
                if numbered:
                    prefix = "." * self._list_depth + " "
                else:
                    prefix = "*" * self._list_depth + " "
                item_lines: list[str] = []
                for index, block in enumerate(blocks):
                    block_is_block_level = self._is_block_level(block)
                    normalized_block = self._normalize_block_lines(
                        block,
                        block_level=block_is_block_level,
                    )
                    if not normalized_block:
                        continue
                    if index == 0:
                        if not block_is_block_level:
                            first_line, *rest_lines = normalized_block
                            item_lines.append(prefix + first_line)
                            item_lines.extend(rest_lines)
                        else:
                            marker = prefix.strip()
                            item_lines.append(f"{marker} {{empty}}" if marker else "{empty}")
                            item_lines.append("+")
                            item_lines.extend(normalized_block)
                        continue
                    if item_lines and item_lines[-1] != "+":
                        item_lines.append("+")
                    item_lines.extend(normalized_block)
                lines.extend(item_lines)
            if not lines:
                return ""
            return "\n".join(lines) + "\n\n"
        finally:
            self._list_depth -= 1

    def _split_list_item_blocks(self, rendered: str) -> list[list[str]]:
        blocks: list[list[str]] = []
        current: list[str] = []
        delimiter: str | None = None
        for line in rendered.splitlines():
            stripped = line.strip()
            if delimiter:
                current.append(line)
                if stripped == delimiter:
                    delimiter = None
                continue
            if stripped in self._BLOCK_DELIMITERS:
                if not current:
                    current = [line]
                else:
                    current.append(line)
                delimiter = stripped
                continue
            if self._is_block_starter_line(stripped):
                if current:
                    blocks.append(current)
                    current = []
                current.append(line)
                continue
            if not stripped:
                if current:
                    blocks.append(current)
                    current = []
                continue
            current.append(line)
        if current:
            blocks.append(current)
        return blocks

    def _is_list_marker_line(self, stripped: str) -> bool:
        if not stripped:
            return False
        if stripped.startswith("."):
            if len(stripped) > 1 and stripped[1].isalnum():
                return True
            index = 0
            while index < len(stripped) and stripped[index] == ".":
                index += 1
            if index > 0 and index < len(stripped) and stripped[index].isspace():
                return True
        if stripped.startswith("*"):
            index = 0
            while index < len(stripped) and stripped[index] == "*":
                index += 1
            if index > 0 and index < len(stripped) and stripped[index].isspace():
                return True
        return False

    def _is_block_starter_line(self, stripped: str) -> bool:
        if not stripped:
            return False
        if stripped.startswith("[[") and stripped.endswith("]]"):
            return False
        if stripped in self._BLOCK_DELIMITERS:
            return True
        if stripped.startswith("["):
            return True
        if self._is_list_marker_line(stripped):
            return True
        if stripped.startswith("image::") or stripped.startswith("video::"):
            return True
        if stripped.startswith("include::"):
            return True
        return False

    def _is_block_level(self, block: Sequence[str]) -> bool:
        for line in block:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("[[") and stripped.endswith("]]"):
                continue
            if stripped in self._BLOCK_DELIMITERS:
                return True
            if stripped.startswith("["):
                return True
            if self._is_list_marker_line(stripped):
                return True
            if stripped.startswith("image::") or stripped.startswith("video::"):
                return True
            if stripped.startswith("include::"):
                return True
            return False
        return False

    def _should_trim_block_line(self, stripped: str) -> bool:
        if not stripped:
            return True
        if stripped.startswith("[[") and stripped.endswith("]]"):
            return True
        if stripped in self._BLOCK_DELIMITERS:
            return True
        if stripped.startswith("["):
            return True
        if self._is_list_marker_line(stripped):
            return True
        if stripped.startswith("image::") or stripped.startswith("video::"):
            return True
        if stripped.startswith("include::"):
            return True
        return False

    def _normalize_block_lines(self, block: Sequence[str], *, block_level: bool) -> list[str]:
        if block_level:
            normalized: list[str] = []
            for line in block:
                stripped = line.strip()
                if self._should_trim_block_line(stripped):
                    normalized.append(line.lstrip())
                else:
                    normalized.append(line)
            return normalized
        return [line.lstrip() for line in block]

    def _normalize_caption(self, caption: str) -> str:
        return " ".join(caption.split())

    def _render_snippet_includes(self, identifier: str, option: str | None) -> str | None:
        document = self._current_document
        if document is None:
            return None
        base_dir = document.path.parent
        blocks: list[str] = []
        # Optional LaTeX arguments (for example "b" to enable breaklines) are ignored in AsciiDoc output.
        _ = (option or "").strip()
        for language, extension in self._SNIPPET_LANGUAGES:
            if language not in self._expand_snippet_languages:
                continue
            relative_path = Path("code") / language / f"{identifier}.{extension}"
            absolute_path = base_dir / relative_path
            if not absolute_path.exists():
                continue
            include_path = self._resolve_resource_path(base_dir, relative_path)
            block_lines = [
                f"[source,{language}]",
                "----",
                f"include::{include_path}[]",
                "----",
            ]
            blocks.append("\n".join(block_lines))
        if not blocks:
            return None
        return "\n\n".join(blocks) + "\n"

    def _resolve_resource_path(self, base_dir: Path, raw_path: str | Path) -> str:
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            candidate = base_dir / candidate
        try:
            return str(candidate.resolve(strict=False))
        except (OSError, RuntimeError):
            return str(candidate)

    def _render_minipage_cell(self, environment: Environment) -> str:
        caption: str | None = None
        image_paths: list[str] = []
        extra_nodes: list[Node] = []
        base_dir = self._current_document.path.parent if self._current_document else Path()

        for node in environment.children:
            if isinstance(node, Command):
                if node.name == "includegraphics":
                    if node.arguments:
                        target = node.arguments[-1]
                        path_text = self._render_nodes(target.children, inline=True).strip()
                        if path_text:
                            resolved = self._resolve_resource_path(base_dir, path_text)
                            image_paths.append(resolved)
                    continue
                if node.name == "caption":
                    caption = self._argument(node, 0, kind="required")
                    continue
                if node.name in {"centering", "hfill"}:
                    continue
            extra_nodes.append(node)

        normalized_caption = self._normalize_caption(caption) if caption else None
        extra_content = self._render_nodes(extra_nodes).strip()

        block_lines: list[str] = []
        if normalized_caption:
            block_lines.append(f".{normalized_caption}")
        for path in image_paths:
            if normalized_caption:
                block_lines.append(f"image::{path}[{normalized_caption}]")
            else:
                block_lines.append(f"image::{path}[]")
        if extra_content:
            block_lines.append(extra_content)

        if not block_lines:
            return ""
        content = "\n".join(block_lines)
        return f"a|\n{content}"

    def _render_figure(self, environment: Environment) -> str:
        if self._figure_contains_tikz(environment):
            return self._render_tikz_figure(environment)
        caption: str | None = None
        minipage_cells: list[str] = []
        images: list[str] = []
        fallback_nodes: list[Node] = []
        for node in environment.children:
            if isinstance(node, Environment) and node.name == "minipage":
                cell = self._render_minipage_cell(node)
                if cell:
                    minipage_cells.append(cell)
                continue
            if isinstance(node, Command):
                if node.name == "includegraphics":
                    rendered_image = self._render_command(node, inline=False).strip()
                    if rendered_image:
                        images.append(rendered_image)
                    continue
                if node.name == "caption":
                    caption = self._argument(node, 0, kind="required")
                    continue
            fallback_nodes.append(node)
        lines: list[str] = []
        normalized_caption = self._normalize_caption(caption) if caption else None
        if normalized_caption:
            lines.append(f".{normalized_caption}")
        extra = self._render_nodes(fallback_nodes).strip()
        if minipage_cells:
            cols_spec = ",".join(["^.^"] * len(minipage_cells)) or "^.^"
            lines.append(f"[cols=\"{cols_spec}\",frame=\"none\",grid=\"none\"]")
            lines.append("|===")
            for cell in minipage_cells:
                lines.append(cell)
            lines.append("|===")
            if extra:
                lines.append(extra)
            return "\n".join(lines) + "\n\n"
        if images:
            lines.extend(images)
            if extra:
                lines.append(extra)
            return "\n".join(lines) + "\n\n"
        if extra:
            lines.append(extra)
        else:
            fallback = self._render_nodes(environment.children).strip()
            if fallback:
                lines.append(fallback)
        return "\n".join(lines) + "\n\n"

    def _render_longtable(self, environment: Environment) -> str:
        caption: str | None = None
        label: str | None = None
        rows: list[list[str]] = []
        current_cell_nodes: list[Node] = []
        current_row_cells: list[str] = []
        header_row_count = 0
        max_columns = 0

        column_spec = self._argument(environment, 0, kind="required")
        column_markers = re.findall(r"[lcr]", column_spec)
        minipage_env: Environment | None = None
        special_case_allowed_commands = {"toprule", "midrule", "bottomrule", "tabularnewline"}

        def only_whitespace(text_node: Text) -> bool:
            return not text_node.content.strip()

        special_case_possible = len(column_markers) == 1

        if special_case_possible:
            for node in environment.children:
                if isinstance(node, Environment) and node.name == "minipage":
                    if minipage_env is not None:
                        special_case_possible = False
                        break
                    minipage_env = node
                    continue
                if isinstance(node, Command):
                    if node.name in special_case_allowed_commands:
                        continue
                    special_case_possible = False
                    break
                if isinstance(node, Text):
                    if only_whitespace(node):
                        continue
                    special_case_possible = False
                    break
                else:
                    special_case_possible = False
                    break

        if special_case_possible and minipage_env is not None:
            raw_body = self._render_nodes(minipage_env.children)
            dedented = textwrap.dedent(raw_body)
            body = "\n".join(line.lstrip() for line in dedented.splitlines()).strip()
            if not body:
                return ""
            lines = ["[.longtable-panel]", "====", body, "====", ""]
            return "\n".join(lines)

        def flush_cell() -> None:
            nonlocal current_cell_nodes, current_row_cells
            rendered = self._render_nodes(current_cell_nodes, inline=True).strip()
            current_row_cells.append(rendered)
            current_cell_nodes = []

        def flush_row() -> None:
            nonlocal current_cell_nodes, current_row_cells, rows, max_columns
            if current_cell_nodes:
                flush_cell()
            if not current_row_cells:
                return
            if all(not cell for cell in current_row_cells):
                current_row_cells = []
                return
            max_columns = max(max_columns, len(current_row_cells))
            rows.append(current_row_cells)
            current_row_cells = []

        for node in environment.children:
            if isinstance(node, Command):
                if node.name in {"toprule", "midrule", "bottomrule"}:
                    continue
                if node.name in {"endhead", "endfirsthead"}:
                    flush_row()
                    header_row_count = len(rows)
                    continue
                if node.name in {"endfoot", "endlastfoot"}:
                    flush_row()
                    continue
                if node.name == "tabularnewline":
                    flush_row()
                    continue
                if node.name == "&":
                    flush_cell()
                    continue
                if node.name == "caption":
                    caption = self._argument(node, 0, kind="required")
                    continue
                if node.name == "label":
                    label = self._argument(node, 0, kind="required")
                    continue
            if isinstance(node, Text):
                content = node.content
                if "&" in content:
                    parts = content.split("&")
                    for index, part in enumerate(parts):
                        if part:
                            current_cell_nodes.append(Text(part))
                        if index < len(parts) - 1:
                            flush_cell()
                    continue
            current_cell_nodes.append(node)
        flush_row()

        if not rows:
            return ""

        column_count = max_columns if max_columns else max(len(row) for row in rows)
        for row in rows:
            if len(row) < column_count:
                row.extend([""] * (column_count - len(row)))

        attributes: list[str] = []
        if column_count:
            cols_attr = ",".join(["1"] * column_count)
            attributes.append(f'cols="{cols_attr}"')
        if header_row_count > 0:
            attributes.append('options="header"')

        lines: list[str] = []
        if label:
            lines.append(f"[[{label}]]")
        if caption:
            lines.append(f".{self._normalize_caption(caption)}")
        if attributes:
            lines.append(f"[{','.join(attributes)}]")
        lines.append("|===")

        for index, row in enumerate(rows):
            is_header = header_row_count > 0 and index < header_row_count
            marker = "h|" if is_header else "|"
            for cell in row:
                text = cell if cell else ""
                if text:
                    text = self._escape_table_cell_code_pipes(text)
                lines.append(f"{marker} {text}" if text else f"{marker} ")

        lines.append("|===")
        lines.append("")
        return "\n".join(lines)

    def _render_argument(self, command: Command, argument: Argument) -> str:
        return self._render_nodes(argument.children, inline=True)

    def _argument(
        self,
        node: Command | Environment,
        index: int,
        *,
        kind: str | None = None,
        strip: bool = True,
    ) -> str:
        if kind == "required":
            arguments = [arg for arg in node.arguments if arg.kind == "required"]
        elif kind == "optional":
            arguments = [arg for arg in node.arguments if arg.kind == "optional"]
        else:
            arguments = list(node.arguments)
        try:
            argument = arguments[index]
        except IndexError:
            return ""
        rendered = self._render_nodes(argument.children, inline=True)
        return rendered.strip() if strip else rendered


def render_asciidoc_document(
    document: Document,
    *,
    expand_snippet_languages: Sequence[str] | None = None,
) -> str:
    renderer = AsciiDocRenderer(expand_snippet_languages=expand_snippet_languages)
    return renderer.render_document(document)


def render_asciidoc_documents(
    documents: Iterable[Document],
    *,
    expand_snippet_languages: Sequence[str] | None = None,
) -> str:
    renderer = AsciiDocRenderer(expand_snippet_languages=expand_snippet_languages)
    return renderer.render_documents(list(documents))
