#!/usr/bin/env python3
"""Unit tests for official stable-release metadata validation."""
from __future__ import annotations

import importlib.util
import pathlib
import unittest

SERVER = pathlib.Path(__file__).with_name("server.py")
SPEC = importlib.util.spec_from_file_location("node_core_lobby_server", SERVER)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def release_payload():
    install_hash = "a" * 64
    update_hash = "b" * 64
    install_name = "node-core-os-install-1.5.6.tar.gz"
    update_name = "node-core-os-update-1.5.6.tar.gz"
    body = (
        f"Installer: {install_name}\nSHA-256: {install_hash}\n\n"
        f"Updater: {update_name}\nSHA-256: {update_hash}\n"
    )
    return {
        "draft": False,
        "prerelease": False,
        "tag_name": "v1.5.6",
        "name": "Node Core OS 1.5.6",
        "published_at": "2026-11-07T01:52:38Z",
        "html_url": "https://github.com/byLAEV/Node-Core-OS/releases/tag/v1.5.6",
        "target_commitish": "0" * 40,
        "body": body,
        "assets": [
            {
                "name": install_name,
                "digest": f"sha256:{install_hash}",
                "size": 1000,
                "browser_download_url": "https://github.com/byLAEV/Node-Core-OS/releases/download/v1.5.6/" + install_name,
            },
            {
                "name": update_name,
                "digest": f"sha256:{update_hash}",
                "size": 1100,
                "browser_download_url": "https://github.com/byLAEV/Node-Core-OS/releases/download/v1.5.6/" + update_name,
            },
        ],
    }


class ReleaseMetadataTests(unittest.TestCase):
    def test_valid_stable_release(self):
        result = MODULE.parse_latest_stable_release(release_payload())
        self.assertEqual(result["version"], "1.5.6")
        self.assertTrue(result["verification"]["stable_release"])
        self.assertEqual(result["assets"]["install"]["sha256"], "a" * 64)
        self.assertEqual(result["assets"]["update"]["sha256"], "b" * 64)
        self.assertFalse(result["verification"]["archive_bytes_downloaded_and_rehashed"])

    def test_rejects_prerelease(self):
        payload = release_payload()
        payload["prerelease"] = True
        with self.assertRaisesRegex(ValueError, "stable"):
            MODULE.parse_latest_stable_release(payload)

    def test_rejects_draft(self):
        payload = release_payload()
        payload["draft"] = True
        with self.assertRaisesRegex(ValueError, "stable"):
            MODULE.parse_latest_stable_release(payload)

    def test_rejects_non_semver_tag(self):
        payload = release_payload()
        payload["tag_name"] = "v1.5.7-rc1"
        with self.assertRaisesRegex(ValueError, "semantic version"):
            MODULE.parse_latest_stable_release(payload)

    def test_rejects_missing_update_package(self):
        payload = release_payload()
        payload["assets"].pop()
        with self.assertRaisesRegex(ValueError, "exactly"):
            MODULE.parse_latest_stable_release(payload)

    def test_rejects_digest_mismatch_with_release_notes(self):
        payload = release_payload()
        payload["body"] = payload["body"].replace("a" * 64, "c" * 64, 1)
        with self.assertRaisesRegex(ValueError, "SHA-256 notes"):
            MODULE.parse_latest_stable_release(payload)

    def test_rejects_non_official_download_host(self):
        payload = release_payload()
        payload["assets"][0]["browser_download_url"] = "https://evil.example/file.tar.gz"
        with self.assertRaisesRegex(ValueError, "metadata is invalid"):
            MODULE.parse_latest_stable_release(payload)


if __name__ == "__main__":
    unittest.main(verbosity=2)
