"""Minimal Pinata V3 client using only Python's standard library."""

from pathlib import Path
import json
import mimetypes
import secrets
import urllib.error
import urllib.request


class PinataClient:
    upload_url = "https://uploads.pinata.cloud/v3/files"

    def __init__(self, credential_path: Path) -> None:
        self.credential_path = credential_path

    def has_credential(self) -> bool:
        return self.credential_path.is_file() and bool(self.credential_path.read_text(encoding="utf-8").strip())

    def save_credential(self, jwt: str) -> None:
        if not jwt.strip():
            raise ValueError("Pinata credential cannot be empty.")
        self.credential_path.parent.mkdir(parents=True, exist_ok=True)
        self.credential_path.write_text(jwt.strip() + "\n", encoding="utf-8")
        self.credential_path.chmod(0o600)

    def remove_credential(self) -> None:
        self.credential_path.unlink(missing_ok=True)

    def _credential(self) -> str:
        if not self.has_credential():
            raise RuntimeError("Pinata credential is not configured.")
        return self.credential_path.read_text(encoding="utf-8").strip()

    def upload_file(self, path: Path) -> dict[str, object]:
        path = Path(path)
        if not path.is_file():
            raise FileNotFoundError(path)
        if path.suffix.lower() != ".ncb":
            raise ValueError("Only encrypted .ncb backups may be uploaded to Pinata.")
        boundary = "----NodeCore" + secrets.token_hex(16)
        body = bytearray()
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(b'Content-Disposition: form-data; name="network"\r\n\r\nprivate\r\n')
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(
            f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'.encode()
        )
        body.extend(
            f"Content-Type: {mimetypes.guess_type(path.name)[0] or 'application/octet-stream'}\r\n\r\n".encode()
        )
        body.extend(path.read_bytes())
        body.extend(f"\r\n--{boundary}--\r\n".encode())

        request = urllib.request.Request(
            self.upload_url,
            data=bytes(body),
            method="POST",
            headers={
                "Authorization": f"Bearer {self._credential()}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Pinata upload failed ({exc.code}): {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Pinata connection failed: {exc.reason}") from exc

        data = payload.get("data")
        if not isinstance(data, dict) or not data.get("cid"):
            raise RuntimeError("Pinata returned an invalid upload response.")
        return data
