# Three-node Kubo resilience test

## Purpose

Verify a bounded resilience property in addition to basic peer connectivity: two receiving Kubo nodes can retrieve a content-addressed fixture after the node that originally published it has stopped.

## Test procedure

1. Start three independent Kubo repositories with unique peer identities.
2. Form a full mesh and verify connectivity.
3. Transfer unique fixtures between all ordered publisher/receiver pairs and compare the received bytes and SHA-256 hashes.
4. Publish a separate resilience fixture on node 0 and record its CID.
5. Explicitly pin that fixture on nodes 1 and 2; confirm each node reports the CID as pinned.
6. Stop node 0.
7. Retrieve the fixture from nodes 1 and 2 by CID, compare bytes, and verify SHA-256.
8. Restart node 0 using the same Kubo repository directory.
9. Verify node 0's peer ID is unchanged and retrieve the pinned fixture after restart.
10. Compare bytes and SHA-256; fail if identity or content differs.
11. Stop node 2 and restart it using the same repository.
12. Verify node 2 retains its peer ID, explicitly reconnect nodes 0 and 1, and confirm they see node 2 as connected.
13. Publish fresh content from node 0 and verify node 2 retrieves identical bytes and SHA-256 after reconnection.

## What a passing result proves

A passing result demonstrates that, within this controlled test runner, the two receiving nodes retained pinned copies of the test fixture and could read those copies after the publisher process was stopped.

## What it does not prove

- It does not prove automatic replication: the test explicitly pins content on both receiving nodes.
- It does not prove persistence across a device reboot or power loss; the added restart check restarts only the Kubo process.
- It does not prove the operating system will automatically start Kubo after a device reboot.
- The reconnection check explicitly issues `swarm connect`; it does not prove automatic peer discovery or automatic reconnection without intervention.
- It does not prove communication across separate physical devices, NATs, or public networks.
- It does not prove that arbitrary content is always available in IPFS.
- It does not prove production-grade durability, backup policy, or security.

The test uses three Kubo processes on one Ubuntu GitHub Actions runner. The restart check verifies the same repository retains its peer identity and explicitly pinned fixture across a Kubo process restart. The reconnection check restarts node 2, verifies its identity, explicitly reconnects it to nodes 0 and 1, and tests a fresh content transfer. A later physical-device test should repeat the scenario across separate devices and network paths.
