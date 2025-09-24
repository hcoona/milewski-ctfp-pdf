from __future__ import annotations

import re

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
        title = self._guess_title(document.path)
        body = self._render_nodes(document.children).strip()
        parts = [f"= {title}"]
        if body:
            parts.append("")
            parts.append(body)
        return "\n".join(parts) + "\n"

    def render_documents(self, documents: Sequence[Document]) -> str:
        rendered = [self.render_document(document).rstrip() for document in documents]
        if not rendered:
            return ""
        return "\n\n////\n\n".join(rendered) + "\n"

    def _render_nodes(self, nodes: Sequence[Node], *, inline: bool = False) -> str:
        chunks: list[str] = []
        for node in nodes:
            chunks.append(self._render_node(node, inline=inline))
        return "".join(chunks)

    def _escape_text(self, text: str) -> str:
        text = self._DOUBLE_QUOTE_PATTERN.sub(lambda match: f'"{match.group(1)}"', text)
        text = text.replace("``", '"').replace("''", '"')
        text = text.replace("C++", "{cpp}")
        text = text.replace("---", "--")
        return text.replace(r"\#", "#")

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
        if name == "Colon":
            return "∷"
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
        if name in {"align", "align*", "equation", "equation*", "gather", "gather*"}:
            self._math_block_depth += 1
            try:
                body = self._render_nodes(environment.children)
            finally:
                self._math_block_depth -= 1
            body = re.sub(r"\n\s*\n", "\n", body)
            lines = [part.strip() for part in body.splitlines()]
            body = "\n".join(lines).strip()
            return f"[latexmath]\n++++\n{body}\n++++\n\n"
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

    def _render_math(self, math: Math) -> str:
        content = self._expand_math_macros(math.content).strip()
        if math.kind == "inline":
            return f"latexmath:[{content}]"
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

    def _guess_title(self, path: Path) -> str:
        stem = path.stem.replace("_", " ").replace("-", " ")
        title = " ".join(part.capitalize() for part in stem.split())
        return title or path.stem


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
