"""Tests for HashPaper's explicit Node Core identity integration."""

import sys
from pathlib import Path
import unittest
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hashpaper.identity import (
    IdentityIntegrationError,
    associate_identity_with_peer,
    load_identity_and_peer_id,
)


class FakeIdentityStore:
    def __init__(self, profile):
        self.profile = profile
        self.associated = []

    def load(self):
        return self.profile

    def associate_node(self, peer_id):
        self.associated.append(peer_id)
        self.profile = dict(self.profile, node_id=peer_id)
        return self.profile


class HashPaperIdentityTests(unittest.TestCase):
    def runtime(self, profile, *, running=True, peer_id="12D3KooW-test"):
        store = FakeIdentityStore(profile)
        kubo = SimpleNamespace(status=lambda: SimpleNamespace(running=running, peer_id=peer_id))
        return SimpleNamespace(identity_profile=store, kubo=kubo)

    def test_requires_existing_profile(self):
        with self.assertRaises(IdentityIntegrationError):
            load_identity_and_peer_id(self.runtime(None))

    def test_requires_live_real_peer_id(self):
        runtime = self.runtime({"identity_id": "synthetic"}, running=False)
        with self.assertRaises(IdentityIntegrationError):
            load_identity_and_peer_id(runtime)

    def test_loads_existing_profile_and_peer_id(self):
        profile = {"identity_id": "synthetic", "node_id": None}
        loaded, peer_id = load_identity_and_peer_id(self.runtime(profile))
        self.assertEqual(loaded["identity_id"], "synthetic")
        self.assertEqual(peer_id, "12D3KooW-test")

    def test_association_is_persisted_only_when_called(self):
        runtime = self.runtime({"identity_id": "synthetic", "node_id": None})
        profile, peer_id = load_identity_and_peer_id(runtime)
        self.assertEqual(runtime.identity_profile.associated, [])
        updated = associate_identity_with_peer(runtime, profile, peer_id)
        self.assertEqual(updated["node_id"], peer_id)
        self.assertEqual(runtime.identity_profile.associated, [peer_id])

    def test_existing_matching_association_is_not_rewritten(self):
        peer_id = "12D3KooW-test"
        runtime = self.runtime({"identity_id": "synthetic", "node_id": peer_id}, peer_id=peer_id)
        profile, actual_peer_id = load_identity_and_peer_id(runtime)
        associate_identity_with_peer(runtime, profile, actual_peer_id)
        self.assertEqual(runtime.identity_profile.associated, [])


if __name__ == "__main__":
    unittest.main()
