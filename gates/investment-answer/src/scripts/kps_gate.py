#!/usr/bin/env python3
"""Command-line entrypoint for KPS Decision Answer Gate."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def add_src_to_path() -> None:
    current = Path(__file__).resolve()
    plugin_root = current.parents[1]
    sys.path.insert(0, str(plugin_root))


add_src_to_path()

from kps_decision_answer_gate.gate import (  # noqa: E402
    SEVERITY_ORDER,
    evaluate_path,
    has_findings_at_or_above,
    render_json,
    render_markdown,
)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect Markdown/JSON draft answers with KPS Decision Answer Gate."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser("check", help="Check one file or a directory of fixtures.")
    check.add_argument("path", help="Markdown/JSON file or directory to inspect.")
    check.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Output format. Defaults to markdown.",
    )
    check.add_argument(
        "--fail-on",
        choices=tuple(SEVERITY_ORDER.keys()),
        help="Exit with code 2 when findings at this severity or higher exist.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    results = evaluate_path(args.path)
    if args.format == "json":
        print(render_json(results))
    else:
        print(render_markdown(results), end="")

    if args.fail_on and has_findings_at_or_above(results, args.fail_on):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
