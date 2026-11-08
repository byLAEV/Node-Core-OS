#!/usr/bin/env python3
"""Isolated tests for the independent Lobby certificate manager."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import sys
LOBBY = Path(__file__).resolve().parents[1] / "lobby"
sys.path.insert(0, str(LOBBY))
from certificate_manager import CertificateManager, CertificateManagerError


OPENSSL = shutil.which("openssl")


@unittest.skipUnless(OPENSSL, "OpenSSL is required for certificate-manager tests")
class CertificateManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="node-core-cert-manager-")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.manager = CertificateManager(self.home, OPENSSL)

    def _peer_certificate(self):
        private = self.home / "peer.key"
        cert = self.home / "peer.crt"
        subprocess.run(
            [
                OPENSSL, "req", "-x509", "-newkey", "ed25519", "-nodes",
                "-keyout", str(private), "-out", str(cert), "-days", "30",
                "-subj", "/CN=Node-Core-Test-Peer",
                "-addext", "basicConstraints=critical,CA:TRUE",
            ],
            check=True, capture_output=True, text=True, timeout=20,
        )
        public_pem = subprocess.run(
            [OPENSSL, "x509", "-in", str(cert), "-pubkey", "-noout"],
            check=True, capture_output=True, text=True,
        ).stdout
        public_path = self.home / "peer.pub"
        public_path.write_text(public_pem, encoding="ascii")
        der = subprocess.run(
            [OPENSSL, "pkey", "-pubin", "-in", str(public_path), "-outform", "DER"],
            check=True, capture_output=True,
        ).stdout
        raw = der[-32:]
        node_id = "sha256:" + hashlib.sha256(raw).hexdigest()
        # Re-issue with the exact NODE ID SAN using a minimal OpenSSL config.
        config = self.home / "peer.cnf"
        config.write_text(
            "[req]\ndistinguished_name=dn\nx509_extensions=extensions\nprompt=no\n"
            "[dn]\nCN=Node-Core-Test-Peer\n"
            "[extensions]\nbasicConstraints=critical,CA:TRUE\n"
            f"subjectAltName=URI:urn:node-core-os:node:{node_id}\n",
            encoding="ascii",
        )
        subprocess.run(
            [
                OPENSSL, "req", "-x509", "-key", str(private), "-out", str(cert),
                "-days", "30", "-config", str(config),
            ],
            check=True, capture_output=True, text=True, timeout=20,
        )
        return cert.read_text(encoding="ascii"), node_id

    def test_catalog_has_eight_non_installable_security_profiles(self):
        inventory = self.manager.inventory()
        self.assertEqual(len(inventory["security_profiles"]), 8)
        self.assertTrue(all(item["installable_certificate"] is False for item in inventory["security_profiles"]))
        self.assertEqual(inventory["technical_certificates"][0]["id"], "lobby-localhost-tls")

    def test_install_renew_recover_lobby_tls_and_keep_backup(self):
        installed = self.manager.change_lobby_tls("tls_install")
        self.assertEqual(installed["after"]["status"], "valid_self_signed")
        self.assertEqual(self.manager.cert_path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.manager.key_path.stat().st_mode & 0o777, 0o600)
        old_fingerprint = installed["after"]["fingerprint_sha256"]

        renewed = self.manager.change_lobby_tls("tls_renew")
        self.assertEqual(renewed["after"]["status"], "valid_self_signed")
        self.assertNotEqual(renewed["after"]["fingerprint_sha256"], old_fingerprint)
        self.assertIn(self.manager.inspect_backup()["status"], ("valid", "valid_self_signed"))

        self.manager.cert_path.write_text("tampered", encoding="ascii")
        self.assertEqual(self.manager.inspect_lobby_tls()["status"], "invalid")
        recovered = self.manager.change_lobby_tls("tls_recover")
        self.assertEqual(recovered["after"]["status"], "valid_self_signed")
        self.assertEqual(recovered["after"]["fingerprint_sha256"], old_fingerprint)

    def test_refuses_to_overwrite_existing_pair_during_install(self):
        self.manager.change_lobby_tls("tls_install")
        with self.assertRaisesRegex(CertificateManagerError, "only when"):
            self.manager.change_lobby_tls("tls_install")

    def test_peer_import_and_revocation_never_return_private_key(self):
        pem, node_id = self._peer_certificate()
        inspected = self.manager.inspect_peer_certificate(pem)
        self.assertEqual(inspected["node_id"], node_id)
        self.assertNotIn("PRIVATE KEY", inspected["certificate_pem"])

        with self.assertRaisesRegex(CertificateManagerError, "fingerprint"):
            self.manager.trust_peer_certificate(pem, "test peer", expected_fingerprint_sha256="0" * 64)
        trusted = self.manager.trust_peer_certificate(
            pem, "test peer", expected_fingerprint_sha256=inspected["fingerprint_sha256"]
        )
        self.assertEqual(trusted["status"], "trusted")
        self.assertEqual(self.manager.list_trusted_peers()[0]["node_id"], node_id)

        revoked = self.manager.revoke_peer(node_id)
        self.assertEqual(revoked["status"], "revoked")
        self.assertEqual(self.manager.list_trusted_peers()[0]["status"], "revoked")

        store = json.loads(self.manager._peer_store_path().read_text(encoding="utf-8"))
        self.assertNotIn("private_key", json.dumps(store).lower())
        self.assertEqual(self.manager._peer_store_path().stat().st_mode & 0o777, 0o600)

    def test_rejects_private_key_input_as_peer_certificate(self):
        with self.assertRaisesRegex(CertificateManagerError, "public PEM certificate"):
            self.manager.inspect_peer_certificate("-----BEGIN PRIVATE KEY-----\nsecret\n-----END PRIVATE KEY-----")

    def test_refuses_symlinked_lobby_certificate(self):
        target = self.home / "elsewhere.crt"
        target.write_text("not a certificate", encoding="ascii")
        self.manager.state.mkdir(parents=True, exist_ok=True)
        self.manager.cert_path.symlink_to(target)
        self.assertEqual(self.manager.inspect_lobby_tls()["status"], "invalid")
        with self.assertRaises(CertificateManagerError):
            self.manager.change_lobby_tls("tls_repair")


if __name__ == "__main__":
    unittest.main(verbosity=2)
