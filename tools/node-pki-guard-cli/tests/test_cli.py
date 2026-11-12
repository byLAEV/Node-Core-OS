from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from node_pki_guard_cli.cli import VerificationError, verify_bundle


OPENSSL = shutil.which("openssl")


@unittest.skipUnless(OPENSSL, "OpenSSL is required for CLI integration tests")
class OpenSSLBundleVerifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="node-pki-cli-test-")
        self.root = Path(self.temp.name)
        self.bundle = self.root / "bundle"
        (self.bundle / "certs").mkdir(parents=True)
        self.ca_key = self.root / "ca.key"
        self.ca_cert = self.root / "ca.pem"
        self.leaf_key = self.root / "leaf.key"
        self.csr = self.root / "leaf.csr"
        self.leaf_cert = self.bundle / "certs" / "certificate.pem"
        self.der_cert = self.bundle / "certs" / "certificate.der"
        self._openssl([
            "req", "-x509", "-newkey", "rsa:2048", "-nodes",
            "-keyout", str(self.ca_key), "-out", str(self.ca_cert),
            "-subj", "/CN=NODE-PKI-GUARD Test Root", "-days", "2",
            "-sha256", "-addext", "basicConstraints=critical,CA:TRUE,pathlen:0",
            "-addext", "keyUsage=critical,keyCertSign,cRLSign",
            "-addext", "subjectKeyIdentifier=hash",
            "-addext", "authorityKeyIdentifier=keyid:always",
        ])
        self._openssl([
            "req", "-new", "-newkey", "rsa:2048", "-nodes",
            "-keyout", str(self.leaf_key), "-out", str(self.csr),
            "-subj", "/CN=service.example.test",
            "-addext", "subjectAltName=DNS:service.example.test",
        ])
        extensions = self.root / "leaf.ext"
        extensions.write_text(
            "basicConstraints=critical,CA:FALSE\n"
            "keyUsage=critical,digitalSignature,keyEncipherment\n"
            "extendedKeyUsage=serverAuth\n"
            "subjectAltName=DNS:service.example.test\n"
            "subjectKeyIdentifier=hash\n"
            "authorityKeyIdentifier=keyid,issuer\n",
            encoding="utf-8",
        )
        self._openssl([
            "x509", "-req", "-in", str(self.csr),
            "-CA", str(self.ca_cert), "-CAkey", str(self.ca_key),
            "-CAcreateserial", "-out", str(self.leaf_cert),
            "-days", "1", "-sha256", "-extfile", str(extensions),
        ])
        self._openssl([
            "x509", "-in", str(self.leaf_cert), "-outform", "DER",
            "-out", str(self.der_cert),
        ])
        self.manifest_path = self.bundle / "manifest.json"
        self._write_manifest()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _openssl(self, arguments: list[str]) -> bytes:
        result = subprocess.run(
            [OPENSSL or "openssl", *arguments],
            capture_output=True,
            check=False,
            timeout=30,
        )
        if result.returncode != 0:
            self.fail(
                "OpenSSL test fixture command failed: "
                + (result.stderr or result.stdout).decode("utf-8", errors="replace")
            )
        return result.stdout

    def _certificate_fingerprints(self) -> tuple[str, str]:
        der = self._openssl([
            "x509", "-in", str(self.leaf_cert), "-outform", "DER",
        ])
        public_key = self._openssl([
            "x509", "-in", str(self.leaf_cert), "-pubkey", "-noout",
        ])
        with tempfile.NamedTemporaryFile() as key_file:
            result = subprocess.run(
                [OPENSSL or "openssl", "pkey", "-pubin", "-outform", "DER"],
                input=public_key, capture_output=True, check=True, timeout=15,
            )
        return hashlib.sha256(der).hexdigest(), hashlib.sha256(result.stdout).hexdigest()

    def _write_manifest(self, *, path: str = "certs/certificate.pem") -> None:
        certificate_fp, spki_fp = self._certificate_fingerprints()
        inventory = []
        for relative in ("certs/certificate.pem", "certs/certificate.der"):
            content = (self.bundle / relative).read_bytes()
            inventory.append({
                "path": relative,
                "sha256": hashlib.sha256(content).hexdigest(),
                "media_type": "application/pem-certificate" if relative.endswith(".pem") else "application/pkix-cert",
            })
        self.manifest_path.write_text(json.dumps({
            "format": "NODE-PKI-GUARD-X509-BUNDLE",
            "version": "1.0",
            "bundle_id": "cli-test-bundle",
            "created_at": "2026-11-11T00:00:00Z",
            "certificate": {
                "path": path,
                "encoding": "PEM" if path.endswith(".pem") else "DER",
                "sha256_fingerprint": certificate_fp,
                "spki_sha256": spki_fp,
            },
            "files": inventory,
        }, indent=2), encoding="utf-8")

    def test_valid_pem_bundle_verifies(self) -> None:
        result = verify_bundle(
            bundle_dir=self.bundle,
            ca_file=self.ca_cert,
            hostname="service.example.test",
            openssl_binary=OPENSSL or "openssl",
        )
        self.assertTrue(result["valid"])
        self.assertEqual(result["bundle_id"], "cli-test-bundle")
        self.assertEqual(result["inventory_files_verified"], 2)
        self.assertFalse(result["revocation_checked"])

    def test_valid_der_bundle_verifies(self) -> None:
        self._write_manifest(path="certs/certificate.der")
        result = verify_bundle(
            bundle_dir=self.bundle,
            ca_file=self.ca_cert,
            hostname="service.example.test",
            openssl_binary=OPENSSL or "openssl",
        )
        self.assertTrue(result["valid"])

    def test_wrong_hostname_is_rejected(self) -> None:
        with self.assertRaises(VerificationError):
            verify_bundle(
                bundle_dir=self.bundle,
                ca_file=self.ca_cert,
                hostname="attacker.example.test",
                openssl_binary=OPENSSL or "openssl",
            )

    def test_untrusted_ca_is_rejected(self) -> None:
        other_key = self.root / "other.key"
        other_ca = self.root / "other.pem"
        self._openssl([
            "req", "-x509", "-newkey", "rsa:2048", "-nodes",
            "-keyout", str(other_key), "-out", str(other_ca),
            "-subj", "/CN=Untrusted Root", "-days", "2", "-sha256",
            "-addext", "basicConstraints=critical,CA:TRUE",
            "-addext", "keyUsage=critical,keyCertSign,cRLSign",
            "-addext", "subjectKeyIdentifier=hash",
            "-addext", "authorityKeyIdentifier=keyid:always",
        ])
        with self.assertRaises(VerificationError):
            verify_bundle(
                bundle_dir=self.bundle,
                ca_file=other_ca,
                hostname="service.example.test",
                openssl_binary=OPENSSL or "openssl",
            )

    def test_inventory_tampering_is_rejected(self) -> None:
        self.leaf_cert.write_bytes(self.leaf_cert.read_bytes() + b"tamper")
        with self.assertRaises(VerificationError):
            verify_bundle(
                bundle_dir=self.bundle,
                ca_file=self.ca_cert,
                hostname="service.example.test",
                openssl_binary=OPENSSL or "openssl",
            )

    def test_manifest_fingerprint_tampering_is_rejected(self) -> None:
        data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        data["certificate"]["sha256_fingerprint"] = "0" * 64
        self.manifest_path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(VerificationError):
            verify_bundle(
                bundle_dir=self.bundle,
                ca_file=self.ca_cert,
                hostname="service.example.test",
                openssl_binary=OPENSSL or "openssl",
            )

    def test_parent_path_traversal_is_rejected(self) -> None:
        data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        data["certificate"]["path"] = "../outside.pem"
        self.manifest_path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(VerificationError):
            verify_bundle(
                bundle_dir=self.bundle,
                ca_file=self.ca_cert,
                hostname="service.example.test",
                openssl_binary=OPENSSL or "openssl",
            )

    def test_duplicate_json_keys_are_rejected(self) -> None:
        self.manifest_path.write_text(
            '{"format":"NODE-PKI-GUARD-X509-BUNDLE","format":"other"}',
            encoding="utf-8",
        )
        with self.assertRaises(VerificationError):
            verify_bundle(
                bundle_dir=self.bundle,
                ca_file=self.ca_cert,
                hostname="service.example.test",
                openssl_binary=OPENSSL or "openssl",
            )


    def test_invalid_encoding_type_is_rejected(self) -> None:
        data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        data["certificate"]["encoding"] = []
        self.manifest_path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(VerificationError):
            verify_bundle(
                bundle_dir=self.bundle,
                ca_file=self.ca_cert,
                hostname="service.example.test",
                openssl_binary=OPENSSL or "openssl",
            )

    def test_require_crl_fails_when_crl_is_missing(self) -> None:
        with self.assertRaises(VerificationError):
            verify_bundle(
                bundle_dir=self.bundle,
                ca_file=self.ca_cert,
                hostname="service.example.test",
                require_crl=True,
                openssl_binary=OPENSSL or "openssl",
            )


if __name__ == "__main__":
    unittest.main()
