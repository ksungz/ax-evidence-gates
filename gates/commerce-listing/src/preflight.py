#!/usr/bin/env python3
"""CLI for listing-preflight."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from listing_preflight.engine import run_preflight
from listing_preflight.input_schema import InputError
from listing_preflight.schema_validator import SchemaValidationError


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run listing-preflight on listing JSON files.")
    parser.add_argument("inputs", nargs="+", help="Listing JSON file(s)")
    parser.add_argument("--out", help="Write a single report to this path")
    parser.add_argument("--reports-dir", help="Write one report per input into this directory")
    parser.add_argument(
        "--deterministic-only",
        action="store_true",
        help="Skip the evidence-limited Codex judgment hints.",
    )
    args = parser.parse_args(argv)

    if args.out and len(args.inputs) != 1:
        parser.error("--out can only be used with one input")

    output_dir = Path(args.reports_dir) if args.reports_dir else None
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    try:
        for input_path in args.inputs:
            report = run_preflight(input_path, include_judgment=not args.deterministic_only)
            destination = _destination(input_path, args.out, output_dir)
            _write_report(report, destination)
            print(_summary(input_path, report, destination))
    except (InputError, SchemaValidationError) as exc:
        print(f"listing-preflight error: {exc}", file=sys.stderr)
        return 2

    return 0


def _destination(input_path, out, output_dir):
    if out:
        return Path(out)
    if output_dir:
        return output_dir / f"{Path(input_path).stem}.report.json"
    return None


def _write_report(report, destination):
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if destination:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")


def _summary(input_path, report, destination):
    suffix = f" -> {destination}" if destination else ""
    return (
        f"{input_path}: {report['status']} "
        f"({report['summary']['finding_count']} findings){suffix}"
    )


if __name__ == "__main__":
    raise SystemExit(main())
