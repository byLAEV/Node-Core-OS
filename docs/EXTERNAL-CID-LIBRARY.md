# External CID Library

**Status:** Initial local reference management implementation. Kubo-backed retrieval, pinning, unpinning, and pin-status checks are implemented through the existing Kubo manager; live network behavior must be tested against a running Kubo daemon.

## Purpose

The External CID Library stores references to content identified by CIDs without mixing those references with content that Node Core added to its own content registry.

The library stores its JSON index at:

`<local_storage_path>/registry/external-cids.json`

Each reference contains a unique reference ID, CID, description, source node, UTC creation time, and notes.

## Operations

- Add a reference and its descriptive metadata.
- Browse references and search their fields.
- View a reference by its reference ID.
- Edit descriptive metadata.
- Retrieve content by CID to a user-selected local file path.
- Pin content on the local Kubo node.
- Query local pin status from Kubo's pin list.
- Unpin content from the local Kubo node.
- Remove a reference from the local index.

## Important semantics

- Saving a reference does not prove the content is available.
- Retrieving content requires Kubo to be running and able to resolve the CID.
- A successful retrieval proves that this node retrieved bytes at that time; it does not establish authenticity or truth.
- Pin status is queried from Kubo rather than inferred from the reference record.
- Removing a reference only removes the local index entry. It does not unpin or delete IPFS content.
- Unpinning affects this node's pin state only and does not guarantee network-wide deletion.
- CID syntax checks follow the current Kubo manager's supported-format checks. These checks are not a substitute for successfully resolving the CID.
- The JSON index is local metadata and is not itself replicated or synchronized across nodes.

## Verification

The unit tests use a mocked Kubo manager to verify local persistence and delegation. They do not replace integration tests against a running Kubo daemon and real network content.
