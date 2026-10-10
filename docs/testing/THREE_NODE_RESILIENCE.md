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
8. Fail the test if either receiver cannot retrieve identical content after node 0 has stopped.

## What a passing result proves

A passing result demonstrates that, within this controlled test runner, the two receiving nodes retained pinned copies of the test fixture and could read those copies after the publisher process was stopped.

## What it does not prove

- It does not prove automatic replication: the test explicitly pins content on both receiving nodes.
- It does not prove persistence across a device reboot or power loss.
- It does not prove communication across separate physical devices, NATs, or public networks.
- It does not prove that arbitrary content is always available in IPFS.
- It does not prove production-grade durability, backup policy, or security.

The test uses three Kubo processes on one Ubuntu GitHub Actions runner. A later physical-device test should repeat the scenario across separate devices and network paths.
