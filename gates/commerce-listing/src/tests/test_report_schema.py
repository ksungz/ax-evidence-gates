import copy
import sys
import unittest
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from listing_preflight.engine import run_preflight
from listing_preflight.report_schema import validate_report
from listing_preflight.schema_validator import SchemaValidationError


class ReportSchemaTest(unittest.TestCase):
    def test_generated_report_validates(self):
        report = run_preflight(SRC_DIR / "examples" / "03-tag-mismatch.json")
        validate_report(report)

    def test_missing_evidence_source_url_fails(self):
        report = run_preflight(SRC_DIR / "examples" / "03-tag-mismatch.json")
        broken = copy.deepcopy(report)
        del broken["findings"][0]["evidence"]["source_url"]

        with self.assertRaisesRegex(SchemaValidationError, "source_url"):
            validate_report(broken)

    def test_empty_evidence_quote_fails(self):
        report = run_preflight(SRC_DIR / "examples" / "03-tag-mismatch.json")
        broken = copy.deepcopy(report)
        broken["findings"][0]["evidence"]["quote"] = ""

        with self.assertRaisesRegex(SchemaValidationError, "minLength"):
            validate_report(broken)


if __name__ == "__main__":
    unittest.main()
