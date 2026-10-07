"""age encryption adapter."""

from pathlib import Path
import subprocess


class AgeEncryption:
    def __init__(self, executable: str = "age") -> None:
        self.executable = executable

    def available(self) -> bool:
        try:
            result = subprocess.run([self.executable, "--version"], check=False, capture_output=True, text=True)
        except OSError:
            return False
        return result.returncode == 0

    def encrypt_with_passphrase(self, source: Path, destination: Path, passphrase: str) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            [self.executable, "--passphrase", "--output", str(destination), str(source)],
            input=passphrase + "\n", text=True, capture_output=True, check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "age encryption failed")
