"""Report schema loading and validation."""

from __future__ import annotations

import json
from pathlib import Path

from .schema_validator import validate

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "report.schema.json"


def load_report_schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def validate_report(report):
    validate(report, load_report_schema())
