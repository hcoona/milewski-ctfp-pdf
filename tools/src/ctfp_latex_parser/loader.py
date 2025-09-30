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


def parse_path(path: Path) -> list[Document]:
    """Parse a path that can be either a file or a directory.

    If path is a .tex file, parse just that file.
    If path is a directory, parse all .tex files in it recursively.
    """
    path = path.resolve()
    if not path.exists():
        raise FileNotFoundError(f"Path {path} does not exist")

    if path.is_file():
        if not path.suffix == ".tex":
            raise ValueError(f"File {path} is not a .tex file")
        return [parse_file(path)]
    elif path.is_dir():
        return parse_directory(path)
    else:
        raise ValueError(f"Path {path} is neither a file nor a directory")
