from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from .analysis import document_stats
from .loader import parse_path
from .renderers import render_asciidoc_documents


def format_summary(documents: Iterable) -> str:
    lines: list[str] = []
    for document in documents:
        stats = document_stats(document)
        lines.append(
            f"{document.path}: nodes={stats.get('total_nodes', 0)}"
            f", commands={stats.get('command_nodes', 0)}"
            f", environments={stats.get('environment_nodes', 0)}"
            f", text_nodes={stats.get('text_nodes', 0)}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ctfp-parse",
        description="Parse the src/content LaTeX subset and emit structured data.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("src/content"),
        help="Root directory or .tex file to parse. If a directory, parse all .tex files recursively.",
    )
    parser.add_argument(
        "--format",
        choices=("summary", "json", "asciidoc"),
        default="summary",
        help="Output format. Summary prints counts, json emits full AST, asciidoc renders text.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty print JSON output.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path to write the result. Defaults to stdout.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="If provided, only parse the first N documents.",
    )
    parser.add_argument(
        "--expand-snippet-language",
        action="append",
        choices=("ocaml", "reason", "scala"),
        help=(
            "Additional snippet languages to expand alongside Haskell. "
            "Repeat the flag to include multiple languages."
        ),
    )
    args = parser.parse_args(argv)

    documents = parse_path(args.root)
    if args.limit is not None:
        documents = documents[: args.limit]

    if not documents:
        raise SystemExit(f"No LaTeX files found at {args.root}")

    extra_languages = args.expand_snippet_language or []

    if args.format == "summary":
        output = format_summary(documents)
    elif args.format == "json":
        payload = [document.to_dict() for document in documents]
        output = json.dumps(payload, indent=2 if args.pretty else None, ensure_ascii=False)
    else:
        output = render_asciidoc_documents(
            documents,
            expand_snippet_languages=extra_languages,
        )

    if args.output:
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
