from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from .analysis import document_stats
from .loader import parse_directory


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
        help="Root directory that contains LaTeX chapters.",
    )
    parser.add_argument(
        "--format",
        choices=("summary", "json"),
        default="summary",
        help="Output format. Summary prints counts, json emits full AST.",
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
    args = parser.parse_args(argv)

    documents = parse_directory(args.root)
    if args.limit is not None:
        documents = documents[: args.limit]

    if not documents:
        raise SystemExit(f"No LaTeX files found below {args.root}")

    if args.format == "summary":
        output = format_summary(documents)
    else:
        payload = [document.to_dict() for document in documents]
        output = json.dumps(payload, indent=2 if args.pretty else None, ensure_ascii=False)

    if args.output:
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
