from __future__ import annotations

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
    def __init__(self) -> None:
        self._current_document: Document | None = None

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

    def _render_node(self, node: Node, *, inline: bool) -> str:
        if isinstance(node, Text):
            return node.content
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
            return "\n"
        if name == "par":
            return "\n\n"
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
            if suffix:
                return f"xref:{target}[{suffix}]"
            return f"xref:{target}[]"
        if name == "ensuremath":
            expr = self._argument(command, 0, kind="required")
            return f"latexmath:[{expr}]"
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
        if name == "noindent":
            return ""
        if name == "includegraphics":
            if command.arguments:
                path_text = self._render_nodes(command.arguments[-1].children, inline=True).strip()
                if path_text:
                    return f"image::{path_text}[]"
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
        if name in {"snip", "snipv", "verbatim", "Verbatim"}:
            language = self._argument(environment, 0, kind="required")
            body = self._render_code_block(environment.children)
            header = f"[source,{language}]" if language else "[source]"
            return f"{header}\n----\n{body}\n----\n\n"
        if name == "figure":
            return self._render_figure(environment)
        if name in {"align", "equation"}:
            body = self._render_nodes(environment.children).strip()
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
        content = math.content.strip()
        if math.kind == "inline":
            return f"latexmath:[{content}]"
        return f"[latexmath]\n++++\n{content}\n++++\n\n"

    def _render_list(self, children: Sequence[Node], *, numbered: bool) -> str:
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
            counter += 1
            rendered_lines = rendered.splitlines()
            first_line = rendered_lines[0].lstrip()
            rest_lines = [line.lstrip() for line in rendered_lines[1:]]
            prefix = f"{counter}. " if numbered else "* "
            lines.append(prefix + first_line)
            lines.extend(rest_lines)
        if not lines:
            return ""
        return "\n".join(lines) + "\n\n"

    def _render_figure(self, environment: Environment) -> str:
        image_path: str | None = None
        caption: str | None = None
        for node in environment.children:
            if isinstance(node, Command):
                if node.name == "includegraphics":
                    if node.arguments:
                        target = node.arguments[-1]
                        image_path = self._render_nodes(target.children, inline=True).strip()
                elif node.name == "caption":
                    caption = self._argument(node, 0, kind="required")
        lines: list[str] = []
        if caption:
            lines.append(f".{caption}")
        if image_path:
            lines.append(f"image::{image_path}[]")
        else:
            lines.append(self._render_nodes(environment.children).strip())
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


def render_asciidoc_document(document: Document) -> str:
    renderer = AsciiDocRenderer()
    return renderer.render_document(document)


def render_asciidoc_documents(documents: Iterable[Document]) -> str:
    renderer = AsciiDocRenderer()
    return renderer.render_documents(list(documents))
