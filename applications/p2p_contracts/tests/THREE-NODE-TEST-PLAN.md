# P2P Contracts v0.1 — Three-Node Field Test Plan

## Purpose

Verify the installed Node Core OS P2P Contracts application on three physically separate nodes (A, B, and C). This field test complements, but is not replaced by, the automated test that runs three independent Kubo daemons on one CI host.

## Preconditions

- Install the same reviewed Node Core OS commit on A, B, and C.
- Each node must have a distinct Kubo peer ID and its own Kubo repository.
- Each node must have Kubo PubSub enabled and the daemon restarted after configuration.
- Confirm each node can see the other two peer IDs using the existing Node Core OS network menu.
- Keep all three Node Core OS applications and Kubo daemons running during the ten-minute window.
- Use test contact details and non-sensitive identity fields. Do not use real BTC or settle an actual exchange.
- Record the commit SHA, Kubo version, node peer IDs, timestamps, proposal hash, and manifest hash from each node.

## Test 1 — Node A opens a propagation

1. On A, open Node Core OS → P2P Contracts → Create Public Request.
2. Choose Check Propagation Hash Status and confirm there is no active proposal.
3. Choose Accept a New Propagation Hash.
4. Fill in A's own BTC exchange request draft and explicitly select which identity fields are allowed to be published.
5. Accept the propagation.
6. Record A's peer ID, proposal hash, accepted timestamp, and automatic submission timestamp.
7. Leave A running. Do not manually create another owner request during this propagation.

Expected result: A announces one proposal and has a local draft that is not yet in the public manifest.

## Test 2 — Node B submits during A's window

1. On B, open Create Public Request → Check Propagation Hash Status.
2. Confirm B reports A's proposal hash and A's peer ID as the unique active proposal.
3. Choose Submit a BTC Exchange Request to the Active Propagation.
4. Enter a small test amount of BTC, a test receive asset/amount, and a test contact method.
5. Submit before A's displayed ten-minute submission timestamp.
6. Record B's request ID and the acknowledgement from A.

Expected result: B's request is saved locally as pending but is not committed into B's manifest before A publishes the canonical batch. A queues B's request and acknowledges receipt.

## Test 3 — A publishes the canonical batch

1. Keep A running until its displayed automatic submission timestamp.
2. Wait for the automatic submission message on A.
3. Record A's owner request ID, batch request count, and final manifest hash.
4. Do not manually re-create either request.

Expected result: A's owner request and B's queued request are committed in one manifest transition and sent as one canonical batch.

## Test 4 — Three-node manifest convergence

On A, B, and C:

1. Open Search Request ID and search for A's owner request ID.
2. Search for B's request ID.
3. Record each node's manifest hash and the visible request/evidence state.
4. Compare all three nodes' current manifest hashes.

Expected result: all three nodes can find both requests and report the same current manifest hash. If a node missed the parent manifest or has a different head, it must reject the transition rather than silently overwrite its state; investigate that node before continuing.

## Test 5 — Closure evidence and reputation

1. On C, search for A's request ID to confirm it has synchronized.
2. Choose Create Request Closure.
3. Enter A's request ID, A's peer ID as the evaluated counterparty, a test rating from 1 to 5, a final state such as exchange_completed, and a clear test statement.
4. Confirm the evidence broadcast.
5. On A and B, search the same request ID and confirm the closure evidence has arrived.
6. Record the new manifest hash on all three nodes.

Expected result: all three nodes show the same final request state, the same evidence ID and rating, and the same new manifest hash. The evidence is still self-reported; this test proves synchronization and hash validation, not that an actual exchange occurred.

## Test 6 — Search and duplicate handling

1. Search both request IDs on each node again.
2. Confirm each request appears once and the closure evidence appears once.
3. Restart the P2P Contracts interface (without deleting any data) and repeat the searches.
4. Confirm the current manifest hash remains unchanged after duplicate messages are seen.

Expected result: duplicate messages do not create duplicate manifest entries or alter the canonical head.

## Failure conditions

Mark the field test FAILED if any of the following occurs:

- B cannot discover A's active proposal while the nodes are connected.
- A does not acknowledge B's request during the open window.
- The owner request and peer requests do not appear in the same canonical batch.
- Any of the three nodes has a different manifest hash after synchronization has completed.
- A request or evidence hash validation error is ignored rather than surfaced.
- A closure record appears on one node but cannot be found on the others after the broadcast timeout and retry.
- A duplicate request or evidence ID creates a second manifest entry.

## Report template

- Tested commit:
- Kubo version:
- Node A peer ID:
- Node B peer ID:
- Node C peer ID:
- Proposal hash:
- Owner request ID:
- Peer request ID:
- Closure evidence ID:
- Manifest hash after request batch on A/B/C:
- Manifest hash after closure evidence on A/B/C:
- Result for each test:
- Error output/logs:
- Approximate UTC timestamps:

Do not mark the physical three-node field test as passed until the recorded evidence from all three separate devices has been compared.
