#!/usr/bin/env python3
import pathlib
import re
import sys
from typing import List


def split_summary_lines(lines: List[str], src_path: str) -> (List[str], List[str]):
    pattern = re.compile(rf"^{re.escape(src_path)}\s+Parse:")
    summary: List[str] = []
    while lines and pattern.match(lines[-1]):
        summary.append(lines.pop())
    summary.reverse()
    return lines, summary


def main() -> int:
    if len(sys.argv) != 6:
        print(
            "Usage: postprocess_cst.py <src-path> <tmp-path> <output-path> <log-path> <stderr-path>",
            file=sys.stderr,
        )
        return 2

    src_path, tmp_path, output_path, log_path, stderr_path = sys.argv[1:]

    tmp = pathlib.Path(tmp_path)
    out = pathlib.Path(output_path)
    log = pathlib.Path(log_path)
    err = pathlib.Path(stderr_path)

    lines = tmp.read_text(encoding="utf-8").splitlines()
    kept_lines, summary_lines = split_summary_lines(lines, src_path)

    output_text = "\n".join(kept_lines)
    if output_text:
        output_text += "\n"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(output_text, encoding="utf-8")

    log_lines = list(summary_lines)
    if err.exists():
        err_text = err.read_text(encoding="utf-8")
        if err_text:
            log_lines.extend(err_text.rstrip("\n").splitlines())

    if not log_lines:
        log_lines.append(f"{src_path} parse exited with status 1 without additional diagnostics.")

    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("\n".join(log_lines) + "\n", encoding="utf-8")

    return 0


if __name__ == "__main__":
    sys.exit(main())
