import json
import sys
import unittest
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from listing_preflight.engine import run_preflight


class ExampleSnapshotTest(unittest.TestCase):
    def test_examples_match_expected_findings_exactly(self):
        example_dir = SRC_DIR / "examples"
        expected = json.loads((example_dir / "expected-findings.json").read_text(encoding="utf-8"))

        for filename, expected_rule_ids in expected.items():
            with self.subTest(filename=filename):
                report = run_preflight(example_dir / filename)
                actual_rule_ids = [finding["rule_id"] for finding in report["findings"]]
                self.assertEqual(actual_rule_ids, expected_rule_ids)


if __name__ == "__main__":
    unittest.main()
