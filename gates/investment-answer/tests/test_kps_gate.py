from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
EXAMPLES = SRC / "examples"
sys.path.insert(0, str(SRC))

from kps_decision_answer_gate.gate import evaluate_file, evaluate_path, render_json  # noqa: E402


class KpsGateTests(unittest.TestCase):
    def test_bad_answer_flags_core_quality_risks(self) -> None:
        result = evaluate_file(EXAMPLES / "bad-answer.md")
        categories = {finding.category for finding in result.findings}

        self.assertIn("unsafe_investment_language", categories)
        self.assertIn("missing_user_context", categories)
        self.assertIn("evidence_url_missing", categories)
        self.assertIn("missing_risk_or_limit", categories)
        self.assertTrue(any(finding.severity == "high" for finding in result.findings))

    def test_better_answer_has_no_findings(self) -> None:
        result = evaluate_file(EXAMPLES / "better-answer.md")
        self.assertEqual([], result.findings)

    def test_json_evidence_entry_requires_public_url(self) -> None:
        result = evaluate_file(EXAMPLES / "json-missing-evidence.json")
        self.assertTrue(
            any(finding.category == "evidence_url_missing" for finding in result.findings),
            result.findings,
        )
        self.assertTrue(
            any("evidence[0]" in finding.location for finding in result.findings),
            result.findings,
        )

    def test_financial_safety_expression_detection(self) -> None:
        result = evaluate_file(EXAMPLES / "bad-answer.md")
        matches = [finding.matched_text for finding in result.findings if finding.matched_text]
        joined = "\n".join(matches)

        self.assertIn("지금 매수", joined)
        self.assertTrue("수익이 확실" in joined or "확실" in joined)

    def test_all_findings_include_required_review_fields(self) -> None:
        results = evaluate_path(EXAMPLES)
        findings = [finding for result in results for finding in result.findings]
        self.assertGreater(len(findings), 0)

        for finding in findings:
            self.assertTrue(finding.evidence_id, finding)
            self.assertTrue(finding.evidence_url.startswith("https://"), finding)
            self.assertTrue(finding.location, finding)
            self.assertTrue(finding.suggestion, finding)

    def test_advisory_fixtures_emit_case_specific_findings(self) -> None:
        order = evaluate_file(EXAMPLES / "advisory-order-outage.md")
        market = evaluate_file(EXAMPLES / "advisory-market-data-delay.md")
        fractional = evaluate_file(EXAMPLES / "advisory-fractional-order.md")

        self.assertEqual("order_outage", order.case_type)
        self.assertTrue(any("order_outage" in finding.id for finding in order.findings))
        self.assertEqual("market_data_delay", market.case_type)
        self.assertTrue(any("market_data_delay" in finding.id for finding in market.findings))
        self.assertEqual("fractional_order", fractional.case_type)
        self.assertTrue(any("fractional_order" in finding.id for finding in fractional.findings))

    def test_json_renderer_is_machine_readable(self) -> None:
        payload = json.loads(render_json([evaluate_file(EXAMPLES / "bad-answer.md")]))
        self.assertEqual("kps-decision-answer-gate", payload["tool"])
        self.assertGreater(payload["summary"]["findings"], 0)


if __name__ == "__main__":
    unittest.main()
