from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .nodes import Document
from .parser import parse_text


def parse_file(path: Path, *, encoding: str = "utf-8") -> Document:
    source = path.read_text(encoding=encoding)
    children = parse_text(source)
    return Document(path=path, children=tuple(children))


def parse_directory(root: Path) -> list[Document]:
    root = root.resolve()
    if not root.exists():
        raise FileNotFoundError(f"Root directory {root} does not exist")
    documents: list[Document] = []
    for tex_file in sorted(root.rglob("*.tex")):
        documents.append(parse_file(tex_file))
    return documents
