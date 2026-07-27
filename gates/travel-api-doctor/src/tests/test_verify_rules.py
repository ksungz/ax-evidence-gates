"""verify_rules의 규칙 인용 검증을 로컬 텍스트로 검증한다."""

import html
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SRC / "scripts"))

import verify_rules  # noqa: E402


class VerifyRulesTest(unittest.TestCase):
    def test_rule_file_loads(self):
        rules = verify_rules.load_rules()
        self.assertEqual(len(rules), 10)
        self.assertEqual(rules[0]["id"], "tna-pagination-zero-based")

    def test_every_rule_has_doc_quote(self):
        for rule in verify_rules.load_rules():
            self.assertTrue(rule.get("docQuote", "").strip(), rule["id"])

    def test_quotes_found_after_html_and_whitespace_normalization(self):
        rules = verify_rules.load_rules()
        rendered_quotes = []
        for rule in rules:
            quote = html.escape(rule["docQuote"])
            quote = quote.replace("page", "<code>page</code>", 1)
            quote = quote.replace("perPage", "<strong>perPage</strong>", 1)
            rendered_quotes.append(f"<p>\n  {quote}\n</p>")

        document_text = "<main>" + "\n".join(rendered_quotes) + "</main>"
        results = verify_rules.verify_quotes(rules, document_text)

        self.assertTrue(all(result.ok for result in results))

    def test_missing_quote_is_reported_as_failure(self):
        rules = [
            {"id": "present", "title": "있는 인용문", "docQuote": "공개 문서의 문장입니다."},
            {"id": "missing", "title": "없는 인용문", "docQuote": "문서에서 사라진 문장입니다."},
        ]
        results = verify_rules.verify_quotes(rules, "공개 문서의 문장입니다.")

        self.assertTrue(results[0].ok)
        self.assertFalse(results[1].ok)

    def test_main_returns_failure_for_missing_quote_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            rules_path = tmp_path / "rules.json"
            doc_path = tmp_path / "docs.txt"
            rules_path.write_text(
                json.dumps(
                    {
                        "rules": [
                            {
                                "id": "missing",
                                "title": "없는 인용문",
                                "docQuote": "스냅샷에 없는 문장입니다.",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            doc_path.write_text("다른 문장만 있습니다.", encoding="utf-8")

            stdout = StringIO()
            stderr = StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = verify_rules.main(
                    ["--rules", str(rules_path), "--document-text", str(doc_path)]
                )

        self.assertEqual(exit_code, 1)
        self.assertIn("[FAIL] missing", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
