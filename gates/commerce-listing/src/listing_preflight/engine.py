"""Preflight report generation."""

from __future__ import annotations

from pathlib import Path

from .input_schema import load_listing
from .judgment import run_judgment_hints
from .report_schema import validate_report
from .rules import run_rules


def run_preflight(path, include_judgment=True):
    data = load_listing(path)
    findings = run_rules(data)
    if include_judgment:
        findings.extend(run_judgment_hints(data))
    report = build_report(path, findings)
    validate_report(report)
    return report


def build_report(path, findings):
    counts = {
        "error_count": sum(1 for finding in findings if finding["severity"] == "error"),
        "warning_count": sum(1 for finding in findings if finding["severity"] == "warning"),
        "info_count": sum(1 for finding in findings if finding["severity"] == "info"),
    }
    return {
        "schema_version": "1.0.0",
        "tool": "listing-preflight",
        "input_file": str(Path(path)),
        "status": "pass" if not findings else "fail",
        "summary": {
            "finding_count": len(findings),
            **counts,
        },
        "findings": findings,
    }
