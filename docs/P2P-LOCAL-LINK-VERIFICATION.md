# Local P2P Link Verification

## Scope

Verify one direct native Node Core OS peer link independently from Kubo/IPFS and multi-node state synchronization.

## Required evidence

- Expected peer node ID is already trusted through the existing trust workflow.
- The connection uses the native P2P service and its existing authenticated transport.
- A challenge/request identifier is echoed in the response.
- The response is authenticated against the trusted peer certificate/identity.
- Record elapsed monotonic time and the result without converting missing measurements to zero.
- Report listener, discovery, trust, and transport failures separately.

## Rejection criteria

Reject an unknown peer, invalid certificate/signature, unexpected peer identity, malformed response, replayed challenge, timeout, or execution as UID 0.

## Latency

A 3-second handshake objective may be measured as a performance threshold, but it must be reported as a test requirement rather than a universal guarantee. Keep connection establishment latency separate from steady-state RTT.

## Not proven by this test

A direct link does not prove relay-free WAN reachability, mesh propagation, consensus, or IPFS availability.

## Test entry points

Use the native P2P service and existing tests in the repository. Do not claim `tools/p2p_local_link_test.py`, `tests/test_p2p_local_link.py`, or a dedicated workflow exists until those paths are present on the tested branch.
