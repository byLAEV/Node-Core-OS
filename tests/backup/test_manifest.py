import unittest

from node_core.backup.manifest import create_manifest, serialize_manifest


class ManifestTests(unittest.TestCase):
    def test_manifest_contains_public_metadata_only(self) -> None:
        payload = serialize_manifest(
            create_manifest(kubo_version="0.43.1", peer_id="12D3KooW-test", keys=["self"])
        )
        self.assertIn(b"node-core-backup", payload)
        self.assertIn(b"12D3KooW-test", payload)
        self.assertNotIn(b"private_key", payload)
        self.assertNotIn(b"pinata", payload.lower())


if __name__ == "__main__":
    unittest.main()
