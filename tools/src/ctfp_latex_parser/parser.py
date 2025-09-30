from __future__ import annotations

from typing import Literal, Sequence

from .nodes import (
    Argument,
    Command,
    Comment,
    Environment,
    Group,
    Math,
    Node,
    Text,
    merge_text_nodes,
)


class LatexParser:
    def __init__(self, source: str):
        self.source = source
        self.length = len(source)
        self.position = 0

    def parse(self) -> list[Node]:
        nodes = self._collect_nodes(stop_tokens=(), stop_chars=frozenset())
        return merge_text_nodes(nodes)

    def _collect_nodes(
        self,
        stop_tokens: Sequence[str],
        stop_chars: Sequence[str],
    ) -> list[Node]:
        collected: list[Node] = []
        tokens = tuple(sorted(stop_tokens, key=len, reverse=True))
        stop_char_set = frozenset(stop_chars)
        while self.position < self.length:
            if tokens:
                matched = self._match_any(tokens)
                if matched is not None:
                    break
            current = self._current_char()
            if stop_char_set and current in stop_char_set:
                break
            if current == "%":
                comment_node, trailing = self._parse_comment()
                collected.append(comment_node)
                if trailing:
                    collected.append(Text(trailing))
                continue
            if current == "\\":
                if self._peek_string("\\begin{"):
                    collected.append(self._parse_environment())
                    continue
                if self._peek_string("\\end{"):
                    break
                if self._peek_string("\\["):
                    collected.append(self._parse_math_delimited("\\[", "\\]", "display"))
                    continue
                if self._peek_string("\\("):
                    collected.append(self._parse_math_delimited("\\(", "\\)", "inline"))
                    continue
                collected.append(self._parse_command())
                continue
            if current == "$":
                collected.append(self._parse_math_dollar())
                continue
            if current == "{":
                collected.append(self._parse_standalone_group("brace"))
                continue
            if current == "}":
                break
            if current == "]" and "]" in stop_char_set:
                break
            collected.append(self._parse_text(tokens, stop_char_set))
        return merge_text_nodes(collected)

    def _parse_text(
        self,
        stop_tokens: Sequence[str],
        stop_chars: frozenset[str],
    ) -> Text:
        start = self.position
        while self.position < self.length:
            if stop_tokens and self._match_any(stop_tokens) is not None:
                break
            current = self._current_char()
            if current in "\\%${[}]":
                break
            if stop_chars and current in stop_chars:
                break
            self.position += 1
        if self.position == start:
            self.position += 1
        return Text(self.source[start:self.position])

    def _parse_comment(self) -> tuple[Comment, str]:
        self.position += 1
        start = self.position
        while self.position < self.length and self.source[self.position] not in "\r\n":
            self.position += 1
        comment_text = self.source[start:self.position]
        trailing = ""
        if self.position < self.length:
            if self.source[self.position] == "\r":
                trailing += "\r"
                self.position += 1
                if self.position < self.length and self.source[self.position] == "\n":
                    trailing += "\n"
                    self.position += 1
            elif self.source[self.position] == "\n":
                trailing += "\n"
                self.position += 1
        return Comment(comment_text), trailing

    def _parse_command(self) -> Command:
        assert self._current_char() == "\\"
        self.position += 1
        name = self._read_command_name()
        star = False
        if self._current_char_optional() == "*":
            star = True
            self.position += 1
        arguments: list[Argument] = []
        while True:
            next_char = self._current_char_optional()
            if next_char == "[":
                arguments.append(self._parse_argument("optional"))
                continue
            if next_char == "{":
                arguments.append(self._parse_argument("required"))
                continue
            break
        return Command(name=name, star=star, arguments=tuple(arguments))

    def _parse_argument(self, kind: Literal["optional", "required"]) -> Argument:
        if kind == "optional":
            assert self._current_char() == "["
            self.position += 1
            children = self._collect_nodes(stop_tokens=(), stop_chars=("]",))
            self._expect_char("]")
            self.position += 1
        else:
            assert self._current_char() == "{"
            self.position += 1
            children = self._collect_nodes(stop_tokens=(), stop_chars=("}",))
            self._expect_char("}")
            self.position += 1
        return Argument(kind=kind, children=tuple(children))

    def _parse_standalone_group(self, kind: Literal["brace", "bracket"]) -> Group:
        closing = "}" if kind == "brace" else "]"
        self.position += 1
        children = self._collect_nodes(stop_tokens=(), stop_chars=(closing,))
        self._expect_char(closing)
        self.position += 1
        return Group(kind=kind, children=tuple(children))

    def _parse_environment(self) -> Environment:
        assert self._peek_string("\\begin{")
        self.position += len("\\begin")
        self._consume_whitespace()
        self._expect_char("{")
        self.position += 1
        name = self._read_until("}")
        self._expect_char("}")
        self.position += 1
        leading_whitespace = self._read_whitespace()
        trailing_whitespace = leading_whitespace
        arguments: list[Argument] = []
        while True:
            current = self._current_char_optional()
            if current == "[":
                arguments.append(self._parse_argument("optional"))
                trailing_whitespace = self._read_whitespace()
                continue
            if current == "{":
                arguments.append(self._parse_argument("required"))
                trailing_whitespace = self._read_whitespace()
                continue
            break
        stop_token = f"\\end{{{name}}}"
        children = self._collect_nodes(stop_tokens=(stop_token,), stop_chars=frozenset())
        indent = self._extract_indent_from_whitespace(trailing_whitespace if arguments else leading_whitespace)
        if indent:
            children = merge_text_nodes([Text(indent), *children])
        self._expect_environment_end(name)
        return Environment(name=name, arguments=tuple(arguments), children=tuple(children))

    def _expect_environment_end(self, name: str) -> None:
        self._expect_string("\\end")
        self.position += len("\\end")
        self._consume_whitespace()
        self._expect_char("{")
        self.position += 1
        closing_name = self._read_until("}")
        self._expect_char("}")
        self.position += 1
        if closing_name != name:
            raise ValueError(f"Mismatched environment end: expected {name!r} but got {closing_name!r}")

    def _parse_math_dollar(self) -> Math:
        assert self._current_char() == "$"
        delimiter = "$$" if self._peek_char(1) == "$" else "$"
        self.position += len(delimiter)
        content = self._read_until(delimiter)
        if self._peek_string(delimiter):
            self.position += len(delimiter)
        return Math(
            kind="display" if delimiter == "$$" else "inline",
            delimiter=delimiter,
            content=content,
        )

    def _parse_math_delimited(self, opening: str, closing: str, kind: str) -> Math:
        assert self._peek_string(opening)
        self.position += len(opening)
        content = self._read_until(closing)
        if self._peek_string(closing):
            self.position += len(closing)
        return Math(kind=kind, delimiter=f"{opening}...{closing}", content=content)

    def _read_command_name(self) -> str:
        if self.position >= self.length:
            return ""
        start = self.position
        ch = self.source[self.position]
        if ch.isalpha():
            self.position += 1
            while self.position < self.length and self.source[self.position].isalpha():
                self.position += 1
            return self.source[start:self.position]
        self.position += 1
        return ch

    def _read_until(self, marker: str) -> str:
        start = self.position
        while self.position < self.length and not self._peek_string(marker):
            self.position += 1
        return self.source[start:self.position]

    def _expect_char(self, char: str) -> None:
        actual = self._current_char_optional()
        if actual != char:
            snippet = self.source[self.position : self.position + 20]
            raise ValueError(
                f"Expected {char!r} but got {actual!r} at position {self.position}: {snippet!r}"
            )

    def _expect_string(self, value: str) -> None:
        if not self._peek_string(value):
            snippet = self.source[self.position : self.position + len(value) + 10]
            raise ValueError(f"Expected {value!r} at position {self.position}: {snippet!r}")

    def _consume_whitespace(self) -> None:
        while self.position < self.length and self.source[self.position] in " \t\r\n":
            self.position += 1

    def _read_whitespace(self) -> str:
        start = self.position
        while self.position < self.length and self.source[self.position] in " \t\r\n":
            self.position += 1
        return self.source[start:self.position]

    def _extract_indent_from_whitespace(self, whitespace: str) -> str:
        if not whitespace:
            return ""
        normalized = whitespace.replace("\r\n", "\n").replace("\r", "\n")
        last_newline = normalized.rfind("\n")
        if last_newline == -1:
            return ""
        indent = normalized[last_newline + 1 :]
        return indent

    def _current_char(self) -> str:
        if self.position >= self.length:
            raise ValueError("Read past end of source")
        return self.source[self.position]

    def _current_char_optional(self) -> str | None:
        if self.position >= self.length:
            return None
        return self.source[self.position]

    def _peek_char(self, offset: int) -> str | None:
        index = self.position + offset
        if index >= self.length:
            return None
        return self.source[index]

    def _peek_string(self, value: str) -> bool:
        return self.source.startswith(value, self.position)

    def _match_any(self, tokens: Sequence[str]) -> str | None:
        for token in tokens:
            if self._peek_string(token):
                return token
        return None


def parse_text(source: str) -> list[Node]:
    parser = LatexParser(source)
    return parser.parse()
