import csv
import tempfile
import unittest
from pathlib import Path
from validate_global_mapping import URL_RE, read_csv

class GlobalMappingValidatorTests(unittest.TestCase):
    def test_https_url_is_accepted(self):
        self.assertIsNotNone(URL_RE.match("https://example.gov/identity"))

    def test_non_http_scheme_is_rejected(self):
        self.assertIsNone(URL_RE.match("file:///etc/passwd"))

    def test_whitespace_in_url_is_rejected(self):
        self.assertIsNone(URL_RE.match("https://example.gov/a b"))

    def test_csv_reader_preserves_quoted_commas(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.csv"
            path.write_text('id,description\\n1,"civil registration, identity"\\n', encoding="utf-8")
            _, rows = read_csv(path)
            self.assertEqual(rows[0]["description"], "civil registration, identity")

if __name__ == "__main__":
    unittest.main()
