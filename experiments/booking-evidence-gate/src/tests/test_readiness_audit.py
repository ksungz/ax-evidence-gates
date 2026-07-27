import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.readiness_audit import audit, format_korean_summary


EVIDENCE = json.loads((ROOT / "fixtures" / "synthetic_tna_evidence.json").read_text(encoding="utf-8"))
POLICY = json.loads((ROOT / "policies" / "claim_policy.json").read_text(encoding="utf-8"))


def run_claim(claim, current_date="2026-04-20"):
    answer = {
        "answerId": "test-answer",
        "currentDate": current_date,
        "claims": [claim],
    }
    return audit(answer, EVIDENCE, POLICY)["verdicts"][0]


class ReadinessAuditTest(unittest.TestCase):
    def test_supported_availability_with_sufficient_evidence(self):
        verdict = run_claim(
            {
                "id": "c1",
                "type": "availability",
                "span": "2026-05-01 예약 가능",
                "caseId": "osaka-rapit-2026-05-01",
                "selectedDate": "2026-05-01",
                "evidence": [
                    {"path": "/tnaOptions/response/data/selectedDate"},
                    {"path": "/tnaOptions/response/data/options/0/id"},
                    {"path": "/tnaCalendars/response/data/blockDates"},
                ],
            }
        )
        self.assertEqual(verdict["verdict"], "SUPPORTED")

    def test_blocked_availability_without_availability_evidence(self):
        verdict = run_claim(
            {
                "id": "c2",
                "type": "availability",
                "span": "2026-05-03 예약 가능",
                "caseId": "osaka-rapit-2026-05-01",
                "selectedDate": "2026-05-03",
                "evidence": [{"path": "/tnaSearch/response/data/items/0/gid"}],
            }
        )
        self.assertEqual(verdict["verdict"], "BLOCKED")
        self.assertTrue(any("selectedDate does not match" in reason for reason in verdict["reasons"]))

    def test_blocked_relative_date_without_current_date(self):
        answer = {
            "answerId": "relative-date-test",
            "claims": [
                {
                    "id": "c3",
                    "type": "relative_date",
                    "span": "내일 예약 가능합니다",
                    "caseId": "osaka-rapit-2026-05-01",
                    "evidence": [],
                }
            ],
        }
        verdict = audit(answer, EVIDENCE, POLICY)["verdicts"][0]
        self.assertEqual(verdict["verdict"], "BLOCKED")

    def test_blocked_search_price_as_final_payment_price(self):
        verdict = run_claim(
            {
                "id": "c4",
                "type": "option_price",
                "span": "최종 결제 가격은 12,657원입니다",
                "caseId": "osaka-rapit-2026-05-01",
                "amount": 12657,
                "currency": "KRW",
                "evidence": [{"path": "/tnaSearch/response/data/items/0/salePrice"}],
            }
        )
        self.assertEqual(verdict["verdict"], "BLOCKED")
        self.assertTrue(any("starting-price" in reason for reason in verdict["reasons"]))

    def test_blocked_cancellation_without_policy_evidence(self):
        verdict = run_claim(
            {
                "id": "c5",
                "type": "cancellation_policy",
                "span": "무료 취소 가능합니다",
                "caseId": "osaka-rapit-2026-05-01",
                "evidence": [],
            }
        )
        self.assertEqual(verdict["verdict"], "BLOCKED")
        self.assertTrue(any("cancellation-policy" in reason for reason in verdict["reasons"]))

    def test_hard_blocked_reservation_or_payment_without_tool_trace(self):
        verdict = run_claim(
            {
                "id": "c6",
                "type": "reservation_or_payment_complete",
                "span": "예약 확정까지 완료되었습니다",
                "caseId": "osaka-rapit-2026-05-01",
                "evidence": [{"path": "/tnaOptions/response/data/options/0/id"}],
            }
        )
        self.assertEqual(verdict["verdict"], "BLOCKED")
        self.assertTrue(any("no reservation or payment tool" in reason for reason in verdict["reasons"]))

    def test_blocked_when_requested_quantity_exceeds_available_purchase_quantity(self):
        verdict = run_claim(
            {
                "id": "c7",
                "type": "availability",
                "span": "2026-05-01 성인 2명 예약 가능",
                "caseId": "osaka-rapit-2026-05-01",
                "selectedDate": "2026-05-01",
                "optionId": 8901234,
                "quantity": 2,
                "evidence": [
                    {"path": "/tnaOptions/response/data/selectedDate"},
                    {"path": "/tnaOptions/response/data/options/0/id"},
                    {"path": "/tnaOptions/response/data/options/0/availablePurchaseQuantity"},
                ],
            }
        )
        self.assertEqual(verdict["verdict"], "BLOCKED")
        self.assertTrue(any("availablePurchaseQuantity" in reason for reason in verdict["reasons"]))

    def test_verdicts_include_claim_span_and_evidence_paths(self):
        result = audit(
            {
                "answerId": "trace-shape-test",
                "currentDate": "2026-04-20",
                "claims": [
                    {
                        "id": "c8",
                        "type": "instant_confirm",
                        "span": "즉시 확정입니다",
                        "caseId": "osaka-rapit-2026-05-01",
                        "evidence": [{"path": "/tnaCalendars/response/data/instantConfirm"}],
                    }
                ],
            },
            EVIDENCE,
            POLICY,
        )
        verdict = result["verdicts"][0]
        self.assertEqual(verdict["span"], "즉시 확정입니다")
        self.assertEqual(verdict["evidencePaths"], ["/tnaCalendars/response/data/instantConfirm"])

    def test_korean_summary_uses_user_facing_blocked_language(self):
        result = audit(
            json.loads((ROOT / "contracts" / "try_in_chat_review.example.json").read_text(encoding="utf-8")),
            EVIDENCE,
            POLICY,
        )
        summary = format_korean_summary(result)
        self.assertIn("전체 판단: 수정 필요", summary)
        self.assertIn("근거 부족 1개", summary)
        self.assertIn("- 근거 부족: 무료 취소도 가능합니다", summary)
        self.assertIn("제공된 근거 데이터에는 취소 정책 근거가 없습니다", summary)
        self.assertNotIn("막아야 함", summary)
        self.assertNotIn("endpoint/field", summary)


if __name__ == "__main__":
    unittest.main()
