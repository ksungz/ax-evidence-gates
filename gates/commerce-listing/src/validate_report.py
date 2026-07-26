#!/usr/bin/env python3
"""Validate listing-preflight report JSON files."""

from __future__ import annotations

import argparse
import json
import sys

from listing_preflight.report_schema import validate_report
from listing_preflight.schema_validator import SchemaValidationError


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate listing-preflight report JSON.")
    parser.add_argument("reports", nargs="+", help="Report JSON files")
    args = parser.parse_args(argv)

    failed = False
    for report_path in args.reports:
        try:
            with open(report_path, encoding="utf-8") as handle:
                report = json.load(handle)
            validate_report(report)
            print(f"{report_path}: OK")
        except (OSError, json.JSONDecodeError, SchemaValidationError) as exc:
            failed = True
            print(f"{report_path}: INVALID: {exc}", file=sys.stderr)

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
