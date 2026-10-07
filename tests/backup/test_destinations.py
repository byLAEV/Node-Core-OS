from pathlib import Path

from node_core.backup.destinations import FileDestination


def test_file_destination_sets_private_permissions(tmp_path: Path) -> None:
    source = tmp_path / "source.ncb"
    destination = tmp_path / "out" / "backup.ncb"
    source.write_bytes(b"encrypted")
    FileDestination().save(source, destination)
    assert destination.read_bytes() == b"encrypted"
    assert destination.stat().st_mode & 0o777 == 0o600
