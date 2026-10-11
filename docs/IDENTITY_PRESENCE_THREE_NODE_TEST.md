# Identity association presence: minimal three-node milestone

This milestone shares a public declaration and a common report without publishing
identity-document data. It is an initial design/testing stage, not an identity
verification or consensus protocol.

## Public declaration

Each node creates its own declaration from its real Kubo peer ID and local
profile association state. The only identity-related fields sent are the public
peer ID and a boolean `identity_associated`. Receivers label this as
`announced_not_verified`. Names, document numbers, dates of birth, photographs,
and other profile fields are not serialized.

## Minimal exchange flow

1. Start Kubo independently on each node.
2. In **Network / Nodes → Identity Presence**, create an announcement.
3. Publish/share the announcement file's CID with the other nodes.
4. Each receiver imports that announcement by CID. The content must be retrievable
   through its own Kubo node; the receiver saves it locally.
5. Collect the required declarations on one node and create a report.
6. Publish the report. Node Core saves the report locally, adds it to IPFS with
   pinning enabled, and checks that the CID appears in the local pin list.
7. Share that report CID with the other two nodes. Each imports it, saves the
   exact received bytes as its current local report, pins the CID locally, and
   verifies the pin.
8. Compare the report CID/reference and file bytes on all three nodes.

This is an explicit CID-exchange workflow for the first minimal implementation.
It uses Kubo/IPFS as the content transport; it does not yet implement automatic
background PubSub or discovery. The CID must be conveyed to the receiver (for
example through the node operator or a local synchronization folder). The next
milestone can automate CID exchange after this end-to-end path is proven.

## Report semantics

- `known_nodes` counts distinct public peer IDs with valid announcements.
- `connected_nodes` is this node plus directly connected peers at report creation;
  it is an observation, not a network-wide consensus value.
- `identity_associations_announced` counts distinct nodes whose declaration is
  `true`.
- `identity_documents_transmitted` and `personal_identity_fields_transmitted`
  are always zero for this protocol.
- One node creates the shared report; all other nodes import the same report CID.
  Independently creating reports on each node would produce different timestamps
  and reference IDs and therefore different CIDs.

## Limitations

A CID identifies content but does not authenticate who made a claim. A successful
pin check proves only that the local Kubo node reports the CID as pinned. It does
not prove the human identity, independent availability across the whole network,
or consensus. Do not publish private identity-profile files.
