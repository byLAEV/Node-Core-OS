from node_core.backup.manifest import create_manifest, serialize_manifest


def test_manifest_contains_public_metadata_only() -> None:
    payload = serialize_manifest(create_manifest(kubo_version="0.43.1", peer_id="12D3KooW-test", keys=["self"]))
    assert b"node-core-backup" in payload
    assert b"12D3KooW-test" in payload
    assert b"private_key" not in payload
    assert b"pinata" not in payload.lower()
