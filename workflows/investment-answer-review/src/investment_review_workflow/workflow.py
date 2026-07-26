"""Human-in-the-loop review workflow built on the Investment Answer Gate."""

from __future__ import annotations

import operator
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Annotated, Any, Callable, Literal, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from kps_decision_answer_gate.gate import SEVERITY_ORDER, evaluate_text


Decision = Literal["approve", "edit", "reject"]
Outcome = Literal["ready", "approved_with_findings", "rejected"]
Clock = Callable[[], datetime]


class AuditEvent(TypedDict):
    timestamp: str
    step: str
    detail: dict[str, Any]


class ReviewState(TypedDict, total=False):
    draft: str
    case_type: str
    source: str
    findings: list[dict[str, Any]]
    max_severity: str | None
    status: str
    outcome: Outcome
    decision: Decision | None
    reviewer_note: str
    revision_count: int
    audit_events: Annotated[list[AuditEvent], operator.add]


def build_review_graph(
    *,
    checkpointer: Any | None = None,
    clock: Clock | None = None,
) -> Any:
    """Compile the review workflow with resumable human approval."""
    now = clock or (lambda: datetime.now(UTC))

    def audit(step: str, **detail: Any) -> AuditEvent:
        return {
            "timestamp": now().isoformat(),
            "step": step,
            "detail": detail,
        }

    def inspect_draft(state: ReviewState) -> ReviewState:
        draft = state.get("draft", "").strip()
        if not draft:
            raise ValueError("draft must not be empty")

        result = evaluate_text(
            draft,
            case_type=state.get("case_type", "investment_decision"),
            source=state.get("source", "review-draft.md"),
        )
        findings = [asdict(finding) for finding in result.findings]
        max_severity = _max_severity(findings)
        return {
            "findings": findings,
            "max_severity": max_severity,
            "status": "inspected",
            "decision": None,
            "audit_events": [
                audit(
                    "draft_inspected",
                    findings=len(findings),
                    max_severity=max_severity,
                    revision_count=state.get("revision_count", 0),
                )
            ],
        }

    def prepare_review(state: ReviewState) -> ReviewState:
        return {
            "status": "awaiting_review",
            "audit_events": [
                audit(
                    "human_review_requested",
                    findings=len(state.get("findings", [])),
                    max_severity=state.get("max_severity"),
                    allowed_decisions=["approve", "edit", "reject"],
                )
            ],
        }

    def request_human_review(state: ReviewState) -> ReviewState:
        response = interrupt(
            {
                "kind": "investment_answer_review",
                "message": "검수 결과를 확인하고 승인, 수정 또는 반려해 주세요.",
                "allowed_decisions": ["approve", "edit", "reject"],
                "findings": state.get("findings", []),
                "max_severity": state.get("max_severity"),
                "revision_count": state.get("revision_count", 0),
            }
        )
        decision, note, edited_draft = _parse_review_response(response)
        update: ReviewState = {
            "decision": decision,
            "reviewer_note": note,
            "status": {
                "approve": "approved_with_findings",
                "edit": "revising",
                "reject": "rejected",
            }[decision],
            "audit_events": [
                audit(
                    "human_decision_recorded",
                    decision=decision,
                    note=note,
                    revision_count=state.get("revision_count", 0),
                )
            ],
        }
        if decision == "edit":
            update["draft"] = edited_draft
            update["revision_count"] = state.get("revision_count", 0) + 1
        elif decision == "approve":
            update["outcome"] = "approved_with_findings"
        else:
            update["outcome"] = "rejected"
        return update

    def mark_ready(state: ReviewState) -> ReviewState:
        return {
            "status": "ready",
            "outcome": "ready",
            "audit_events": [
                audit(
                    "draft_ready",
                    revision_count=state.get("revision_count", 0),
                )
            ],
        }

    def finalize(state: ReviewState) -> ReviewState:
        outcome = state.get("outcome", "ready")
        return {
            "status": "completed",
            "audit_events": [
                audit(
                    "review_completed",
                    outcome=outcome,
                    findings=len(state.get("findings", [])),
                    revision_count=state.get("revision_count", 0),
                )
            ],
        }

    builder = StateGraph(ReviewState)
    builder.add_node("inspect_draft", inspect_draft)
    builder.add_node("prepare_review", prepare_review)
    builder.add_node("request_human_review", request_human_review)
    builder.add_node("mark_ready", mark_ready)
    builder.add_node("finalize", finalize)

    builder.add_edge(START, "inspect_draft")
    builder.add_conditional_edges(
        "inspect_draft",
        _route_after_inspection,
        {
            "needs_review": "prepare_review",
            "ready": "mark_ready",
        },
    )
    builder.add_edge("prepare_review", "request_human_review")
    builder.add_conditional_edges(
        "request_human_review",
        _route_after_human_review,
        {
            "reinspect": "inspect_draft",
            "finalize": "finalize",
        },
    )
    builder.add_edge("mark_ready", "finalize")
    builder.add_edge("finalize", END)

    return builder.compile(checkpointer=checkpointer or InMemorySaver())


def get_interrupt_payload(result: ReviewState) -> dict[str, Any] | None:
    """Return the first interrupt payload from a graph result, if present."""
    interrupts = result.get("__interrupt__")
    if not interrupts:
        return None
    first = interrupts[0]
    value = getattr(first, "value", first)
    return value if isinstance(value, dict) else {"message": str(value)}


def _route_after_inspection(state: ReviewState) -> str:
    return "needs_review" if state.get("findings") else "ready"


def _route_after_human_review(state: ReviewState) -> str:
    return "reinspect" if state.get("decision") == "edit" else "finalize"


def _max_severity(findings: list[dict[str, Any]]) -> str | None:
    if not findings:
        return None
    return max(
        (str(finding["severity"]) for finding in findings),
        key=lambda severity: SEVERITY_ORDER[severity],
    )


def _parse_review_response(response: Any) -> tuple[Decision, str, str]:
    if isinstance(response, str):
        payload: dict[str, Any] = {"decision": response}
    elif isinstance(response, dict):
        payload = response
    else:
        raise ValueError("review response must be a decision string or object")

    decision = payload.get("decision")
    if decision not in {"approve", "edit", "reject"}:
        raise ValueError("decision must be approve, edit, or reject")

    note = str(payload.get("note", "")).strip()
    edited_draft = str(
        payload.get("edited_draft") or payload.get("draft") or ""
    ).strip()
    if decision == "edit" and not edited_draft:
        raise ValueError("edited_draft is required when decision is edit")
    return decision, note, edited_draft
