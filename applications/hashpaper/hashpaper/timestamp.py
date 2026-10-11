"""OpenTimestamps CLI adapter for HashPaper.

This module delegates timestamp operations to the official `ots` executable.
It does not implement cryptography or infer verification from file existence.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Sequence


class TimestampError(RuntimeError):
    """Raised when an OpenTimestamps operation cannot be completed safely."""


@dataclass(frozen=True)
class TimestampResult:
    operation: str
    status: str
    proof_file: str | None
    proof_verification: str
    original_sha256: str | None
    return_code: int | None
    stdout: str
    stderr: str
    bitcoin_block_height: int | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class OpenTimestampsClient:
    """Safe wrapper around the official `ots` command-line client."""

    def __init__(self, executable: str = "ots", timeout_seconds: int = 120) -> None:
        self.executable = executable
        self.timeout_seconds = timeout_seconds

    def _executable_path(self) -> str:
        # Prefer the executable managed by Node Core OS. A globally installed
        # command may belong to another Python environment or be incompatible.
        if self.executable == "ots":
            configured = os.environ.get("NODE_CORE_OTS_EXECUTABLE")
            candidates = []
            if configured:
                candidates.append(Path(os.path.expandvars(configured)).expanduser())
            data_dir = Path(
                os.environ.get("NODE_CORE_DATA_DIR", str(Path.home() / ".node-core"))
            ).expanduser()
            candidates.append(data_dir / "runtime" / "opentimestamps-venv" / "bin" / "ots")
            for candidate in candidates:
                if candidate.is_file() and os.access(candidate, os.X_OK):
                    return str(candidate)

        path = shutil.which(self.executable)
        if path is not None:
            return path

        raise TimestampError(
            "OpenTimestamps client 'ots' was not found. The Node Core OS installer, "
            "updater, or HashPaper installer must install the official "
            "opentimestamps-client package in the current user's private environment "
            "under '~/.node-core/runtime/opentimestamps-venv/bin/ots'. "
            "Do not run HashPaper or its installer as root."
        )

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _run(self, args: Sequence[str]) -> subprocess.CompletedProcess[str]:
        executable = self._executable_path()
        try:
            return subprocess.run(
                [executable, *args],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise TimestampError(
                f"OpenTimestamps command timed out after {self.timeout_seconds} seconds."
            ) from exc
        except OSError as exc:
            raise TimestampError(f"Unable to execute OpenTimestamps client: {exc}") from exc

    @staticmethod
    def _combined_output(result: subprocess.CompletedProcess[str]) -> str:
        return (result.stdout + "\n" + result.stderr).strip()

    @staticmethod
    def _block_height(output: str) -> int | None:
        match = re.search(r"Bitcoin block\s+(\d+)\s+attests", output, re.IGNORECASE)
        return int(match.group(1)) if match else None

    def stamp(self, original_path: Path) -> TimestampResult:
        original = Path(original_path).expanduser()
        if not original.is_file():
            raise TimestampError(f"Original document does not exist: {original}")
        if original.name.endswith(".ots"):
            raise TimestampError("The original document path must not end in .ots.")
        proof = Path(str(original) + ".ots")
        if proof.exists():
            raise TimestampError(f"Proof already exists; refusing to overwrite it: {proof}")

        before = self._sha256(original)
        result = self._run(["stamp", str(original)])
        after = self._sha256(original)
        if before != after:
            raise TimestampError("The original document changed during timestamp submission.")
        if result.returncode != 0 or not proof.is_file() or proof.stat().st_size == 0:
            output = self._combined_output(result)
            raise TimestampError(
                "OpenTimestamps did not create a usable proof file. "
                f"Exit code: {result.returncode}. Output: {output or '(empty)'}"
            )
        return TimestampResult(
            operation="stamp",
            status="WAITING_FOR_BITCOIN",
            proof_file=str(proof),
            proof_verification="NOT_VERIFIED",
            original_sha256=after,
            return_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )

    def check(self, original_path: Path, *, upgrade: bool = False) -> TimestampResult:
        original = Path(original_path).expanduser()
        if not original.is_file():
            raise TimestampError(f"Original document does not exist: {original}")
        proof = Path(str(original) + ".ots")
        if not proof.is_file() or proof.stat().st_size == 0:
            raise TimestampError(f"OpenTimestamps proof is missing or empty: {proof}")

        original_hash = self._sha256(original)
        backup: Path | None = None
        operation = "verify"
        if upgrade:
            operation = "upgrade"
            backup = Path(str(proof) + ".before-upgrade")
            suffix = 1
            while backup.exists():
                backup = Path(str(proof) + f".before-upgrade.{suffix}")
                suffix += 1
            shutil.copy2(proof, backup)

        try:
            args = (["upgrade", str(proof)] if upgrade else ["verify", str(proof)])
            result = self._run(args)
        except Exception:
            # An interrupted upgrade may have modified the proof before the
            # client timed out or failed. Keep the backup unless the current
            # proof is byte-for-byte identical to it.
            if backup is not None and backup.exists() and proof.is_file():
                if backup.read_bytes() == proof.read_bytes():
                    backup.unlink()
            raise

        output = self._combined_output(result)
        if upgrade and result.returncode == 0:
            # Keep the backup when the official client changed the proof; the old
            # evidence remains available for inspection and rollback.
            if backup is not None and backup.exists() and backup.read_bytes() == proof.read_bytes():
                backup.unlink()

        if result.returncode == 0 and re.search(r"Success!.*Bitcoin block\s+\d+\s+attests", output, re.IGNORECASE | re.DOTALL):
            status = "VERIFIED"
            verification = "SUCCESS"
        elif re.search(r"Pending confirmation in Bitcoin blockchain", output, re.IGNORECASE):
            status = "WAITING_FOR_BITCOIN"
            verification = "PENDING"
        elif result.returncode == 0 and upgrade and re.search(r"Timestamp is complete", output, re.IGNORECASE):
            # A successful upgrade indicates completion, but only verify confirms
            # the proof against the original document. Do not claim VERIFIED here.
            status = "ANCHOR_AVAILABLE"
            verification = "NOT_CHECKED_AFTER_UPGRADE"
        elif result.returncode != 0 and re.search(r"calendar|network|connection|timeout|unavailable", output, re.IGNORECASE):
            status = "NETWORK_ERROR"
            verification = "NOT_VERIFIED"
        elif result.returncode != 0:
            status = "PROOF_ERROR"
            verification = "FAILED_OR_NOT_VERIFIED"
        else:
            status = "NOT_CHECKED"
            verification = "NOT_CHECKED"

        # The original bytes are never written by this adapter.
        if self._sha256(original) != original_hash:
            raise TimestampError("The original document changed during proof verification.")

        return TimestampResult(
            operation=operation,
            status=status,
            proof_file=str(proof),
            proof_verification=verification,
            original_sha256=original_hash,
            return_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            bitcoin_block_height=self._block_height(output) if status == "VERIFIED" else None,
        )
