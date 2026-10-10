# Node Core OS — Implementation Architecture

Infrastructure -> Runtime -> BIOS/Core -> Content Registry -> Identity/Protocols -> Applications.

## Node Core BIOS

BIOS is the administrative boundary of the Node.

### Storage

Storage owns the local Node storage root and safe filesystem access. Its state is
independent from the Kubo repository.

### IPFS / Kubo

BIOS owns Kubo infrastructure:

Detect -> Initialize -> Configure -> Start -> Status -> Stop

Kubo is treated as an external node service. Node Core does not reimplement Kubo
or expose its administrative RPC as the application API.

## Node Core Content v1

The completed content path is:

Add -> CID -> Registry -> Publish -> Share
                         |        |
                         |        +-> ipfs://CID
                         |        +-> gateway /ipfs/CID
                         |
                         +-> Pin / Unpin
                         |
                         +-> Retrieve

### CID Registry

The local registry is Node Core's durable index of content it knows about. It is
not a replacement for IPFS and does not become the source of truth for content.

Current record fields:

- CID
- name
- size
- creation timestamp
- pin state
- original local source path
- optional owner identity
- provenance metadata
- publication timestamp
- publication mode

Registry storage:

~/.node-core/storage/registry/content.json

### Publication semantics

Content v1 deliberately uses **CID publication**, not IPNS. Publish records that
a registered resource is published by the Node Core content layer and pins it by
default so the local Kubo node retains it.

Share produces portable references from the CID. It does not grant permissions and
does not expose the administrative Kubo RPC.

IPNS/key-backed naming belongs above this layer because it will require identity and
cryptographic key management.

## Identity activity, personhood, and evidence (future layers)

The specifications below define planned capabilities and are not claims of existing
runtime functionality:

- [Identity Function Proof, Preference Propagation, and Consensus](IDENTITY-FUNCTION-PROOF.md)
  defines activity evidence, preference protocols, propagation states, consensus/finality,
  freshness, and contextual reputation.
- [Personhood Verification, Evidence Categories, and Selective Disclosure](IDENTITY-PERSONHOOD-AND-SELECTIVE-EVIDENCE.md)
  defines policy-bound personhood assessment, constancy-history metrics, evidence
  categories, privacy boundaries, and future zero-knowledge selective disclosure.

The architecture separates the identity's activity history from personhood assessment,
node availability, credential validity, and third-party authorization. A long valid
history may measure constancy, but it cannot alone prove that the identity belongs to
a real person. That claim requires a qualifying personhood procedure and must remain
bound to its policy and validity period. A preference vote alone is not a human test.

Evidence labels such as professional, cultural, family, intimate, health, sports,
academic, financial, and citizenship are classification metadata, not proof that a
claim is true. Each credential needs its own issuer/authenticity, validity, and
revocation checks. Zero-knowledge proofs may later support selective disclosure, but
they do not independently establish the truth of an underlying claim.

Local storage and Kubo/IPFS are complementary. A CID does not prove authenticity,
consensus acceptance, persistence, or confidentiality. Sensitive evidence must be
private or encrypted by design; public manifests must not reveal sensitive labels
by default.

The current identity implementation is a local structural/time validator only. It
does not verify signatures cryptographically, establish that an identity is a real
person, implement anti-Sybil controls, propagate evidence across peers, run distributed
consensus, issue personal credentials, or generate ZKPs. The next phases must define
the threat model, schemas, cryptographic contracts, and tests before network behavior
is claimed.

## Remembering & Forgetting (future layer)

The [Remembering & Forgetting specification](REMEMBERING-FORGETTING.md) extends the existing Forget / Remember Context Model. It distinguishes requirement-driven selective recall from data deletion and defines future work for context selection, access, validity, retention, revocation, local deletion, and Kubo/IPFS lifecycle operations.

This is a planned layer, not a claim of current runtime functionality. Before implementation, audit existing content registry and storage contracts. Do not treat context forgetting, revocation, unpinning, and deletion as equivalent. In particular, local unpinning or reference removal does not establish network-wide deletion.

The public [Remembering & Forgetting roadmap](../web-test-bench/remembering.html) explains the model and its planned implementation phases.

## Storage layout

~/.node-core/
  config.json
  storage/
    registry/
      content.json
  ipfs/
