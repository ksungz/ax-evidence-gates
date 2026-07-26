#!/usr/bin/env python3
"""Run the investment-answer review workflow from the command line."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from uuid import uuid4


REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_SRC = Path(__file__).resolve().parent
GATE_SRC = REPO_ROOT / "gates" / "investment-answer" / "src"
sys.path.insert(0, str(WORKFLOW_SRC))
sys.path.insert(0, str(GATE_SRC))

from langgraph.types import Command  # noqa: E402

from investment_review_workflow import (  # noqa: E402
    build_review_graph,
    get_interrupt_payload,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a resumable human review for an investment-answer draft."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Inspect and optionally decide a draft")
    run_parser.add_argument("input", type=Path, help="Markdown draft to inspect")
    run_parser.add_argument(
        "--case-type",
        default="investment_decision",
        choices=[
            "investment_decision",
            "order_outage",
            "market_data_delay",
            "fractional_order",
        ],
    )
    run_parser.add_argument(
        "--decision",
        choices=["approve", "edit", "reject"],
        help="Decision to apply if the workflow pauses",
    )
    run_parser.add_argument(
        "--edited-file",
        type=Path,
        help="Replacement draft required for --decision edit",
    )
    run_parser.add_argument("--note", default="", help="Reviewer note")
    run_parser.add_argument(
        "--audit-out",
        type=Path,
        help="Write the final audit record as JSON",
    )

    subparsers.add_parser("diagram", help="Print the workflow as Mermaid")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    graph = build_review_graph()

    if args.command == "diagram":
        print(graph.get_graph().draw_mermaid())
        return 0

    draft = args.input.read_text(encoding="utf-8")
    config = {"configurable": {"thread_id": f"cli-{uuid4()}"}}
    result = graph.invoke(
        {
            "draft": draft,
            "case_type": args.case_type,
            "source": str(args.input),
            "revision_count": 0,
            "audit_events": [],
        },
        config=config,
    )
    _print_summary(result)

    pending = get_interrupt_payload(result)
    if pending is not None:
        if not args.decision:
            print("\nDecision required: rerun with --decision approve|edit|reject.")
            return 2

        response: dict[str, str] = {
            "decision": args.decision,
            "note": args.note,
        }
        if args.decision == "edit":
            if not args.edited_file:
                raise SystemExit("--edited-file is required with --decision edit")
            response["edited_draft"] = args.edited_file.read_text(encoding="utf-8")

        result = graph.invoke(Command(resume=response), config=config)
        _print_summary(result)

    if args.audit_out:
        args.audit_out.parent.mkdir(parents=True, exist_ok=True)
        args.audit_out.write_text(
            json.dumps(
                {
                    "status": result.get("status"),
                    "outcome": result.get("outcome"),
                    "decision": result.get("decision"),
                    "revision_count": result.get("revision_count", 0),
                    "findings": result.get("findings", []),
                    "audit_events": result.get("audit_events", []),
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"Audit written: {args.audit_out}")

    return 0


def _print_summary(result: dict[str, object]) -> None:
    findings = result.get("findings", [])
    print(
        json.dumps(
            {
                "status": result.get("status"),
                "outcome": result.get("outcome"),
                "decision": result.get("decision"),
                "revision_count": result.get("revision_count", 0),
                "findings": len(findings) if isinstance(findings, list) else 0,
                "max_severity": result.get("max_severity"),
                "waiting_for_human": get_interrupt_payload(result) is not None,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
