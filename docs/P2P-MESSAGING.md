# Native P2P text-message requests

Node Core OS reuses the existing persistent Ed25519 node identity and the native
P2P transport. A canonical node ID has the form
`sha256:<64 lowercase hexadecimal characters>`. It is derived from the public
key and remains stable while the identity files are preserved.

## First implementation

- Messages use the native P2P protocol over mutually authenticated TLS 1.3.
- The sender must have the recipient certificate explicitly trusted locally.
- The recipient must trust the sender certificate and have its native P2P listener
  running. The service accepts only explicitly trusted peers.
- On the local LAN, the menu can use the signed discovery announcement to resolve
  a node ID to a host and port. If that endpoint is unavailable, the operator can
  enter a reachable host and port manually.
- The receiver writes the message to `~/.node-core/p2p/messages.json` as a pending
  inbox request before sending a receipt. The sender records a delivery receipt in
  its local outbox only after receiving that acknowledgment.
- Messages are local-only. They are not added to IPFS/Kubo or published automatically.
- This is a first text-message request flow, not a WAN relay, global directory,
  asynchronous delivery queue, or end-to-end encrypted chat. Availability outside
  the LAN requires a reachable endpoint and suitable network routing. TLS protects
  the connection; the receiver's persisted local inbox is not a claim that the
  recipient has read or accepted the content.

## Menu use

Open **Network / Nodes** and choose **15. Send P2P text-message request**. Enter the
recipient's canonical Node ID; the menu uses a matching signed LAN discovery record
when possible and otherwise asks for an endpoint. Review the message and type
`SEND` to transmit it.

Choose **16. P2P message inbox** on the receiving node to inspect requests and mark
them as read. A successful sender receipt means the recipient's software accepted
the message and persisted it, not that a human read it.

## Interoperability and limits

Protocol messages are versioned JSON objects with a bounded length. Message text is
limited to 4096 Unicode characters. Incoming request IDs are idempotent per sender,
so an identical retry does not create a duplicate inbox item; reusing an ID with
different content is rejected. Message history is bounded and stored with restrictive
local filesystem permissions on POSIX systems.

A Node ID is a technical cryptographic identifier. It does not prove civil identity,
professional qualifications, or general trustworthiness. Only trust certificates
through a separate channel after verifying the fingerprint. Do not copy private
keys between nodes.
