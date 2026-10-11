"""Tests for HashPaper's OpenTimestamps CLI adapter using a fake client."""

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hashpaper.timestamp import OpenTimestampsClient, TimestampError


class OpenTimestampsClientTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir()
        self.original_path = self.root / "document-001.md"
        self.original_path.write_text("Synthetic document\n", encoding="utf-8")
        self.fake_ots = self.bin_dir / "ots"
        self.fake_ots.write_text(
            "#!/usr/bin/env python3\n"
            "import pathlib, sys\n"
            "args = sys.argv[1:]\n"
            "if args[0] == 'stamp':\n"
            "    source = pathlib.Path(args[1])\n"
            "    pathlib.Path(str(source) + '.ots').write_bytes(b'fake-proof')\n"
            "    print('Submitting to remote calendar https://calendar.example')\n"
            "elif args[0] == 'verify':\n"
            "    if 'verified' in pathlib.Path(args[1]).read_bytes().decode('latin1'):\n"
            "        print('Success! Bitcoin block 123456 attests existence as of test time')\n"
            "    else:\n"
            "        print('Calendar https://calendar.example: Pending confirmation in Bitcoin blockchain')\n"
            "elif args[0] == 'upgrade':\n"
            "    proof = pathlib.Path(args[1])\n"
            "    proof.write_bytes(b'fake-proof-verified')\n"
            "    print('Success! Timestamp is complete')\n"
            "else:\n"
            "    sys.exit(2)\n",
            encoding="utf-8",
        )
        self.fake_ots.chmod(0o755)
        self.old_path = os.environ.get("PATH", "")
        os.environ["PATH"] = str(self.bin_dir) + os.pathsep + self.old_path

    def tearDown(self):
        os.environ["PATH"] = self.old_path
        self.temporary.cleanup()

    def test_stamp_creates_proof_and_preserves_original(self):
        original_bytes = self.original_path.read_bytes()
        result = OpenTimestampsClient().stamp(self.original_path)
        self.assertEqual(result.status, "WAITING_FOR_BITCOIN")
        self.assertEqual(result.proof_verification, "NOT_VERIFIED")
        self.assertTrue(Path(result.proof_file).is_file())
        self.assertEqual(self.original_path.read_bytes(), original_bytes)

    def test_stamp_refuses_to_overwrite_existing_proof(self):
        Path(str(self.original_path) + ".ots").write_bytes(b"existing")
        with self.assertRaises(TimestampError):
            OpenTimestampsClient().stamp(self.original_path)
        self.assertEqual(Path(str(self.original_path) + ".ots").read_bytes(), b"existing")

    def test_check_distinguishes_pending_from_verified(self):
        proof = Path(str(self.original_path) + ".ots")
        proof.write_bytes(b"fake-proof")
        client = OpenTimestampsClient()
        pending = client.check(self.original_path)
        self.assertEqual(pending.status, "WAITING_FOR_BITCOIN")
        self.assertEqual(pending.proof_verification, "PENDING")
        proof.write_bytes(b"fake-proof-verified")
        verified = client.check(self.original_path)
        self.assertEqual(verified.status, "VERIFIED")
        self.assertEqual(verified.proof_verification, "SUCCESS")
        self.assertEqual(verified.bitcoin_block_height, 123456)

    def test_upgrade_keeps_backup_if_proof_changes(self):
        proof = Path(str(self.original_path) + ".ots")
        proof.write_bytes(b"fake-proof")
        result = OpenTimestampsClient().check(self.original_path, upgrade=True)
        self.assertEqual(result.status, "ANCHOR_AVAILABLE")
        self.assertTrue(Path(str(proof) + ".before-upgrade").is_file())
        self.assertEqual(proof.read_bytes(), b"fake-proof-verified")

    def test_interrupted_upgrade_keeps_backup_if_proof_changed(self):
        proof = Path(str(self.original_path) + ".ots")
        original_proof = b"proof-before-interrupted-upgrade"
        proof.write_bytes(original_proof)
        client = OpenTimestampsClient()

        def fail_after_modifying_proof(args):
            proof.write_bytes(b"partially-upgraded-proof")
            raise TimestampError("synthetic interrupted upgrade")

        client._run = fail_after_modifying_proof
        with self.assertRaises(TimestampError):
            client.check(self.original_path, upgrade=True)

        backup = Path(str(proof) + ".before-upgrade")
        self.assertTrue(backup.is_file())
        self.assertEqual(backup.read_bytes(), original_proof)
        self.assertEqual(proof.read_bytes(), b"partially-upgraded-proof")

    def test_private_node_core_environment_is_discovered_without_path_entry(self):
        private_bin = self.root / "runtime" / "opentimestamps-venv" / "bin"
        private_bin.mkdir(parents=True)
        private_ots = private_bin / "ots"
        private_ots.write_text("#!/bin/sh\\nexit 0\\n", encoding="utf-8")
        private_ots.chmod(0o755)
        old_data_dir = os.environ.get("NODE_CORE_DATA_DIR")
        old_path = os.environ.get("PATH", "")
        try:
            os.environ["NODE_CORE_DATA_DIR"] = str(self.root)
            os.environ["PATH"] = str(self.root / "empty-path")
            resolved = OpenTimestampsClient()._executable_path()
            self.assertEqual(resolved, str(private_ots))
        finally:
            os.environ["PATH"] = old_path
            if old_data_dir is None:
                os.environ.pop("NODE_CORE_DATA_DIR", None)
            else:
                os.environ["NODE_CORE_DATA_DIR"] = old_data_dir

    def test_missing_client_is_reported(self):
        client = OpenTimestampsClient(executable="hashpaper-ots-does-not-exist")
        with self.assertRaises(TimestampError):
            client.stamp(self.original_path)


if __name__ == "__main__":
    unittest.main()
