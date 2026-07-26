from __future__ import annotations

import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_SRC = Path(__file__).resolve().parents[1] / "src"
GATE_SRC = REPO_ROOT / "gates" / "investment-answer" / "src"
EXAMPLES = GATE_SRC / "examples"
sys.path.insert(0, str(WORKFLOW_SRC))
sys.path.insert(0, str(GATE_SRC))

from langgraph.types import Command  # noqa: E402

from investment_review_workflow import (  # noqa: E402
    build_review_graph,
    get_interrupt_payload,
)


FIXED_TIME = datetime(2026, 7, 27, 0, 0, tzinfo=UTC)


class InvestmentAnswerReviewWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.graph = build_review_graph(clock=lambda: FIXED_TIME)

    def test_safe_draft_completes_without_human_review(self) -> None:
        result = self._start("better-answer.md", thread_id="safe")

        self.assertEqual("completed", result["status"])
        self.assertEqual("ready", result["outcome"])
        self.assertEqual([], result["findings"])
        self.assertIsNone(get_interrupt_payload(result))

    def test_risky_draft_pauses_for_human_review(self) -> None:
        result = self._start("bad-answer.md", thread_id="pause")

        self.assertEqual("awaiting_review", result["status"])
        self.assertTrue(result["findings"])
        payload = get_interrupt_payload(result)
        self.assertIsNotNone(payload)
        self.assertEqual(
            ["approve", "edit", "reject"],
            payload["allowed_decisions"],
        )

    def test_reviewer_can_approve_with_findings(self) -> None:
        config = {"configurable": {"thread_id": "approve"}}
        self._start("bad-answer.md", config=config)
        result = self.graph.invoke(
            Command(resume={"decision": "approve", "note": "예외 승인"}),
            config=config,
        )

        self.assertEqual("completed", result["status"])
        self.assertEqual("approved_with_findings", result["outcome"])
        self.assertEqual("approve", result["decision"])
        self.assertEqual("예외 승인", result["reviewer_note"])

    def test_reviewer_can_reject(self) -> None:
        config = {"configurable": {"thread_id": "reject"}}
        self._start("bad-answer.md", config=config)
        result = self.graph.invoke(
            Command(resume={"decision": "reject", "note": "위험 문구 수정 필요"}),
            config=config,
        )

        self.assertEqual("completed", result["status"])
        self.assertEqual("rejected", result["outcome"])
        self.assertEqual("reject", result["decision"])

    def test_edited_draft_is_reinspected_and_can_pass(self) -> None:
        config = {"configurable": {"thread_id": "edit"}}
        self._start("bad-answer.md", config=config)
        better_draft = (EXAMPLES / "better-answer.md").read_text(encoding="utf-8")
        result = self.graph.invoke(
            Command(
                resume={
                    "decision": "edit",
                    "note": "공개 근거와 위험 설명 추가",
                    "edited_draft": better_draft,
                }
            ),
            config=config,
        )

        self.assertEqual("completed", result["status"])
        self.assertEqual("ready", result["outcome"])
        self.assertEqual(1, result["revision_count"])
        self.assertEqual([], result["findings"])
        inspected_events = [
            event
            for event in result["audit_events"]
            if event["step"] == "draft_inspected"
        ]
        self.assertEqual(2, len(inspected_events))

    def _start(
        self,
        filename: str,
        *,
        thread_id: str | None = None,
        config: dict[str, dict[str, str]] | None = None,
    ) -> dict[str, object]:
        resolved_config = config or {
            "configurable": {"thread_id": thread_id or filename}
        }
        draft = (EXAMPLES / filename).read_text(encoding="utf-8")
        return self.graph.invoke(
            {
                "draft": draft,
                "case_type": "investment_decision",
                "source": filename,
                "revision_count": 0,
                "audit_events": [],
            },
            config=resolved_config,
        )


if __name__ == "__main__":
    unittest.main()
