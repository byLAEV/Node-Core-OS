# Entity Identity and Node Association Model

**Status:** Implemented local registry primitive; distributed identity protocol remains proposed.  
**Version:** 0.1.0  
**Scope:** Generic entity records, technical node references, and references to supporting evidence.

## 1. Purpose

Node Core OS needs a shared identity foundation for its service catalog. The foundation must represent people, organizations, devices, physical or logical objects, services, programs, and other resources without requiring every entity to have a civil identity document.

The initial implementation is a private local registry in `node_core/identity/entity_registry.py`. It does not publish records to Kubo/IPFS, issue certificates, verify civil identity, prove node ownership, or implement distributed consensus.

## 2. Concepts that must remain distinct

- **Entity:** the person, organization, device, object, service, program, or resource being represented.
- **Entity identity record:** the local registry record and its stable `entity_id`.
- **Technical node:** a Node Core OS installation or network participant with its own cryptographic key and node identifier.
- **Node association:** a declared relationship between an entity and a technical node. A declaration is not proof of key control or legal ownership.
- **Identity document:** a document or record that may support a claim about a person or organization. Its existence does not itself mean the document was checked or is authentic.
- **Evidence reference:** a pointer to evidence held elsewhere. The registry does not store raw document contents.
- **Credential:** a signed claim with an issuer, subject, scope, validity and revocation rules. Credential issuance and cryptographic verification are separate capabilities.
- **CID:** a content identifier. It identifies content; it does not by itself prove authorship, identity, permission, truth, confidentiality, or availability.

## 3. Entity types

The first schema accepts these values:

- `person`
- `organization`
- `device`
- `object`
- `service`
- `program`
- `resource`
- `other`

A person may have several technical nodes. A service may run across several nodes. A node may be referenced by multiple entities for different declared relationships. The registry therefore stores node links inside each entity and does not put a single `node_id` on the entity as its identity.

The current implementation supports one-to-many links from an entity to node identifiers. A future graph-wide query and distributed relationship protocol must define how reverse links and conflicts are reconciled across independent registries.

## 4. Local record and privacy boundary

The local file is:

`~/.node-core/identity/entity-registry.json`

The registry applies restrictive POSIX permissions where supported (directory `0700`, file `0600`), writes through a temporary file, and fails closed when stored JSON is malformed or has an unsupported schema version.

A record contains:

- local entity identifier;
- entity type and optional display label;
- local lifecycle status;
- an explicit `declared` identity assurance state;
- node relationship references;
- evidence references marked `unverified`;
- creation, update, and revocation timestamps.

Do not put raw ID numbers, passport images, birth dates, phone numbers, email addresses, private keys, access tokens, or other sensitive fields in public IPFS content. This registry does not need those fields to represent an entity. If an application needs identity-document verification, it must define a separate consent, minimization, access-control, retention, issuer-validation, and revocation process.

## 5. Initial Python interface

```python
from pathlib import Path
from node_core.identity.entity_registry import EntityIdentityRegistry

registry = EntityIdentityRegistry(Path.home() / ".node-core")

person = registry.register_entity("person")
device = registry.register_entity("device", display_name="Synthetic test device")

registry.link_node(
    person["entity_id"],
    "sha256:example-node-id",
    relationship="controlled_by",
)

registry.add_evidence_reference(
    person["entity_id"],
    "identity_document",
    "local-evidence://reference-created-by-the-caller",
)

print(registry.get_entity(person["entity_id"]))
```

The identifiers and references in this example are illustrative. A call to `link_node` records a declared relationship; it does not cryptographically verify control of that node. The evidence reference is marked `unverified` and does not establish that a document is genuine.

## 6. Relationship to existing identity components

- `node_core/identity/node_identity.py` manages a technical node's cryptographic identity.
- `node_core/identity/profile.py` manages a local user-declared personal profile with document fields.
- `node_core/identity/associations.py` verifies control of a node key for a one-time challenge when associating that node with an existing profile.
- `node_core/identity/entity_registry.py` provides a generic entity model and declared node/evidence references.

These components are complementary, not interchangeable. The existing profile's document fields are not a requirement for registering a generic entity such as a device, program, service, or object.

## 7. Security and distributed roadmap

The following are explicitly not implemented by this first primitive:

1. cryptographic verification of personal or organizational documents;
2. an issuer trust registry, credential issuance, expiry, or revocation protocol;
3. identity uniqueness or Sybil resistance;
4. graph synchronization or distributed consensus;
5. publication of entity manifests or policies to Kubo/IPFS;
6. privacy-preserving selective disclosure or zero-knowledge proofs;
7. global access control or attack mitigation.

Follow-up stages should specify and test: signed credential format and issuer trust; proof of possession; expiry and revocation; consent and recovery; anti-replay; rate-limited admission; node-to-entity relationship verification; safe synchronization and conflict handling; and the policy for any public CID. Sensitive personal identity data must remain private by default.

## 8. Acceptance criteria for this primitive

- Register all supported entity types without requiring personal document fields.
- Permit one entity to reference multiple technical nodes.
- Keep evidence references separate from raw evidence and mark them unverified by default.
- Preserve the distinction between declared relationship and cryptographically verified control.
- Support node-link removal and entity revocation without silently deleting the audit record.
- Reject unknown entity types, invalid relationships, malformed registry data, and writes to revoked entities.
- Store data locally with restrictive file permissions where supported.
- Pass the dedicated unit tests before this primitive is considered verified.

Passing these tests verifies only the local data model. It does not establish distributed operation, document authenticity, real-person uniqueness, production readiness, or security against network attacks.
