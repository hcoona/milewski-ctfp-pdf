from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Literal, Sequence


class Node:
    def to_dict(self) -> dict:
        raise NotImplementedError


@dataclass
class Text(Node):
    content: str

    def to_dict(self) -> dict:
        return {"type": "text", "content": self.content}


@dataclass
class Comment(Node):
    content: str

    def to_dict(self) -> dict:
        return {"type": "comment", "content": self.content}


@dataclass
class Argument:
    kind: Literal["optional", "required"]
    children: Sequence[Node] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "children": [child.to_dict() for child in self.children],
        }


@dataclass
class Command(Node):
    name: str
    star: bool
    arguments: Sequence[Argument] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "type": "command",
            "name": self.name,
            "star": self.star,
            "arguments": [arg.to_dict() for arg in self.arguments],
        }


@dataclass
class Group(Node):
    kind: Literal["brace", "bracket"]
    children: Sequence[Node] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "type": "group",
            "kind": self.kind,
            "children": [child.to_dict() for child in self.children],
        }


@dataclass
class Math(Node):
    kind: Literal["inline", "display"]
    delimiter: str
    content: str

    def to_dict(self) -> dict:
        return {
            "type": "math",
            "kind": self.kind,
            "delimiter": self.delimiter,
            "content": self.content,
        }


@dataclass
class Environment(Node):
    name: str
    arguments: Sequence[Argument] = field(default_factory=tuple)
    children: Sequence[Node] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "type": "environment",
            "name": self.name,
            "arguments": [arg.to_dict() for arg in self.arguments],
            "children": [child.to_dict() for child in self.children],
        }


@dataclass
class Document:
    path: Path
    children: Sequence[Node] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "path": str(self.path),
            "children": [child.to_dict() for child in self.children],
        }


def merge_text_nodes(nodes: Iterable[Node]) -> list[Node]:
    merged: list[Node] = []
    for node in nodes:
        if isinstance(node, Text):
            if merged and isinstance(merged[-1], Text):
                merged[-1].content += node.content
            else:
                merged.append(Text(node.content))
        else:
            merged.append(node)
    return merged
