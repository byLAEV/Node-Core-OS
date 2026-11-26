import json
from pathlib import Path
import tempfile
import unittest

from applications.p2p_contracts.p2p_contracts.genesis import (
    GENESIS_HASH, content_hash, load_genesis, next_propagation_hash,
)


class GenesisManifestTests(unittest.TestCase):
    def test_bundled_genesis_manifest_is_valid(self):
        manifest = load_genesis()
        self.assertEqual(manifest["genesis_hash"], GENESIS_HASH)
        self.assertEqual(manifest["block"], 0)
        self.assertEqual(manifest["status"], "GENESIS_REFERENCE")

    def test_tampered_root_is_rejected(self):
        manifest = load_genesis()
        manifest["genesis_hash"] = "f" * 64
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "genesis.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_genesis(path)

    def test_content_hash_ignores_derived_hash_fields(self):
        payload = {"block": 1, "requests": [], "derived_hashes": {"HL": "a" * 64}}
        altered = {"block": 1, "requests": [], "derived_hashes": {"HL": "b" * 64}}
        self.assertEqual(content_hash(payload), content_hash(altered))

    def test_propagation_hash_uses_binary_hashes(self):
        result = next_propagation_hash(GENESIS_HASH, "1" * 64)
        self.assertEqual(len(result), 64)
        self.assertEqual(result, next_propagation_hash(GENESIS_HASH, "1" * 64))

    def test_invalid_hash_is_rejected(self):
        with self.assertRaises(ValueError):
            next_propagation_hash("not-a-hash", "1" * 64)


if __name__ == "__main__":
    unittest.main()
