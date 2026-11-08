#!/usr/bin/env python3
"""Unit tests for official stable-release metadata validation."""
from __future__ import annotations

import hashlib
import importlib.util
import io
import pathlib
import tempfile
import tarfile
import json
import unittest
from unittest import mock

SERVER = pathlib.Path(__file__).resolve().parents[1] / "lobby" / "server.py"
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


    def test_downloads_and_verifies_package_bytes_atomically(self):
        package_bytes = b"unit-test-release-package"
        payload = release_payload()
        install_name = "node-core-os-install-1.5.6.tar.gz"
        install_asset = payload["assets"][0]
        install_asset["size"] = len(package_bytes)
        install_asset["digest"] = "sha256:" + hashlib.sha256(package_bytes).hexdigest()
        payload["body"] = payload["body"].replace("a" * 64, hashlib.sha256(package_bytes).hexdigest(), 1)
        release = MODULE.parse_latest_stable_release(payload)

        class FakeResponse(io.BytesIO):
            def __enter__(self):
                return self
            def __exit__(self, *args):
                self.close()
            def geturl(self):
                return "https://release-assets.githubusercontent.com/asset"

        with tempfile.TemporaryDirectory() as temp:
            old_home, old_state = MODULE.HOME, MODULE.STATE
            MODULE.HOME = pathlib.Path(temp)
            MODULE.STATE = MODULE.HOME / ".node-core" / "lobby"
            try:
                with mock.patch.object(MODULE.urllib.request, "urlopen", return_value=FakeResponse(package_bytes)):
                    receipt = MODULE.download_and_verify_release_package("install", release)
                package_path = MODULE.STATE / "packages" / install_name
                self.assertEqual(package_path.read_bytes(), package_bytes)
                self.assertEqual(receipt["status"], "sha256_verified")
                self.assertEqual(receipt["actual_sha256"], hashlib.sha256(package_bytes).hexdigest())
                self.assertFalse(receipt["extracted"])
                self.assertFalse(receipt["executed"])
                self.assertEqual(package_path.stat().st_mode & 0o777, 0o600)
            finally:
                MODULE.HOME, MODULE.STATE = old_home, old_state

    def test_rejects_download_digest_mismatch_and_keeps_no_partial_package(self):
        package_bytes = b"tampered-package"
        payload = release_payload()
        install_name = "node-core-os-install-1.5.6.tar.gz"
        payload["assets"][0]["size"] = len(package_bytes)
        # Keep the official expected digest from the fixture; the bytes are tampered.
        release = MODULE.parse_latest_stable_release(payload)

        class FakeResponse(io.BytesIO):
            def __enter__(self):
                return self
            def __exit__(self, *args):
                self.close()
            def geturl(self):
                return "https://release-assets.githubusercontent.com/asset"

        with tempfile.TemporaryDirectory() as temp:
            old_home, old_state = MODULE.HOME, MODULE.STATE
            MODULE.HOME = pathlib.Path(temp)
            MODULE.STATE = MODULE.HOME / ".node-core" / "lobby"
            try:
                with mock.patch.object(MODULE.urllib.request, "urlopen", return_value=FakeResponse(package_bytes)):
                    with self.assertRaisesRegex(ValueError, "SHA-256"):
                        MODULE.download_and_verify_release_package("install", release)
                package_path = MODULE.STATE / "packages" / install_name
                self.assertFalse(package_path.exists())
                self.assertEqual(list((MODULE.STATE / "packages").glob("*.part")), [])
            finally:
                MODULE.HOME, MODULE.STATE = old_home, old_state


    def _stage_installer_fixture(self, temp, kind="install", unsafe=False):
        old_home, old_state = MODULE.HOME, MODULE.STATE
        MODULE.HOME = pathlib.Path(temp)
        MODULE.STATE = MODULE.HOME / ".node-core" / "lobby"
        package_dir = MODULE.ensure_package_directory()
        name = f"node-core-os-{kind}-9.9.9.tar.gz"
        archive_path = package_dir / name
        files = {
            f"node-core-os/installer/{kind}.sh": b"#!/usr/bin/env bash\\nexit 0\\n",
            "node-core-os/installer/config/defaults": b"NODE_CORE_DATA_DIR=$HOME/.node-core\\n",
        }
        if kind == "install":
            files["node-core-os/installer/lib/filesystem.sh"] = b"prepare_filesystem() { :; }\\n"
        with tarfile.open(archive_path, "w:gz") as archive:
            for member_name, content in files.items():
                info = tarfile.TarInfo(member_name)
                info.size = len(content)
                info.mode = 0o755 if member_name.endswith(".sh") else 0o644
                archive.addfile(info, io.BytesIO(content))
            if unsafe:
                info = tarfile.TarInfo("node-core-os/installer/escape.sh")
                info.type = tarfile.SYMTYPE
                info.linkname = "../../outside"
                archive.addfile(info)
        digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
        receipt_path = package_dir / (name + ".json")
        receipt_path.write_text(json.dumps({"status":"sha256_verified","kind":kind,"asset_name":name,"actual_sha256":digest,"expected_sha256":digest,"tag":"v9.9.9","version":"9.9.9"}), encoding="utf-8")
        return old_home, old_state, name, digest

    def test_extracts_only_canonical_install_script_from_verified_package(self):
        with tempfile.TemporaryDirectory() as temp:
            old_home, old_state, name, digest = self._stage_installer_fixture(temp, "install")
            try:
                with mock.patch.object(MODULE, "latest_stable_release", return_value={"status":"verified_metadata","version":"9.9.9","tag":"v9.9.9","assets":{"install":{"sha256":digest}}}), mock.patch.object(MODULE, "package_receipts", return_value={"packages":[{"asset_name":name,"kind":"install","version":"9.9.9"}]}):
                    root, work = MODULE._verified_installer_root("install")
                self.assertTrue((root / "installer" / "install.sh").is_file())
                self.assertTrue((root / "installer" / "lib" / "filesystem.sh").is_file())
                self.assertEqual(root.parent, work)
                import shutil
                shutil.rmtree(work)
            finally:
                MODULE.HOME, MODULE.STATE = old_home, old_state

    def test_selects_official_update_script_not_install_script(self):
        with tempfile.TemporaryDirectory() as temp:
            old_home, old_state, name, digest = self._stage_installer_fixture(temp, "update")
            try:
                with mock.patch.object(MODULE, "latest_stable_release", return_value={"status":"verified_metadata","version":"9.9.9","tag":"v9.9.9","assets":{"update":{"sha256":digest}}}), mock.patch.object(MODULE, "package_receipts", return_value={"packages":[{"asset_name":name,"kind":"update","version":"9.9.9"}]}):
                    root, work = MODULE._verified_installer_root("update")
                self.assertTrue((root / "installer" / "update.sh").is_file())
                self.assertFalse((root / "installer" / "install.sh").exists())
                import shutil
                shutil.rmtree(work)
            finally:
                MODULE.HOME, MODULE.STATE = old_home, old_state

    def test_rejects_symlink_members_in_official_package(self):
        with tempfile.TemporaryDirectory() as temp:
            old_home, old_state, name, digest = self._stage_installer_fixture(temp, "install", unsafe=True)
            try:
                with mock.patch.object(MODULE, "latest_stable_release", return_value={"status":"verified_metadata","version":"9.9.9","tag":"v9.9.9","assets":{"install":{"sha256":digest}}}), mock.patch.object(MODULE, "package_receipts", return_value={"packages":[{"asset_name":name,"kind":"install","version":"9.9.9"}]}):
                    with self.assertRaisesRegex(ValueError, "unsafe path|unsupported link"):
                        MODULE._verified_installer_root("install")
            finally:
                MODULE.HOME, MODULE.STATE = old_home, old_state


if __name__ == "__main__":
    unittest.main(verbosity=2)
