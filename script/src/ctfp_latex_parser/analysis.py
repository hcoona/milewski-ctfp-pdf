from __future__ import annotations

from collections import Counter
from typing import Iterable

from .nodes import Argument, Command, Comment, Document, Environment, Group, Math, Node, Text


def iter_nodes(nodes: Iterable[Node]) -> Iterable[Node]:
    for node in nodes:
        yield node
        if isinstance(node, Environment):
            yield from iter_nodes(node.children)
        elif isinstance(node, Group):
            yield from iter_nodes(node.children)
        elif isinstance(node, Command):
            for argument in node.arguments:
                yield from iter_nodes(argument.children)


def document_stats(document: Document) -> dict:
    counter: Counter[str] = Counter()
    for node in iter_nodes(document.children):
        if isinstance(node, Text):
            counter["text_nodes"] += 1
            counter["text_chars"] += len(node.content)
        elif isinstance(node, Comment):
            counter["comment_nodes"] += 1
        elif isinstance(node, Command):
            counter["command_nodes"] += 1
        elif isinstance(node, Environment):
            counter["environment_nodes"] += 1
        elif isinstance(node, Group):
            counter["group_nodes"] += 1
        elif isinstance(node, Math):
            counter["math_nodes"] += 1
    counter["total_nodes"] = sum(counter[key] for key in (
        "text_nodes",
        "comment_nodes",
        "command_nodes",
        "environment_nodes",
        "group_nodes",
        "math_nodes",
    ))
    return dict(counter)
