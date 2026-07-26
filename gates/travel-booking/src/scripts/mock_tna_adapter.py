#!/usr/bin/env python3
"""Return synthetic MyRealTrip TNA fixture data by documented endpoint group."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ENDPOINT_KEYS = {
    "search": "tnaSearch",
    "detail": "tnaDetail",
    "options": "tnaOptions",
    "calendars": "tnaCalendars",
}


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", default="fixtures/synthetic_tna_evidence.json")
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--endpoint", choices=sorted(ENDPOINT_KEYS), required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    fixture = load_json(args.evidence)
    key = ENDPOINT_KEYS[args.endpoint]
    for case in fixture.get("cases", []):
        if case.get("caseId") == args.case_id:
            if key not in case:
                raise SystemExit(f"case does not include {key}")
            print(json.dumps(case[key], ensure_ascii=False, indent=2))
            return 0
    raise SystemExit(f"unknown caseId: {args.case_id}")


if __name__ == "__main__":
    raise SystemExit(main())
