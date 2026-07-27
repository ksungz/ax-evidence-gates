"""integration_lint의 규칙 검출을 예시 파일로 검증한다.

실행 (플러그인 루트 src/ 에서):
    python3 -m unittest tests.test_integration_lint -v
"""

import sys
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SRC / "scripts"))

import integration_lint  # noqa: E402

BAD = SRC / "examples" / "bad_integration.py"
GOOD = SRC / "examples" / "good_integration.py"


def run_lint(path):
    rules, _ = integration_lint.load_rules()
    content = path.read_text(encoding="utf-8")
    return integration_lint.check_file(path, content, rules)


class BadExampleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.findings = run_lint(BAD)
        cls.rule_ids = {f["rule"] for f in cls.findings}

    def test_tna_zero_based_page_detected(self):
        self.assertIn("tna-pagination-zero-based", self.rule_ids)

    def test_tna_size_field_mixup_detected(self):
        self.assertIn("tna-pagination-field-mixup", self.rule_ids)

    def test_city_code_trap_detected(self):
        self.assertIn("airport-code-trap", self.rule_ids)

    def test_mylink_length_unchecked_detected(self):
        self.assertIn("mylink-length-unchecked", self.rule_ids)

    def test_pagesize_over_300_detected(self):
        self.assertIn("reservations-pagesize-over-300", self.rule_ids)

    def test_missing_rate_limit_retry_detected(self):
        self.assertIn("missing-429-retry", self.rule_ids)

    def test_bearer_prefix_missing_detected(self):
        self.assertIn("bearer-prefix-missing", self.rule_ids)

    def test_hardcoded_key_detected(self):
        self.assertIn("hardcoded-api-key", self.rule_ids)

    def test_reservations_lookback_info_present(self):
        self.assertIn("reservations-lookback-window", self.rule_ids)

    def test_every_finding_carries_doc_quote(self):
        for f in self.findings:
            self.assertTrue(f["docQuote"].strip(), f"docQuote 누락: {f['rule']}")

    def test_exit_code_is_error(self):
        exit_code = integration_lint.main([str(BAD), "--format", "json"])
        self.assertEqual(exit_code, 1)


class GoodExampleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.findings = run_lint(GOOD)

    def test_no_findings_on_good_example(self):
        self.assertEqual(
            [], self.findings,
            f"good 예시에서 오검출: {[f['rule'] for f in self.findings]}",
        )

    def test_exit_code_is_clean(self):
        exit_code = integration_lint.main([str(GOOD), "--format", "json"])
        self.assertEqual(exit_code, 0)


class RuleRegistryTest(unittest.TestCase):
    def test_registry_loads_and_has_ten_rules(self):
        rules, source = integration_lint.load_rules()
        self.assertEqual(len(rules), 10)
        self.assertIn("docs.myrealtrip.com", source)


if __name__ == "__main__":
    unittest.main()
