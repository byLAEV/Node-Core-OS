"""Auditable OpenPGP frontend backed by the installed GnuPG executable."""
from __future__ import annotations

import argparse
import getpass
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Sequence

FINGERPRINT_RE = re.compile(r"^(?:[A-F0-9]{40}|[A-F0-9]{64})$", re.IGNORECASE)


class OpenPGPError(RuntimeError):
    """Raised when an OpenPGP operation cannot be verified."""


class OpenPGPManager:
    """Manage OpenPGP operations in a dedicated, user-owned GnuPG home."""

    def __init__(self, home: str | Path | None = None, executable: str = "gpg") -> None:
        self.executable = shutil.which(executable) or ""
        configured_home = home or os.environ.get("NODE_CORE_OPENPGP_HOME")
        self.home = Path(configured_home).expanduser() if configured_home else (
            Path.home() / ".node-core" / "openpgp" / "gnupg"
        )

    def _prepare(self) -> None:
        if not self.executable:
            raise OpenPGPError("GnuPG (gpg) is not installed or is not available in PATH.")
        self.home.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            self.home.chmod(0o700)
        except OSError as exc:
            raise OpenPGPError(f"Cannot secure OpenPGP home directory: {exc}") from exc

    def _run(
        self,
        arguments: Sequence[str],
        *,
        passphrase: str | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        self._prepare()
        command = [self.executable, "--homedir", str(self.home), "--batch", "--yes", "--no-tty"]
        input_text = None
        if passphrase is not None:
            if not passphrase:
                raise OpenPGPError("An empty passphrase is not accepted.")
            command.extend(["--pinentry-mode", "loopback", "--passphrase-fd", "0"])
            input_text = passphrase + "\n"
        command.extend(arguments)
        try:
            result = subprocess.run(
                command, input=input_text, text=True, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, check=False, timeout=120,
                env={**os.environ, "GNUPGHOME": str(self.home)},
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise OpenPGPError(f"GnuPG could not complete the operation: {exc}") from exc
        if check and result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            raise OpenPGPError(detail or f"GnuPG exited with status {result.returncode}.")
        return result

    def status(self) -> dict[str, str]:
        result = self._run(["--version"])
        return {
            "backend": result.stdout.splitlines()[0] if result.stdout else "GnuPG version unknown",
            "home": str(self.home),
            "status": "available",
        }

    @staticmethod
    def _validate_fingerprint(fingerprint: str) -> str:
        normalized = fingerprint.replace(" ", "").upper()
        if not FINGERPRINT_RE.fullmatch(normalized):
            raise OpenPGPError("Provide the complete 40- or 64-character hexadecimal fingerprint, not a short key ID.")
        return normalized

    def list_keys(self) -> list[dict[str, str]]:
        result = self._run(["--with-colons", "--list-keys"])
        keys: list[dict[str, str]] = []
        current: dict[str, str] | None = None
        for line in result.stdout.splitlines():
            fields = line.split(":")
            if fields[0] == "pub":
                if current:
                    keys.append(current)
                current = {"fingerprint": "", "uid": ""}
            elif fields[0] == "fpr" and current and not current["fingerprint"]:
                current["fingerprint"] = fields[9]
            elif fields[0] == "uid" and current and not current["uid"]:
                current["uid"] = fields[9]
        if current:
            keys.append(current)
        return [key for key in keys if key["fingerprint"]]

    def generate_key(self, user_id: str, passphrase: str) -> str:
        user_id = user_id.strip()
        if not user_id or "\n" in user_id or "\r" in user_id:
            raise OpenPGPError("A single-line name and email address are required.")
        self._run(["--quick-generate-key", user_id, "ed25519", "sign", "2y"], passphrase=passphrase)
        matching = [key for key in self.list_keys() if key["uid"] == user_id]
        if len(matching) != 1:
            raise OpenPGPError("The new key was not uniquely discoverable after generation.")
        fingerprint = matching[0]["fingerprint"]
        self._run(["--quick-add-key", fingerprint, "cv25519", "encr", "2y"], passphrase=passphrase)
        if not any(key["fingerprint"] == fingerprint for key in self.list_keys()):
            raise OpenPGPError("The generated key could not be confirmed in the local keyring.")
        return fingerprint

    @staticmethod
    def _require_input(path: str | Path) -> Path:
        source = Path(path).expanduser()
        if not source.is_file():
            raise OpenPGPError(f"Input file does not exist: {source}")
        return source

    @staticmethod
    def _require_new_output(path: Path) -> None:
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if path.exists():
            raise OpenPGPError(f"Refusing to overwrite an existing file: {path}")

    def export_public(self, fingerprint: str, output: str | Path) -> Path:
        fingerprint = self._validate_fingerprint(fingerprint)
        destination = Path(output).expanduser()
        self._require_new_output(destination)
        try:
            self._run(["--armor", "--output", str(destination), "--export", fingerprint])
            if not destination.is_file() or destination.stat().st_size == 0:
                raise OpenPGPError("GnuPG did not produce a non-empty public-key export.")
            return destination
        except Exception:
            destination.unlink(missing_ok=True)
            raise

    def import_public(self, source: str | Path) -> None:
        path = self._require_input(source)
        self._run(["--import", str(path)])

    def encrypt(self, source: str | Path, output: str | Path, recipient: str) -> Path:
        source_path = self._require_input(source)
        fingerprint = self._validate_fingerprint(recipient)
        destination = Path(output).expanduser()
        self._require_new_output(destination)
        try:
            # Authenticate this full fingerprint independently before using it.
            # "always" avoids interactive trust prompts; it does not authenticate identity.
            self._run([
                "--trust-model", "always", "--output", str(destination),
                "--recipient", fingerprint, "--encrypt", str(source_path),
            ])
            if not destination.is_file() or destination.stat().st_size == 0:
                raise OpenPGPError("GnuPG did not produce a non-empty encrypted message.")
            return destination
        except Exception:
            destination.unlink(missing_ok=True)
            raise

    def decrypt(self, source: str | Path, output: str | Path, passphrase: str) -> Path:
        source_path = self._require_input(source)
        destination = Path(output).expanduser()
        self._require_new_output(destination)
        try:
            self._run(["--output", str(destination), "--decrypt", str(source_path)], passphrase=passphrase)
            if not destination.is_file():
                raise OpenPGPError("GnuPG did not create the decrypted output.")
            return destination
        except Exception:
            destination.unlink(missing_ok=True)
            raise

    def sign(self, source: str | Path, output: str | Path, fingerprint: str, passphrase: str) -> Path:
        source_path = self._require_input(source)
        signer = self._validate_fingerprint(fingerprint)
        destination = Path(output).expanduser()
        self._require_new_output(destination)
        try:
            self._run([
                "--local-user", signer, "--output", str(destination),
                "--detach-sign", str(source_path),
            ], passphrase=passphrase)
            if not destination.is_file() or destination.stat().st_size == 0:
                raise OpenPGPError("GnuPG did not produce a detached signature.")
            return destination
        except Exception:
            destination.unlink(missing_ok=True)
            raise

    def verify(self, signature: str | Path, source: str | Path) -> str:
        signature_path = self._require_input(signature)
        source_path = self._require_input(source)
        result = self._run([
            "--status-fd", "1", "--verify", str(signature_path), str(source_path),
        ], check=False)
        if result.returncode != 0 or "[GNUPG:] GOODSIG " not in result.stdout:
            detail = (result.stderr or result.stdout).strip()
            raise OpenPGPError("Signature verification failed. " + detail)
        fingerprints = [
            line.split()[2] for line in result.stdout.splitlines()
            if line.startswith("[GNUPG:] VALIDSIG ") and len(line.split()) > 2
        ]
        if not fingerprints:
            raise OpenPGPError("GnuPG returned GOODSIG but no machine-readable VALIDSIG fingerprint.")
        return fingerprints[0]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="node-openpgp",
        description="Linux terminal frontend for interoperable OpenPGP using GnuPG.",
    )
    parser.add_argument("--home", help="Dedicated GnuPG home (default: ~/.node-core/openpgp/gnupg).")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status", help="Check GnuPG and the user-level keyring.")
    commands.add_parser("list", help="List public keys and full fingerprints.")
    keygen = commands.add_parser("keygen", help="Generate Ed25519 signing key and Cv25519 encryption subkey.")
    keygen.add_argument("--name", required=True)
    keygen.add_argument("--email", required=True)
    export = commands.add_parser("export-public", help="Export a public key as ASCII armor.")
    export.add_argument("--fingerprint", required=True)
    export.add_argument("--output", required=True)
    imp = commands.add_parser("import-public", help="Import a public key from a file.")
    imp.add_argument("--input", required=True)
    encrypt = commands.add_parser("encrypt", help="Encrypt a file to a recipient's full fingerprint.")
    encrypt.add_argument("--recipient", required=True)
    encrypt.add_argument("--input", required=True)
    encrypt.add_argument("--output", required=True)
    decrypt = commands.add_parser("decrypt", help="Decrypt a file with the local private key.")
    decrypt.add_argument("--input", required=True)
    decrypt.add_argument("--output", required=True)
    sign = commands.add_parser("sign", help="Create a detached OpenPGP signature.")
    sign.add_argument("--fingerprint", required=True)
    sign.add_argument("--input", required=True)
    sign.add_argument("--output", required=True)
    verify = commands.add_parser("verify", help="Verify a detached signature against its input file.")
    verify.add_argument("--signature", required=True)
    verify.add_argument("--input", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    manager = OpenPGPManager(home=args.home)
    try:
        if args.command == "status":
            status = manager.status()
            print(f"Status: {status['status']}\nBackend: {status['backend']}\nKeyring: {status['home']}")
        elif args.command == "list":
            keys = manager.list_keys()
            if not keys:
                print("No public keys found in the Node Core OS OpenPGP keyring.")
            for key in keys:
                print(f"Fingerprint: {key['fingerprint']}\nUser ID: {key['uid']}\n")
        elif args.command == "keygen":
            first = getpass.getpass("New OpenPGP passphrase (minimum 12 characters): ")
            second = getpass.getpass("Repeat passphrase: ")
            if len(first) < 12:
                raise OpenPGPError("Use a passphrase of at least 12 characters.")
            if first != second:
                raise OpenPGPError("Passphrases do not match.")
            fingerprint = manager.generate_key(f"{args.name} <{args.email}>", first)
            print("OpenPGP key generated and confirmed.")
            print(f"Fingerprint: {fingerprint}")
            print("Algorithms: Ed25519 signing primary key + Cv25519 encryption subkey")
        elif args.command == "export-public":
            print(f"Public key exported: {manager.export_public(args.fingerprint, args.output)}")
        elif args.command == "import-public":
            manager.import_public(args.input)
            print("Public key import completed. Verify its full fingerprint out-of-band before use.")
        elif args.command == "encrypt":
            print(f"Encrypted file created: {manager.encrypt(args.input, args.output, args.recipient)}")
        elif args.command == "decrypt":
            passphrase = getpass.getpass("OpenPGP passphrase: ")
            print(f"Decrypted file created: {manager.decrypt(args.input, args.output, passphrase)}")
        elif args.command == "sign":
            passphrase = getpass.getpass("OpenPGP passphrase: ")
            print(f"Detached signature created: {manager.sign(args.input, args.output, args.fingerprint, passphrase)}")
        elif args.command == "verify":
            fingerprint = manager.verify(args.signature, args.input)
            print("Signature: VALID")
            print(f"Signing fingerprint: {fingerprint}")
        return 0
    except OpenPGPError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
