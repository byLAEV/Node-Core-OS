"""age encryption adapter using a Linux pseudo-terminal for passphrase mode."""

import errno
import os
from pathlib import Path
import pty
import select
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
        if not passphrase:
            raise ValueError("Encryption passphrase cannot be empty.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        master_fd, slave_fd = pty.openpty()
        process = subprocess.Popen(
            [self.executable, "--passphrase", "--output", str(destination), str(source)],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            close_fds=True,
        )
        os.close(slave_fd)
        transcript = bytearray()
        prompts_sent = 0
        try:
            while process.poll() is None:
                ready, _, _ = select.select([master_fd], [], [], 0.5)
                if not ready:
                    continue
                try:
                    chunk = os.read(master_fd, 4096)
                except OSError as exc:
                    if exc.errno == errno.EIO:
                        break
                    raise
                if not chunk:
                    break
                transcript.extend(chunk)
                lower = bytes(transcript).lower()
                if prompts_sent == 0 and b"enter passphrase" in lower:
                    os.write(master_fd, (passphrase + "\n").encode())
                    prompts_sent = 1
                    transcript.clear()
                elif prompts_sent == 1 and b"repeat passphrase" in lower:
                    os.write(master_fd, (passphrase + "\n").encode())
                    prompts_sent = 2
                    transcript.clear()
        finally:
            os.close(master_fd)

        returncode = process.wait()
        if returncode != 0:
            destination.unlink(missing_ok=True)
            raise RuntimeError("age encryption failed.")
        if prompts_sent != 2:
            destination.unlink(missing_ok=True)
            raise RuntimeError("age passphrase prompt protocol was not completed.")
        destination.chmod(0o600)
