#!/usr/bin/env python3
"""Independent Lobby certificate inventory and lifecycle manager.

The Lobby manages its own loopback TLS certificate and the Node Core OS
explicit peer-certificate allowlist. Node Core OS identity private keys and
its own P2P certificate are never created, read, rotated, or exported here.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import json
import os
import re
import shutil
import ssl
import stat
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
CATALOG_PATH = HERE / "certificates" / "catalog.json"
ED25519_SPKI_PREFIX = bytes.fromhex("302a300506032b6570032100")
NODE_URI_PREFIX = "urn:node-core-os:node:"
MAX_PEER_PEM_BYTES = 64 * 1024


class CertificateManagerError(ValueError):
    """Raised when a certificate operation cannot be performed safely."""


class CertificateManager:
    """Read, validate, and manage the Lobby TLS pair and pinned Node Core peers."""

    def __init__(self, home: Path | str | None = None, openssl: str | None = None) -> None:
        self.home = Path(home or Path.home()).expanduser()
        self.base = self.home / ".node-core"
        self.state = self.base / "lobby"
        self.cert_path = self.state / "localhost.crt"
        self.key_path = self.state / "localhost.key"
        self.security_dir = self.state / "certificates"
        self.backup_dir = self.security_dir / "backups"
        self.quarantine_dir = self.security_dir / "quarantine"
        self.audit_path = self.security_dir / "actions.jsonl"
        self.openssl = openssl or shutil.which("openssl")
        self.core_data_dir = self._core_data_dir()

    def _core_data_dir(self) -> Path:
        configured = os.environ.get("NODE_CORE_DATA_DIR")
        if configured:
            return Path(configured).expanduser()
        config_path = self.base / "config.json"
        if not config_path.is_symlink() and config_path.is_file():
            try:
                if config_path.stat().st_size <= 65536:
                    value = json.loads(config_path.read_text(encoding="utf-8"))
                    if isinstance(value, dict) and isinstance(value.get("data_dir"), str):
                        return Path(value["data_dir"]).expanduser()
            except (OSError, ValueError, TypeError):
                pass
        return self.base

    @staticmethod
    def _mode(path: Path) -> str | None:
        try:
            return oct(stat.S_IMODE(path.stat().st_mode))
        except OSError:
            return None

    @staticmethod
    def _utc_now() -> dt.datetime:
        return dt.datetime.now(dt.timezone.utc)

    @staticmethod
    def _parse_openssl_date(value: str) -> dt.datetime:
        try:
            parsed = dt.datetime.strptime(value.strip(), "%b %d %H:%M:%S %Y %Z")
            return parsed.replace(tzinfo=dt.timezone.utc)
        except ValueError as exc:
            raise CertificateManagerError("OpenSSL returned an unsupported certificate date") from exc

    def _run_openssl(self, arguments: list[str], timeout: float = 10.0) -> subprocess.CompletedProcess[str]:
        if not self.openssl:
            raise CertificateManagerError("OpenSSL is not installed. Install Termux package openssl-tool.")
        try:
            result = subprocess.run(
                [self.openssl, *arguments],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise CertificateManagerError(f"OpenSSL could not complete the requested check: {exc}") from exc
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "OpenSSL validation failed").strip()
            raise CertificateManagerError(detail[:240])
        return result

    def _x509_metadata(self, cert_path: Path) -> dict[str, Any]:
        if cert_path.is_symlink() or not cert_path.is_file():
            raise CertificateManagerError("Certificate path is missing, not a regular file, or is a symlink")
        raw = self._run_openssl([
            "x509", "-in", str(cert_path), "-noout", "-subject", "-issuer",
            "-serial", "-dates", "-fingerprint", "-sha256"
        ]).stdout
        fields: dict[str, str] = {}
        for line in raw.splitlines():
            if "=" in line:
                name, value = line.split("=", 1)
                fields[name.strip().lower()] = value.strip()
        not_before_text = fields.get("notbefore")
        not_after_text = fields.get("notafter")
        if not not_before_text or not not_after_text:
            raise CertificateManagerError("Certificate validity dates are missing")
        not_before = self._parse_openssl_date(not_before_text)
        not_after = self._parse_openssl_date(not_after_text)
        fingerprint_text = fields.get("sha256 fingerprint") or fields.get("sha256fingerprint") or ""
        fingerprint = re.sub(r"[^0-9a-fA-F]", "", fingerprint_text).lower()
        if len(fingerprint) != 64:
            raise CertificateManagerError("Certificate SHA-256 fingerprint could not be parsed")
        san_text = self._run_openssl([
            "x509", "-in", str(cert_path), "-noout", "-ext", "subjectAltName"
        ]).stdout
        eku_result = subprocess.run(
            [self.openssl, "x509", "-in", str(cert_path), "-noout", "-ext", "extendedKeyUsage"],
            capture_output=True, text=True, timeout=10, check=False,
        )
        return {
            "subject": fields.get("subject", ""),
            "issuer": fields.get("issuer", ""),
            "serial": fields.get("serial", ""),
            "not_before": not_before.isoformat(),
            "not_after": not_after.isoformat(),
            "expires_in_days": (not_after - self._utc_now()).days,
            "fingerprint_sha256": fingerprint,
            "san": san_text.strip().splitlines()[-1].strip() if san_text.strip() else "",
            "extended_key_usage": (eku_result.stdout or "").strip(),
            "self_signed": fields.get("subject") == fields.get("issuer"),
            "currently_valid": not_before <= self._utc_now() <= not_after,
        }

    def inspect_lobby_tls(self) -> dict[str, Any]:
        cert_exists = self.cert_path.exists() or self.cert_path.is_symlink()
        key_exists = self.key_path.exists() or self.key_path.is_symlink()
        result: dict[str, Any] = {
            "id": "lobby-localhost-tls",
            "name": "Lobby loopback HTTPS",
            "certificate_path": str(self.cert_path),
            "private_key_path": str(self.key_path),
            "private_key_contents_exposed": False,
            "private_key_present": bool(key_exists and self.key_path.is_file() and not self.key_path.is_symlink()),
            "private_key_mode": self._mode(self.key_path) if key_exists and not self.key_path.is_symlink() else None,
            "status": "missing",
            "trust_model": "Self-signed local server certificate; not automatically trusted by Android or other devices.",
            "renewal_supported": bool(self.openssl),
            "backup_available": False,
        }
        if not cert_exists and not key_exists:
            result["detail"] = "No active Lobby TLS certificate pair is present."
            return result
        if self.cert_path.is_symlink() or self.key_path.is_symlink():
            result["status"] = "invalid"
            result["detail"] = "Refusing to inspect certificate paths that are symlinks."
            return result
        if cert_exists != key_exists:
            result["status"] = "incomplete"
            result["detail"] = "Only one member of the certificate/private-key pair exists. Repair requires explicit approval."
            return result
        try:
            if self.cert_path.is_symlink() or self.key_path.is_symlink():
                raise CertificateManagerError("Refusing to inspect certificate paths that are symlinks")
            metadata = self._x509_metadata(self.cert_path)
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(str(self.cert_path), str(self.key_path))
            san = metadata["san"].lower()
            host_ok = "dns:localhost" in san and ("ip address:127.0.0.1" in san or "ip:127.0.0.1" in san)
            if not host_ok:
                result["status"] = "invalid"
                result["detail"] = "Certificate SAN must include DNS:localhost and IP:127.0.0.1."
            elif not metadata["currently_valid"]:
                result["status"] = "expired_or_not_yet_valid"
                result["detail"] = "Certificate is outside its validity interval."
            else:
                result["status"] = "valid_self_signed" if metadata["self_signed"] else "valid"
                result["detail"] = "Certificate and private key match; loopback SAN and validity checks passed."
            result.update(metadata)
            result["key_pair_matches"] = True
            result["system_trust_installed"] = False
        except (CertificateManagerError, OSError, ssl.SSLError) as exc:
            result["status"] = "invalid"
            result["detail"] = str(exc)[:240]
            result["key_pair_matches"] = False
        result["backup_available"] = self.inspect_backup()["status"] in ("valid", "valid_self_signed")
        return result

    def inspect_backup(self) -> dict[str, Any]:
        cert = self.backup_dir / "localhost.crt"
        key = self.backup_dir / "localhost.key"
        if not cert.exists() or not key.exists():
            return {"status": "missing", "certificate_path": str(cert)}
        try:
            if cert.is_symlink() or key.is_symlink():
                raise CertificateManagerError("Certificate backup contains a symlink")
            metadata = self._x509_metadata(cert)
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(str(cert), str(key))
            san = metadata["san"].lower()
            if "dns:localhost" not in san or not ("ip address:127.0.0.1" in san or "ip:127.0.0.1" in san):
                raise CertificateManagerError("Backup certificate SAN is not valid for the Lobby")
            if not metadata["currently_valid"]:
                raise CertificateManagerError("Backup certificate is outside its validity interval")
            return {"status": "valid_self_signed" if metadata["self_signed"] else "valid", **metadata}
        except (CertificateManagerError, OSError, ssl.SSLError) as exc:
            return {"status": "invalid", "detail": str(exc)[:240]}

    def inspect_node_identity_tls(self) -> dict[str, Any]:
        identity = self.core_data_dir / "identity"
        cert = identity / "node-cert.pem"
        key = identity / "private" / "node.key"
        metadata_path = identity / "node.json"
        result: dict[str, Any] = {
            "id": "node-core-p2p-identity-tls",
            "name": "Node Core OS P2P identity certificate",
            "certificate_path": str(cert),
            "private_key_present": bool(key.is_file() and not key.is_symlink()),
            "private_key_contents_exposed": False,
            "manager": "Node Core OS core",
            "lobby_mutation_allowed": False,
            "status": "missing",
        }
        if not cert.exists():
            result["detail"] = "No P2P identity certificate is present. Node Core OS creates it when the P2P identity service is initialized."
            return result
        if cert.is_symlink() or metadata_path.is_symlink():
            result.update(status="invalid", detail="Refusing to follow symlinks in the Node Core identity directory.")
            return result
        try:
            if not metadata_path.is_file():
                raise CertificateManagerError("Node identity metadata is missing")
            meta = json.loads(metadata_path.read_text(encoding="utf-8"))
            public_hex = meta.get("public_key") if isinstance(meta, dict) else None
            node_id = meta.get("node_id") if isinstance(meta, dict) else None
            pem_public = self._run_openssl(["x509", "-in", str(cert), "-pubkey", "-noout"]).stdout
            with tempfile.NamedTemporaryFile("w", encoding="ascii", prefix="node-core-peer-key-", delete=False) as handle:
                public_path = Path(handle.name)
                handle.write(pem_public)
            try:
                os.chmod(public_path, 0o600)
                der = subprocess.run(
                    [self.openssl, "pkey", "-pubin", "-in", str(public_path), "-outform", "DER"],
                    capture_output=True, timeout=10, check=False,
                )
            finally:
                public_path.unlink(missing_ok=True)
            if der.returncode != 0 or not der.stdout.startswith(ED25519_SPKI_PREFIX) or len(der.stdout) != len(ED25519_SPKI_PREFIX) + 32:
                raise CertificateManagerError("P2P certificate does not contain a raw Ed25519 public key")
            raw_key = der.stdout[len(ED25519_SPKI_PREFIX):]
            derived_id = "sha256:" + hashlib.sha256(raw_key).hexdigest()
            if public_hex != raw_key.hex() or node_id != derived_id:
                raise CertificateManagerError("P2P certificate public key does not match node.json")
            x509 = self._x509_metadata(cert)
            san = x509["san"]
            if NODE_URI_PREFIX + derived_id not in san:
                raise CertificateManagerError("P2P certificate SAN does not match the local NODE ID")
            if not x509["self_signed"] or not x509["currently_valid"]:
                raise CertificateManagerError("P2P certificate is not a currently valid self-signed identity certificate")
            self._run_openssl(["verify", "-check_ss_sig", "-CAfile", str(cert), str(cert)])
            result.update(status="valid", detail="Ed25519 key, NODE ID, self-signature, SAN and validity checks passed.", node_id=derived_id, **x509)
        except (CertificateManagerError, OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            result.update(status="invalid", detail=str(exc)[:240])
        return result

    def _peer_store_path(self) -> Path:
        return self.core_data_dir / "p2p" / "trusted-peers.json"

    def list_trusted_peers(self) -> list[dict[str, Any]]:
        path = self._peer_store_path()
        if path.is_symlink():
            raise CertificateManagerError("Refusing to read a symlink as the Node Core peer trust store")
        if not path.exists():
            return []
        if not path.is_file() or path.stat().st_size > 5 * 1024 * 1024:
            raise CertificateManagerError("Peer trust store is not a bounded regular file")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise CertificateManagerError("Node Core peer trust store is unreadable or invalid JSON") from exc
        if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("peers"), dict):
            raise CertificateManagerError("Unsupported or malformed Node Core peer trust store")
        records = []
        for node_id, value in sorted(data["peers"].items()):
            if not isinstance(value, dict) or value.get("node_id") != node_id:
                raise CertificateManagerError("Peer trust record does not match its NODE ID key")
            if value.get("status") not in ("trusted", "revoked"):
                raise CertificateManagerError("Peer trust record has an invalid status")
            pem = value.get("certificate_pem")
            if not isinstance(pem, str):
                raise CertificateManagerError("Peer trust record is missing its public certificate")
            inspected = self.inspect_peer_certificate(pem)
            if inspected["node_id"] != node_id:
                raise CertificateManagerError("Stored peer certificate does not match its NODE ID")
            if inspected["fingerprint_sha256"] != value.get("fingerprint_sha256"):
                raise CertificateManagerError("Stored peer certificate fingerprint does not match its record")
            label = value.get("label", "")
            if not isinstance(label, str) or len(label) > 128:
                raise CertificateManagerError("Stored peer label is invalid")
            records.append({
                "node_id": node_id,
                "fingerprint_sha256": inspected["fingerprint_sha256"],
                "label": label,
                "status": value["status"],
                "added_at": value.get("added_at", ""),
                "revoked_at": value.get("revoked_at") or "",
            })
        return records

    def inventory(self) -> dict[str, Any]:
        if CATALOG_PATH.is_symlink() or not CATALOG_PATH.is_file():
            raise CertificateManagerError("Bundled security certificate catalog is missing or unsafe")
        try:
            catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise CertificateManagerError("Bundled security certificate catalog is unreadable") from exc
        if not isinstance(catalog, dict) or catalog.get("schema_version") != 1:
            raise CertificateManagerError("Unsupported security certificate catalog schema")
        technical = []
        for item in catalog.get("technical_certificates", []):
            entry = dict(item)
            if entry.get("id") == "lobby-localhost-tls":
                entry["runtime"] = self.inspect_lobby_tls()
            elif entry.get("id") == "node-core-p2p-identity-tls":
                entry["runtime"] = self.inspect_node_identity_tls()
            elif entry.get("id") == "node-core-peer-trust-store":
                peers = self.list_trusted_peers()
                entry["runtime"] = {
                    "status": "configured" if peers else "empty",
                    "trusted_count": sum(peer["status"] == "trusted" for peer in peers),
                    "revoked_count": sum(peer["status"] == "revoked" for peer in peers),
                    "path": str(self._peer_store_path()),
                    "peers": peers,
                }
            else:
                entry["runtime"] = {"status": "not_configured", "detail": "No managed file or issuer trust source is configured."}
            technical.append(entry)
        return {
            "generated_at": self._utc_now().isoformat(),
            "catalog_version": catalog.get("catalog_version"),
            "technical_certificates": technical,
            "security_profiles": catalog.get("security_profiles", []),
            "policies": catalog.get("policies", {}),
            "audit_log_path": str(self.audit_path),
        }

    def _ensure_owned_directory(self, path: Path) -> None:
        for candidate in (self.base, self.state, self.security_dir, path):
            if candidate.is_symlink():
                raise CertificateManagerError(f"Refusing to use a symlink for security state: {candidate}")
            if candidate.exists() and not candidate.is_dir():
                raise CertificateManagerError(f"Security state path is not a directory: {candidate}")
        self.base.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.state.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.security_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
        for candidate in (self.base, self.state, self.security_dir, path):
            if hasattr(os, "getuid") and candidate.stat().st_uid != os.getuid():
                raise CertificateManagerError(f"Security state directory is not owned by the current user: {candidate}")
            try:
                candidate.chmod(0o700)
            except OSError:
                pass

    def _copy_atomic(self, source: Path, destination: Path) -> None:
        if source.is_symlink() or not source.is_file() or destination.is_symlink():
            raise CertificateManagerError("Refusing unsafe certificate backup or restore path")
        fd, name = tempfile.mkstemp(prefix=".certificate-copy-", dir=str(destination.parent))
        try:
            with os.fdopen(fd, "wb") as output, source.open("rb") as input_file:
                shutil.copyfileobj(input_file, output)
                output.flush()
                os.fsync(output.fileno())
            os.chmod(name, 0o600)
            os.replace(name, destination)
        except BaseException:
            Path(name).unlink(missing_ok=True)
            raise

    def _generate_lobby_pair(self) -> tuple[Path, Path, dict[str, Any]]:
        self._ensure_owned_directory(self.security_dir)
        cert_fd, cert_name = tempfile.mkstemp(prefix=".localhost-", suffix=".crt", dir=str(self.security_dir))
        key_fd, key_name = tempfile.mkstemp(prefix=".localhost-", suffix=".key", dir=str(self.security_dir))
        os.close(cert_fd)
        os.close(key_fd)
        cert_tmp, key_tmp = Path(cert_name), Path(key_name)
        try:
            cert_tmp.unlink()
            key_tmp.unlink()
            self._run_openssl([
                "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-sha256",
                "-keyout", str(key_tmp), "-out", str(cert_tmp), "-days", "365",
                "-subj", "/CN=localhost",
                "-addext", "basicConstraints=critical,CA:FALSE",
                "-addext", "keyUsage=critical,digitalSignature,keyEncipherment",
                "-addext", "extendedKeyUsage=serverAuth",
                "-addext", "subjectAltName=DNS:localhost,IP:127.0.0.1",
            ], timeout=45.0)
            os.chmod(cert_tmp, 0o600)
            os.chmod(key_tmp, 0o600)
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(str(cert_tmp), str(key_tmp))
            metadata = self._x509_metadata(cert_tmp)
            san = metadata["san"].lower()
            if not metadata["currently_valid"] or "dns:localhost" not in san or not (
                "ip address:127.0.0.1" in san or "ip:127.0.0.1" in san
            ):
                raise CertificateManagerError("Generated Lobby certificate failed SAN or validity checks")
            return cert_tmp, key_tmp, metadata
        except BaseException:
            cert_tmp.unlink(missing_ok=True)
            key_tmp.unlink(missing_ok=True)
            raise

    def _audit(self, action: str, result: str, fingerprint_before: str = "", fingerprint_after: str = "") -> None:
        self._ensure_owned_directory(self.security_dir)
        if self.audit_path.is_symlink():
            raise CertificateManagerError("Refusing to append through a symlink audit log")
        record = {
            "timestamp": self._utc_now().isoformat(),
            "action": action,
            "result": result,
            "fingerprint_before": fingerprint_before,
            "fingerprint_after": fingerprint_after,
            "private_key_material_logged": False,
        }
        descriptor = os.open(str(self.audit_path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            with os.fdopen(descriptor, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, sort_keys=True) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
        except BaseException:
            raise
        try:
            self.audit_path.chmod(0o600)
        except OSError:
            pass

    def change_lobby_tls(self, action: str) -> dict[str, Any]:
        if action not in ("tls_install", "tls_renew", "tls_repair", "tls_recover"):
            raise CertificateManagerError("Unsupported Lobby TLS certificate action")
        self._ensure_owned_directory(self.backup_dir)
        before = self.inspect_lobby_tls()
        backup_cert = self.backup_dir / "localhost.crt"
        backup_key = self.backup_dir / "localhost.key"
        if action == "tls_install" and before["status"] != "missing":
            raise CertificateManagerError("Install is allowed only when the Lobby certificate and key are both absent")
        if action == "tls_renew" and before["status"] not in ("valid", "valid_self_signed"):
            raise CertificateManagerError("Renew requires a currently valid Lobby certificate pair; use repair for an invalid pair")
        if action == "tls_repair" and before["status"] in ("valid", "valid_self_signed"):
            raise CertificateManagerError("Repair is not needed because the active Lobby certificate pair is valid")
        if action == "tls_recover":
            backup = self.inspect_backup()
            if backup["status"] not in ("valid", "valid_self_signed"):
                raise CertificateManagerError("No currently valid certificate backup is available for recovery")
            if self.cert_path.exists() and self.cert_path.is_symlink() or self.key_path.exists() and self.key_path.is_symlink():
                raise CertificateManagerError("Refusing to recover through symlink certificate paths")
            recovery = self.security_dir / ("before-recovery-" + str(int(time.time())))
            recovery.mkdir(mode=0o700, parents=True, exist_ok=False)
            for source, name in ((self.cert_path, "localhost.crt"), (self.key_path, "localhost.key")):
                if source.exists():
                    self._copy_atomic(source, recovery / name)
            temp_cert = self.security_dir / (".recover-" + str(os.getpid()) + ".crt")
            temp_key = self.security_dir / (".recover-" + str(os.getpid()) + ".key")
            self._copy_atomic(backup_cert, temp_cert)
            self._copy_atomic(backup_key, temp_key)
            try:
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                context.load_cert_chain(str(temp_cert), str(temp_key))
                os.replace(temp_key, self.key_path)
                os.replace(temp_cert, self.cert_path)
            finally:
                temp_cert.unlink(missing_ok=True)
                temp_key.unlink(missing_ok=True)
            after = self.inspect_lobby_tls()
            if after["status"] not in ("valid", "valid_self_signed"):
                raise CertificateManagerError("Recovered Lobby certificate failed post-install validation")
            self._audit(action, "success", before.get("fingerprint_sha256", ""), after.get("fingerprint_sha256", ""))
            return {"action": action, "before": before, "after": after, "restart_required": True, "backup_available": True}

        if action == "tls_renew":
            self._copy_atomic(self.cert_path, backup_cert)
            self._copy_atomic(self.key_path, backup_key)

        cert_tmp = key_tmp = None
        quarantined: list[tuple[Path, Path]] = []
        try:
            # Generate and validate the replacement before moving any active file.
            cert_tmp, key_tmp, generated = self._generate_lobby_pair()
            if action == "tls_repair":
                self._ensure_owned_directory(self.quarantine_dir)
                stamp = str(int(time.time()))
                for source, suffix in ((self.cert_path, ".crt"), (self.key_path, ".key")):
                    if source.exists():
                        if source.is_symlink() or not source.is_file():
                            raise CertificateManagerError("Refusing to move an unsafe existing TLS file")
                        destination = self.quarantine_dir / ("localhost-" + stamp + suffix)
                        os.replace(source, destination)
                        quarantined.append((destination, source))
            os.replace(key_tmp, self.key_path)
            os.replace(cert_tmp, self.cert_path)
            after = self.inspect_lobby_tls()
            if after["status"] not in ("valid", "valid_self_signed"):
                raise CertificateManagerError("New Lobby certificate failed post-install validation")
            self._audit(action, "success", before.get("fingerprint_sha256", ""), after.get("fingerprint_sha256", ""))
            return {
                "action": action,
                "before": before,
                "after": after,
                "restart_required": True,
                "backup_available": self.inspect_backup()["status"] in ("valid", "valid_self_signed"),
                "generated_certificate": {
                    "fingerprint_sha256": generated["fingerprint_sha256"],
                    "not_after": generated["not_after"],
                    "san": generated["san"],
                },
            }
        except BaseException:
            if action == "tls_renew" and backup_cert.is_file() and backup_key.is_file():
                self._copy_atomic(backup_key, self.key_path)
                self._copy_atomic(backup_cert, self.cert_path)
            elif action == "tls_install":
                self.cert_path.unlink(missing_ok=True)
                self.key_path.unlink(missing_ok=True)
            elif action == "tls_repair" and quarantined:
                # Only remove newly placed regular files after the original pair
                # has actually been moved aside. If validation aborts before that
                # point, leave every pre-existing path untouched.
                for active in (self.cert_path, self.key_path):
                    if active.exists() and active.is_file() and not active.is_symlink():
                        active.unlink()
                for saved, original in reversed(quarantined):
                    if saved.exists():
                        os.replace(saved, original)
            raise
        finally:
            if cert_tmp:
                cert_tmp.unlink(missing_ok=True)
            if key_tmp:
                key_tmp.unlink(missing_ok=True)

    def inspect_peer_certificate(self, pem_text: str) -> dict[str, Any]:
        if not isinstance(pem_text, str) or not pem_text or len(pem_text.encode("utf-8")) > MAX_PEER_PEM_BYTES:
            raise CertificateManagerError("Peer certificate PEM is empty or exceeds 64 KiB")
        if "PRIVATE KEY" in pem_text or pem_text.count("-----BEGIN CERTIFICATE-----") != 1 or pem_text.count("-----END CERTIFICATE-----") != 1:
            raise CertificateManagerError("Upload exactly one public PEM certificate; private keys and certificate bundles are not accepted")
        try:
            encoded = pem_text.encode("ascii")
        except UnicodeEncodeError as exc:
            raise CertificateManagerError("PEM certificate must contain ASCII text") from exc
        self._ensure_owned_directory(self.security_dir)
        fd, name = tempfile.mkstemp(prefix=".peer-inspect-", suffix=".pem", dir=str(self.security_dir))
        path = Path(name)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(path, 0o600)
            meta = self._x509_metadata(path)
            public_pem = self._run_openssl(["x509", "-in", str(path), "-pubkey", "-noout"]).stdout
            with tempfile.NamedTemporaryFile("w", encoding="ascii", prefix=".peer-public-", delete=False, dir=str(self.security_dir)) as public_file:
                public_path = Path(public_file.name)
                public_file.write(public_pem)
            try:
                os.chmod(public_path, 0o600)
                der = subprocess.run(
                    [self.openssl, "pkey", "-pubin", "-in", str(public_path), "-outform", "DER"],
                    capture_output=True, timeout=10, check=False,
                )
            finally:
                public_path.unlink(missing_ok=True)
            if der.returncode != 0 or not der.stdout.startswith(ED25519_SPKI_PREFIX) or len(der.stdout) != len(ED25519_SPKI_PREFIX) + 32:
                raise CertificateManagerError("Peer certificate must use Ed25519 public-key cryptography")
            public_key = der.stdout[len(ED25519_SPKI_PREFIX):]
            node_id = "sha256:" + hashlib.sha256(public_key).hexdigest()
            san = meta["san"]
            if NODE_URI_PREFIX + node_id not in san:
                raise CertificateManagerError("Peer certificate SAN does not bind its public key to the derived NODE ID")
            if not meta["self_signed"] or not meta["currently_valid"]:
                raise CertificateManagerError("Peer certificate must be currently valid and self-signed")
            constraints = self._run_openssl(["x509", "-in", str(path), "-noout", "-ext", "basicConstraints"]).stdout
            if "CA:TRUE" not in constraints.upper():
                raise CertificateManagerError("Node Core OS P2P peer certificate must declare CA:TRUE for explicit pinning")
            self._run_openssl(["verify", "-check_ss_sig", "-CAfile", str(path), str(path)])
            return {
                "node_id": node_id,
                "public_key": public_key.hex(),
                "fingerprint_sha256": meta["fingerprint_sha256"],
                "subject": meta["subject"],
                "issuer": meta["issuer"],
                "serial": meta["serial"],
                "not_before": meta["not_before"],
                "not_after": meta["not_after"],
                "san": meta["san"],
                "signature_valid": True,
                "currently_valid": True,
                "certificate_pem": encoded.decode("ascii"),
            }
        finally:
            path.unlink(missing_ok=True)

    def _load_peer_store(self) -> dict[str, Any]:
        path = self._peer_store_path()
        if path.is_symlink():
            raise CertificateManagerError("Refusing to write to a symlink peer trust store")
        parent = path.parent
        if parent.is_symlink():
            raise CertificateManagerError("Refusing to write through a symlink peer directory")
        if path.exists():
            if not path.is_file() or path.stat().st_size > 5 * 1024 * 1024:
                raise CertificateManagerError("Peer trust store is not a bounded regular file")
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise CertificateManagerError("Peer trust store is unreadable or invalid JSON") from exc
        else:
            data = {"schema_version": 1, "peers": {}}
        if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("peers"), dict):
            raise CertificateManagerError("Unsupported or malformed Node Core peer trust store")
        # Validate every existing public certificate before writing a modified
        # trust store; never preserve silently corrupted trust records.
        for node_id, record in data["peers"].items():
            if not isinstance(record, dict) or record.get("node_id") != node_id:
                raise CertificateManagerError("Existing peer trust record is malformed")
            if record.get("status") not in ("trusted", "revoked"):
                raise CertificateManagerError("Existing peer trust status is invalid")
            pem = record.get("certificate_pem")
            if not isinstance(pem, str):
                raise CertificateManagerError("Existing peer trust certificate is missing")
            inspected = self.inspect_peer_certificate(pem)
            if inspected["node_id"] != node_id or inspected["fingerprint_sha256"] != record.get("fingerprint_sha256"):
                raise CertificateManagerError("Existing peer trust certificate failed identity or fingerprint validation")
        return data

    def _save_peer_store(self, data: dict[str, Any]) -> None:
        path = self._peer_store_path()
        if self.core_data_dir.is_symlink() or (self.core_data_dir / "p2p").is_symlink():
            raise CertificateManagerError("Refusing to write through a symlink in the Node Core data path")
        self.core_data_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        peer_dir = self.core_data_dir / "p2p"
        peer_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        if hasattr(os, "getuid") and (self.core_data_dir.stat().st_uid != os.getuid() or peer_dir.stat().st_uid != os.getuid()):
            raise CertificateManagerError("Node Core peer trust directory is not owned by the current user")
        try:
            self.core_data_dir.chmod(0o700)
            peer_dir.chmod(0o700)
        except OSError:
            pass
        fd, temporary = tempfile.mkstemp(prefix=".trusted-peers-", suffix=".tmp", dir=str(peer_dir))
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
            try:
                path.chmod(0o600)
            except OSError:
                pass
        except BaseException:
            Path(temporary).unlink(missing_ok=True)
            raise

    def trust_peer_certificate(
        self, pem_text: str, label: str = "", replace: bool = False,
        expected_fingerprint_sha256: str = "",
    ) -> dict[str, Any]:
        if not isinstance(label, str) or len(label) > 128 or any(ord(char) < 32 for char in label):
            raise CertificateManagerError("Peer label must contain at most 128 printable characters")
        inspected = self.inspect_peer_certificate(pem_text)
        if not isinstance(expected_fingerprint_sha256, str) or re.fullmatch(r"[0-9a-f]{64}", expected_fingerprint_sha256) is None:
            raise CertificateManagerError("Confirm the inspected 64-character SHA-256 fingerprint before trusting this peer")
        if not hmac.compare_digest(inspected["fingerprint_sha256"], expected_fingerprint_sha256):
            raise CertificateManagerError("The confirmed SHA-256 fingerprint does not match the inspected peer certificate")
        data = self._load_peer_store()
        peers = data["peers"]
        node_id = inspected["node_id"]
        previous = peers.get(node_id)
        pem = inspected.pop("certificate_pem")
        if previous:
            if not isinstance(previous, dict) or previous.get("status") not in ("trusted", "revoked"):
                raise CertificateManagerError("Existing peer record is malformed")
            if previous.get("certificate_pem") == pem and previous.get("status") == "trusted":
                return {"status": "already_trusted", "node_id": node_id, "fingerprint_sha256": inspected["fingerprint_sha256"]}
            if previous.get("status") == "trusted" and not replace:
                raise CertificateManagerError("A different certificate is already trusted for this NODE ID; explicit replacement is required")
        peers[node_id] = {
            "node_id": node_id,
            "certificate_pem": pem,
            "fingerprint_sha256": inspected["fingerprint_sha256"],
            "label": label,
            "status": "trusted",
            "added_at": self._utc_now().isoformat(),
            "revoked_at": None,
        }
        self._save_peer_store(data)
        self._audit("peer_trust", "success", "", inspected["fingerprint_sha256"])
        return {"status": "trusted", "node_id": node_id, "fingerprint_sha256": inspected["fingerprint_sha256"], "label": label}

    def revoke_peer(self, node_id: str) -> dict[str, Any]:
        if not isinstance(node_id, str) or re.fullmatch(r"sha256:[0-9a-f]{64}", node_id) is None:
            raise CertificateManagerError("A canonical sha256 NODE ID is required")
        data = self._load_peer_store()
        record = data["peers"].get(node_id)
        if not isinstance(record, dict):
            raise CertificateManagerError("Cannot revoke an unknown peer")
        if record.get("status") != "revoked":
            record["status"] = "revoked"
            record["revoked_at"] = self._utc_now().isoformat()
            self._save_peer_store(data)
            self._audit("peer_revoke", "success", record.get("fingerprint_sha256", ""), "")
        return {"status": "revoked", "node_id": node_id, "effective_after_core_reload": True}

    def execute(self, action: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        values = payload or {}
        if action.startswith("tls_"):
            return self.change_lobby_tls(action)
        if action == "peer_inspect":
            inspected = self.inspect_peer_certificate(values.get("certificate_pem", ""))
            inspected.pop("certificate_pem", None)
            return inspected
        if action == "peer_trust":
            return self.trust_peer_certificate(
                values.get("certificate_pem", ""),
                values.get("label", ""),
                values.get("replace") is True,
                values.get("expected_fingerprint_sha256", ""),
            )
        if action == "peer_revoke":
            return self.revoke_peer(values.get("node_id", ""))
        raise CertificateManagerError("Unknown certificate-manager operation")
