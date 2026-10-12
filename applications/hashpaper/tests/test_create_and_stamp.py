"""Regression tests for HashPaper creating and timestamping in one operation."""

from contextlib import redirect_stderr, redirect_stdout
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hashpaper.cli import main


class HashPaperCreateAndStampTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir()
        self.fake_ots = self.bin_dir / "ots"
        self.fake_ots.write_text(
            "#!/usr/bin/env python3\\n"
            "import os, pathlib, sys\\n"
            "args = sys.argv[1:]\\n"
            "if not args or args[0] != 'stamp': sys.exit(2)\\n"
            "if os.environ.get('FAKE_OTS_FAIL') == '1':\\n"
            "    print('synthetic calendar unavailable', file=sys.stderr)\\n"
            "    sys.exit(7)\\n"
            "pathlib.Path(args[1] + '.ots').write_bytes(b'synthetic proof')\\n"
            "print('Submitting to remote calendar https://calendar.example')\\n"
            ,
            encoding="utf-8",
        )
        self.fake_ots.chmod(0o755)
        self.old_path = os.environ.get("PATH", "")
        self.old_data_dir = os.environ.get("NODE_CORE_DATA_DIR")
        self.old_fail = os.environ.get("FAKE_OTS_FAIL")
        os.environ["PATH"] = str(self.bin_dir) + os.pathsep + self.old_path
        os.environ["NODE_CORE_DATA_DIR"] = str(self.root / "node-core-data")
        os.environ.pop("FAKE_OTS_FAIL", None)

    def tearDown(self):
        os.environ["PATH"] = self.old_path
        if self.old_data_dir is None:
            os.environ.pop("NODE_CORE_DATA_DIR", None)
        else:
            os.environ["NODE_CORE_DATA_DIR"] = self.old_data_dir
        if self.old_fail is None:
            os.environ.pop("FAKE_OTS_FAIL", None)
        else:
            os.environ["FAKE_OTS_FAIL"] = self.old_fail
        self.temporary.cleanup()

    def test_create_also_submits_same_original_to_opentimestamps(self):
        original = self.root / "created.md"
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            status = main(["create", "--output", str(original), "--title", "Synthetic", "--text", "Synthetic body"])
        proof = Path(str(original) + ".ots")
        self.assertEqual(status, 0)
        self.assertEqual(original.read_text(encoding="utf-8"), "# Synthetic\\n\\nSynthetic body\\n")
        self.assertEqual(proof.read_bytes(), b"synthetic proof")
        self.assertIn("OpenTimestamps status: WAITING_FOR_BITCOIN", stdout.getvalue())
        self.assertIn("not proof of Bitcoin confirmation", stdout.getvalue())

    def test_original_is_preserved_when_timestamp_submission_fails(self):
        original = self.root / "created-failure.md"
        stderr = io.StringIO()
        os.environ["FAKE_OTS_FAIL"] = "1"
        with redirect_stderr(stderr):
            status = main(["create", "--output", str(original), "--title", "Synthetic", "--text", "Keep this original"])
        self.assertEqual(status, 1)
        self.assertTrue(original.is_file())
        self.assertIn("Keep this original", original.read_text(encoding="utf-8"))
        self.assertFalse(Path(str(original) + ".ots").exists())
        self.assertIn("original was preserved", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
