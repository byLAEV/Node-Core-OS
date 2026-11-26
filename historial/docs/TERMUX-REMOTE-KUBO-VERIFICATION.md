# Termux Remote Kubo Read Verification

## Scope

Verify that an existing Node Core OS identity running in Termux retrieves a synthetic remote content object, checks its bytes, and submits a signed receipt for the same workflow run.

## Existing entry points

- Workflow: [termux-remote-kubo-read.yml](../.github/workflows/termux-remote-kubo-read.yml)
- Helper: [termux_remote_kubo_read.py](../tools/termux_remote_kubo_read.py)
- Tests: [test_termux_remote_kubo_read.py](../tests/test_termux_remote_kubo_read.py)

Confirm these paths exist on the commit under test before relying on them.

## Required validation

1. Read the synthetic content from the intended Kubo peer.
2. Calculate SHA-256 over the received raw bytes and compare it with the run's expected digest.
3. Load the existing persistent identity. Never generate a new identity to make a test pass.
4. Sign a canonical payload containing schema, run nonce, node ID, CID, and SHA-256.
5. Verify the signature and compare the node ID to an independently supplied expected identity.
6. Reject an old or mismatched nonce, wrong CID, wrong digest, duplicate receipt, malformed payload, or invalid signature.
7. Keep Kubo's administrative API bound to loopback; never expose port 5001 publicly.
8. Run as a normal user and fail if UID is zero.

## Evidence and outcomes

Store only synthetic test data, the validated receipt, non-secret public identity data, timestamps, and diagnostic outcomes. Never upload private keys, seed phrases, credentials, or personal content.

- PASS: the live test ran and all remote checks passed.
- FAIL: the live test ran and any required check failed.
- SKIPPED: the event/condition did not launch the test.
- INCOMPLETE: it ran but the expected receipt or enough evidence was not obtained.

The manual workflow being skipped on a pull request is not proof of a successful remote read.
