"""Local SHA-256 evidence for Node Core OS persistent state.

The manifest records digests and relative paths only; it never copies file contents.
Because the identity scope includes the NODE ID private-key file, manifests must
remain local and private. Do not upload them to public CI artifacts or issues.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Any, Mapping


MANIFEST_SCHEMA_VERSION = 1
KUBO_VOLATILE_PATHS = frozenset(
    {
        "api",
        "repo.lock",
        "datastore/LOCK",
        "node-core.pid",
        "node-core-daemon.log",
    }
)
REQUIRED_IDENTITY_FILES = (
    "node.json",
    "private/node.key",
    "profile.json",
    "entity-registry.json",
)


class PersistenceIntegrityError(ValueError):
    """Raised when persistent state cannot be inspected safely."""


def _require_directory(path: Path, label: str) -> Path:
    candidate = path.expanduser()
    try:
        metadata = candidate.lstat()
    except OSError as exc:
        raise PersistenceIntegrityError(
            f"{label} directory is unavailable: {candidate}"
        ) from exc
    if stat.S_ISLNK(metadata.st_mode):
        raise PersistenceIntegrityError(
            f"{label} directory must not be a symbolic link."
        )
    if not stat.S_ISDIR(metadata.st_mode):
        raise PersistenceIntegrityError(f"{label} path is not a directory.")
    return candidate.absolute()


def _require_regular_file(path: Path, label: str) -> Path:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise PersistenceIntegrityError(
            f"Required {label} file is missing or unreadable."
        ) from exc
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise PersistenceIntegrityError(
            f"Required {label} file must be a regular file, not a symbolic link."
        )
    return path


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            while True:
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
    except OSError as exc:
        raise PersistenceIntegrityError(
            f"Could not read a persistent-state file: {path.name}"
        ) from exc
    return digest.hexdigest()


def _record_path(path: Path, relative_path: str) -> dict[str, Any]:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise PersistenceIntegrityError(
            f"Could not inspect persistent-state entry: {relative_path}"
        ) from exc

    if stat.S_ISLNK(metadata.st_mode):
        # Hash the link target string itself. Never follow a symlink out of a
        # persistent data root during an integrity check.
        try:
            link_target = os.readlink(path).encode("utf-8", errors="surrogateescape")
        except OSError as exc:
            raise PersistenceIntegrityError(
                f"Could not inspect symbolic link: {relative_path}"
            ) from exc
        return {
            "path": relative_path,
            "kind": "symlink",
            "size_bytes": len(link_target),
            "sha256": hashlib.sha256(link_target).hexdigest(),
        }

    if not stat.S_ISREG(metadata.st_mode):
        raise PersistenceIntegrityError(
            f"Unsupported special file in persistent state: {relative_path}"
        )

    return {
        "path": relative_path,
        "kind": "file",
        "size_bytes": metadata.st_size,
        "sha256": _sha256_file(path),
    }


def _scan_directory(root: Path, *, exclude_kubo_runtime: bool = False) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []

    for current, directory_names, file_names in os.walk(
        root, topdown=True, followlinks=False
    ):
        current_path = Path(current)
        directory_names.sort()
        file_names.sort()

        retained_directories: list[str] = []
        for directory_name in directory_names:
            path = current_path / directory_name
            relative = path.relative_to(root).as_posix()
            if exclude_kubo_runtime and relative in KUBO_VOLATILE_PATHS:
                continue
            if path.is_symlink():
                entries.append(_record_path(path, relative))
            else:
                retained_directories.append(directory_name)
        directory_names[:] = retained_directories

        for file_name in file_names:
            path = current_path / file_name
            relative = path.relative_to(root).as_posix()
            if exclude_kubo_runtime and relative in KUBO_VOLATILE_PATHS:
                continue
            entries.append(_record_path(path, relative))

    return sorted(entries, key=lambda item: item["path"])


def _scan_file(path: Path) -> list[dict[str, Any]]:
    return [_record_path(path, path.name)]


def _scope(files: list[dict[str, Any]], root_label: str) -> dict[str, Any]:
    return {
        "root": root_label,
        "file_count": len(files),
        "total_bytes": sum(item["size_bytes"] for item in files),
        "files": files,
    }


def capture_persistence_manifest(
    data_dir: str | os.PathLike[str],
    *,
    storage_dir: str | os.PathLike[str] | None = None,
    kubo_repo: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Capture SHA-256 digests for identity, profile, registry, local storage and Kubo."""
    data_root = _require_directory(Path(data_dir), "Node Core OS data root")
    identity_root = _require_directory(data_root / "identity", "identity")
    for relative in REQUIRED_IDENTITY_FILES:
        _require_regular_file(identity_root / relative, relative)

    local_storage = _require_directory(
        Path(storage_dir) if storage_dir is not None else data_root / "storage",
        "local storage",
    )

    configured_kubo_path = kubo_repo
    if configured_kubo_path is None:
        configured_kubo_path = os.environ.get("IPFS_PATH") or str(data_root / "ipfs")
    kubo_root = _require_directory(Path(configured_kubo_path), "Kubo/IPFS repository")

    profile_path = _require_regular_file(identity_root / "profile.json", "identity profile")
    registry_path = _require_regular_file(
        identity_root / "entity-registry.json", "entity registry"
    )

    scopes = {
        "entity_registry": _scope(
            _scan_file(registry_path), "identity/entity-registry.json"
        ),
        "kubo_ipfs": _scope(
            _scan_directory(kubo_root, exclude_kubo_runtime=True),
            "configured Kubo/IPFS repository",
        ),
        "local_storage": _scope(_scan_directory(local_storage), "configured local storage"),
        "node_identity": _scope(_scan_directory(identity_root), "identity"),
        "profile": _scope(_scan_file(profile_path), "identity/profile.json"),
    }

    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "algorithm": "sha256",
        "policy": {
            "symlinks": "hash link target without following it",
            "kubo_excluded_runtime_paths": sorted(KUBO_VOLATILE_PATHS),
        },
        "scopes": scopes,
    }


def compare_persistence_manifests(
    before: Mapping[str, Any], after: Mapping[str, Any]
) -> dict[str, Any]:
    """Compare two manifests by scope, relative path, file kind, size and digest."""
    for manifest in (before, after):
        if (
            manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION
            or manifest.get("algorithm") != "sha256"
            or not isinstance(manifest.get("scopes"), Mapping)
        ):
            raise PersistenceIntegrityError("Unsupported or invalid persistence manifest.")

    def flatten(manifest: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for scope_name, scope_data in manifest["scopes"].items():
            if not isinstance(scope_data, Mapping) or not isinstance(
                scope_data.get("files"), list
            ):
                raise PersistenceIntegrityError("Invalid scope data in persistence manifest.")
            for item in scope_data["files"]:
                if not isinstance(item, Mapping) or not isinstance(item.get("path"), str):
                    raise PersistenceIntegrityError("Invalid file entry in persistence manifest.")
                key = f"{scope_name}/{item['path']}"
                result[key] = dict(item)
        return result

    before_files = flatten(before)
    after_files = flatten(after)
    before_keys = set(before_files)
    after_keys = set(after_files)

    added = sorted(after_keys - before_keys)
    removed = sorted(before_keys - after_keys)
    changed = sorted(
        key
        for key in before_keys & after_keys
        if any(
            before_files[key].get(field) != after_files[key].get(field)
            for field in ("kind", "size_bytes", "sha256")
        )
    )
    before_scopes = set(before["scopes"])
    after_scopes = set(after["scopes"])
    added_scopes = sorted(after_scopes - before_scopes)
    removed_scopes = sorted(before_scopes - after_scopes)
    policy_changed = before.get("policy") != after.get("policy")

    matches = not (
        added or removed or changed or added_scopes or removed_scopes or policy_changed
    )
    return {
        "matches": matches,
        "added": added,
        "removed": removed,
        "changed": changed,
        "added_scopes": added_scopes,
        "removed_scopes": removed_scopes,
        "policy_changed": policy_changed,
    }


def write_persistence_manifest(
    output_path: str | os.PathLike[str], manifest: Mapping[str, Any]
) -> Path:
    """Write a manifest atomically with owner-only permissions (0600)."""
    target = Path(output_path).expanduser().absolute()
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".node-core-persistence-", suffix=".tmp", dir=target.parent
    )
    temporary_path = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(manifest, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, target)
        os.chmod(target, 0o600)
    except Exception:
        try:
            os.close(descriptor)
        except OSError:
            pass
        try:
            temporary_path.unlink()
        except OSError:
            pass
        raise
    return target


def read_persistence_manifest(path: str | os.PathLike[str]) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PersistenceIntegrityError("Could not read the persistence manifest.") from exc
    if not isinstance(payload, dict):
        raise PersistenceIntegrityError("Persistence manifest must be a JSON object.")
    return payload


def _summary(manifest: Mapping[str, Any]) -> dict[str, Any]:
    scopes = manifest["scopes"]
    return {
        name: {
            "file_count": scope["file_count"],
            "total_bytes": scope["total_bytes"],
        }
        for name, scope in sorted(scopes.items())
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Capture or compare private SHA-256 persistence evidence."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    capture = commands.add_parser("capture", help="Capture a private persistence manifest.")
    capture.add_argument(
        "--data-dir",
        default=os.environ.get("NODE_CORE_DATA_DIR", str(Path.home() / ".node-core")),
    )
    capture.add_argument("--storage-dir")
    capture.add_argument("--kubo-repo")
    capture.add_argument("--output", required=True)

    compare = commands.add_parser("compare", help="Compare two private persistence manifests.")
    compare.add_argument("--before", required=True)
    compare.add_argument("--after", required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "capture":
            manifest = capture_persistence_manifest(
                args.data_dir,
                storage_dir=args.storage_dir,
                kubo_repo=args.kubo_repo,
            )
            output = write_persistence_manifest(args.output, manifest)
            print(
                json.dumps(
                    {
                        "status": "captured",
                        "manifest_file_mode": "0600",
                        "scopes": _summary(manifest),
                    },
                    sort_keys=True,
                )
            )
            return 0

        before = read_persistence_manifest(args.before)
        after = read_persistence_manifest(args.after)
        result = compare_persistence_manifests(before, after)
        print(
            json.dumps(
                {
                    "status": "match" if result["matches"] else "mismatch",
                    "added_count": len(result["added"]),
                    "removed_count": len(result["removed"]),
                    "changed_count": len(result["changed"]),
                    "added_scope_count": len(result["added_scopes"]),
                    "removed_scope_count": len(result["removed_scopes"]),
                    "policy_changed": result["policy_changed"],
                },
                sort_keys=True,
            )
        )
        return 0 if result["matches"] else 1
    except (OSError, PersistenceIntegrityError) as exc:
        parser.exit(2, f"persistence-integrity: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
