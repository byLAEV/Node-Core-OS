# Node Core OS P2P Contracts — Version 0.1 (development)

## Status

This is an experimental development version with an English terminal interface. It supports public BTC-for-asset requests, request closure/reputation evidence, local request search, and experimental Kubo PubSub synchronization between connected nodes.

## Main menu

1. Create Public Request
2. Create Private Request (disabled; OpenPGP is not implemented)
3. Create Request Closure
4. Search Request ID

The operator must consent to local use of the existing Node Core OS identity profile before entering the menu. Every public request separately asks which personal identity fields may be published. The node peer ID is added automatically. No private key is requested or generated.

## Public propagation flow

The public request submenu offers:

- Check Propagation Hash Status
- Accept a New Propagation Hash
- View Propagation Status
- Create This Node's BTC Exchange Request (unlocked after the node's own ten-minute window)
- Submit a BTC Exchange Request to the Active Propagation (for a peer submitting to another node)

A node prepares its own public BTC exchange request as a local draft before it accepts a propagation hash. It then announces the proposal and opens a ten-minute request-collection window. Other nodes query peers and, if they observe one unique active proposal, can submit a public BTC exchange request to the proposing node. The receiving node queues valid request documents. When the ten-minute timer elapses, an active application automatically commits the owner's prepared request together with queued peer requests in one manifest transition and broadcasts that exact canonical manifest plus its request documents. Receiving peers verify the hash, parent hash, sequence, append-only request index and document hashes, then install the same manifest bytes so synchronized nodes converge on the same manifest hash. Public request broadcasts and closure evidence are hash-validated and imported by peers that receive them.

Kubo PubSub topic: node-core-os/p2p-contracts/propagation/v1.

Kubo PubSub must be enabled in each node's Kubo configuration (Pubsub.Enabled=true) and Kubo must be restarted. The application does not silently change an existing node's Kubo configuration.

For an existing installation, set the correct Node Core Kubo repository before enabling PubSub:

    export IPFS_PATH="$HOME/.node-core/ipfs"
    if [ -x "$HOME/.node-core/bin/ipfs" ]; then
      KUBO="$HOME/.node-core/bin/ipfs"
    else
      KUBO="${PREFIX:?Termux PREFIX is required}/bin/ipfs"
    fi
    "$KUBO" config --json Pubsub.Enabled true

Then stop and start the Kubo daemon from Node Core OS. The daemon launcher detects whether the installed Kubo version requires the --enable-pubsub-experiment flag and uses it only when that flag is supported. Do not run a second daemon against the same IPFS_PATH.

## Local tests

From the repository root:

    python -m unittest applications.p2p_contracts.tests.test_service applications.p2p_contracts.tests.test_propagation -v

These tests do not require a running Kubo daemon.

## Three independent real Kubo daemons (local integration)

The integration test creates three separate temporary Kubo repositories and daemons, connects them as peers, then tests:

1. Node A announces a propagation hash.
2. Node B discovers A's active proposal.
3. B sends a BTC exchange request to A.
4. A imports the received request batch into its manifest and broadcasts it.
5. A publishes its own BTC exchange request; B and C synchronize it.
6. C creates closure evidence with a rating and publishes it.
7. A, B, and C search the request ID and verify the synchronized final state and evidence.

It does not modify or use an existing user's Kubo repository. It shortens the timer in the test fixture after checking that the production constant is 600 seconds; it does not wait ten real minutes.

Run it with an installed Kubo CLI:

    IPFS_BIN="$(command -v ipfs)" python applications/p2p_contracts/tests/three_node_real_kubo.py

GitHub Actions also runs this integration test using a pinned Kubo CLI version. Three local daemons on one machine prove application-level peer synchronization in that environment, but are not a substitute for testing three physically separate, already-installed Node Core OS devices.

## Important limitations

This is not a production consensus protocol. PubSub messages carry claimed node IDs but are not cryptographically signed or authenticated. A malicious peer can spoof fields, and the prototype cannot prove global absence of competing proposals, enforce a network-wide exclusive lease, or prevent Sybil attacks. The query only reflects responses received during its time window.

The ten-minute timeout automatically submits the prepared owner request and queued incoming requests only while the application remains active and can reach Kubo. A peer that missed a previous manifest transition cannot import a later transition until it has recovered the missing parent; automatic multi-step catch-up is not implemented. If the application or node is offline, the lease may expire and the batch will not be submitted. Recovery across crashes, a signed quorum, and a globally authoritative chain head are not implemented. The integration test must pass before calling this version tested.

Closure evidence and reputation ratings are self-reported; they are not independent proof that an exchange occurred. No BTC or other asset transaction is executed. Private requests remain disabled pending real OpenPGP encryption. HashPaper behavior is unchanged.

## Data

Local request, evidence, manifest and propagation state is stored under the configured Node Core OS storage path in p2p_contracts/.
