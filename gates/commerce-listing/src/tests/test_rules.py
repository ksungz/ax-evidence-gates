import copy
import json
import sys
import unittest
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from listing_preflight.judgment import run_judgment_hints
from listing_preflight.rules import run_rules


class RuleEngineTest(unittest.TestCase):
    def setUp(self):
        self.ok = json.loads((SRC_DIR / "examples" / "01-ok.json").read_text(encoding="utf-8"))

    def test_ok_sample_has_no_deterministic_findings(self):
        self.assertEqual(run_rules(copy.deepcopy(self.ok)), [])

    def test_required_field_missing_is_a_finding(self):
        data = copy.deepcopy(self.ok)
        del data["description"]
        self.assertRuleIds(run_rules(data), ["REQUIRED-FIELD-MISSING"])

    def test_gosi_material_percent_missing(self):
        data = copy.deepcopy(self.ok)
        data["disclosure"]["material"] = "면 폴리에스터 혼방"
        self.assertRuleIds(run_rules(data), ["GOSI-MATERIAL-PERCENT-MISSING"])

    def test_gosi_disclosure_field_missing(self):
        data = copy.deepcopy(self.ok)
        del data["disclosure"]["manufactured_at"]
        self.assertRuleIds(run_rules(data), ["GOSI-CLOTHING-07-MISSING"])

    def test_size_unit_and_inversion_rules(self):
        data = json.loads((SRC_DIR / "examples" / "04-size-anomaly.json").read_text(encoding="utf-8"))
        self.assertRuleIds(run_rules(data), ["SIZE-UNIT-SUSPECT", "SIZE-ORDER-INVERSION"])

    def test_size_measurement_missing(self):
        data = copy.deepcopy(self.ok)
        del data["size_chart"][0]["chest_width_cm"]
        self.assertRuleIds(run_rules(data), ["SIZE-MEASUREMENT-MISSING"])

    def test_judgment_attr_gap_terms(self):
        data = json.loads((SRC_DIR / "examples" / "02-attr-gap.json").read_text(encoding="utf-8"))
        self.assertRuleIds(
            run_judgment_hints(data),
            ["TERM-CLUSTER-PUFFER", "ATTR-GAP-LENGTH", "ATTR-GAP-NECKLINE"],
        )

    def test_judgment_mixed_neckline(self):
        data = copy.deepcopy(self.ok)
        data["product_name"] = "U넥 베이직 티셔츠"
        data["description"] = "라운드넥으로도 표현되는 넥라인 샘플입니다."
        self.assertRuleIds(run_judgment_hints(data), ["TERM-MIXED-NECKLINE"])

    def test_judgment_midi_measurement_request(self):
        data = copy.deepcopy(self.ok)
        data["product_name"] = "미디 기장 니트 탑"
        data["description"] = "기장 표현을 실측으로 확인해야 하는 샘플입니다."
        self.assertRuleIds(run_judgment_hints(data), ["TERM-MIDI-MEASUREMENT-REQUEST"])

    def test_judgment_tag_mismatch(self):
        data = json.loads((SRC_DIR / "examples" / "03-tag-mismatch.json").read_text(encoding="utf-8"))
        self.assertRuleIds(run_judgment_hints(data), ["TAG-MISMATCH-SWEATSHIRT"])

    def assertRuleIds(self, findings, expected):
        self.assertEqual([finding["rule_id"] for finding in findings], expected)


if __name__ == "__main__":
    unittest.main()
