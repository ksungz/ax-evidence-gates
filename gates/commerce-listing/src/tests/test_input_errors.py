import json
import sys
import tempfile
import unittest
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from listing_preflight.input_schema import InputError, load_listing


class InputErrorTest(unittest.TestCase):
    def test_empty_file_has_clear_error(self):
        path = self._write_text("")
        with self.assertRaisesRegex(InputError, "empty input file"):
            load_listing(path)

    def test_unknown_top_level_field_has_clear_error(self):
        path = self._write_json({"product_name": "샘플", "price": 10000})
        with self.assertRaisesRegex(InputError, "unknown field at root: price"):
            load_listing(path)

    def test_type_error_has_clear_error(self):
        path = self._write_json({"tags": "후드티셔츠"})
        with self.assertRaisesRegex(InputError, "tags must be an array"):
            load_listing(path)

    def _write_json(self, payload):
        return self._write_text(json.dumps(payload, ensure_ascii=False))

    def _write_text(self, text):
        handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".json")
        with handle:
            handle.write(text)
        self.addCleanup(lambda: Path(handle.name).unlink(missing_ok=True))
        return handle.name


if __name__ == "__main__":
    unittest.main()
