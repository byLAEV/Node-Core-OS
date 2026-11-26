# Remembering & Forgetting — Future Architecture Specification

**Status:** Proposed future work. This document describes intended behavior; it does not claim that the complete model is implemented.

## 1. Core principle

Node Core OS distinguishes **preserving historical information** from **actively applying that information to the present context**.

> **The present is the default context. The past remains available as evidence, but it is not applied by default. A current requirement determines whether relevant history should be remembered.**

This is a context-selection model, not a synonym for data deletion.

`FORGOTTEN` means historical information is not automatically applied to the active context. It does not mean the underlying record has been destroyed.

- `PRESERVED != ACTIVELY USED`
- `FORGOTTEN != DELETED`
- `STORED != AUTHORIZED`
- `AVAILABLE != VALID`

## 2. Separate operations

The implementation must not collapse these operations into one status or command:

| Operation | Intended meaning |
|---|---|
| Remember | Selectively retrieve and apply historical context required by a specific request. |
| Forget context | Stop applying historical context by default; preserve the record unless a separate policy says otherwise. |
| Restrict | Prevent specified actors or operations from accessing or applying a record. |
| Expire | Mark a record, permission, or credential as past its configured validity or retention boundary. |
| Revoke | Invalidate a credential, authorization, or claim according to its issuing or governing policy. |
| Delete / purge | Remove information from storage locations controlled by the system, subject to the defined deletion policy. |
| Unpin | Stop requesting local Kubo/IPFS persistence for a content identifier. This does not prove network-wide deletion. |
| Publish / share | Make content or a reference available to others under the defined publication behavior. |

A record may be preserved while forgotten from active context, restricted from an application, or revoked for a particular purpose. Each state must be represented independently where needed.

## 3. Requirement-driven selective recall

A request should declare its purpose, scope, and the evidence required to satisfy it. The memory layer should select the minimum relevant historical information rather than loading an entire identity or activity history.

Conceptual flow:

```text
CURRENT REQUEST
      |
      v
PURPOSE AND REQUIREMENT
      |
      v
IS HISTORICAL CONTEXT REQUIRED?
      |                         |
      | NO                      | YES
      v                         v
Use present context       Select minimum relevant history
                                |
                                v
                         Check access and validity
                                |
                                v
                         Apply relevant evidence
                                |
                                v
                         Evaluate current request
```

The existence of a record does not itself authorize its use, disclosure, or publication. A requester must satisfy the applicable access policy, and recalled evidence must be evaluated for freshness, integrity, validity, and scope.

## 4. Storage domains

### Local storage

The Node may manage local records, metadata, indexes, policies, and user-controlled keys. Deletion claims must be scoped to the local copies and indexes the operation actually controls. Backups, snapshots, external copies, and storage-media behavior may limit what can be verified.

### Kubo / IPFS

A CID identifies content; it does not by itself prove authenticity, availability, confidentiality, authorization, or truth.

The implementation must distinguish:
- removing a local registry reference;
- removing a local source file;
- unpinning content from the local Kubo node;
- withdrawing a publication or link controlled by the user;
- deleting a key used to decrypt encrypted content.

None of these actions alone guarantees that copies held by other peers or third parties disappear. Public content should be treated as potentially copied. Sensitive content must not be published in plaintext by default.

## 5. Encryption and cryptographic forgetting

Encryption may reduce exposure when distributed storage is needed for private material. Destroying a decryption key may make a ciphertext inaccessible to parties who do not hold another copy of that key, but it is not proof that all keys, plaintext copies, backups, or previously decrypted versions have been destroyed.

Key destruction must therefore be an explicit, high-impact operation with defined authorization, backup behavior, confirmation, and recovery implications. The system must not claim universal cryptographic erasure without evidence that supports that claim.

## 6. Records, identity, evidence, and reputation

Historical records may support identity, credentials, a personal life history, evidence, and contextual reputation. These must remain separate concepts:

- A personal narrative is an account supplied by its author.
- Evidence may support a claim but does not automatically prove every interpretation of it.
- Integrity verification shows that content matches a reference or signature under the relevant assumptions; it does not independently prove the real-world truth of the content.
- Credential validity and revocation must be checked under the credential's own rules.
- Reputation should be contextual and based on relevant evidence, not an automatic permanent label derived from the entire history.

When a user removes a personal entry, the system should apply the entry's policy and report the scope of the completed operation. If another record must be retained for a defined security, legal, or protocol purpose, retain only what is justified and minimize personal data.

## 7. Proposed data and state model

The eventual schema should be informed by existing repository models before implementation. It should separate, at minimum:

- object identity and type;
- storage locations and content references;
- access policy;
- retention and expiry policy;
- validity and revocation state;
- active-context selection state;
- deletion request and execution state;
- integrity reference;
- operation result and verification scope.

Avoid using one universal status to represent availability, validity, authorization, active-context inclusion, and deletion. These dimensions can differ simultaneously.

Suggested lifecycle labels for discussion—not yet a committed runtime schema—include `ACTIVE`, `FORGOTTEN_FROM_CONTEXT`, `RESTRICTED`, `EXPIRED`, `REVOKED`, `PENDING_DELETION`, `DELETED_FROM_CONTROLLED_STORAGE`, `UNAVAILABLE`, and `SUPERSEDED`. Use separate fields if multiple conditions can apply at once.

## 8. User-facing behavior

A future Memory & Privacy interface should explain, for each record where applicable:
- where it is stored;
- whether it is local, encrypted, or publicly distributed;
- who can access or apply it;
- whether it is included in the current context;
- whether it is valid, expired, or revoked;
- what retention policy applies;
- which forget, restrict, revoke, unpublish, unpin, or delete actions are available;
- what the system completed and what remains outside its control.

The interface must never report "deleted everywhere" based only on a local deletion or unpin operation.

## 9. Implementation roadmap

1. **Repository audit:** identify current storage, registry, identity, evidence, content, Kubo, and test contracts. Reuse existing modules and avoid duplicate abstractions.
2. **Requirements and threat model:** define actors, permissions, expected failure modes, privacy boundaries, backup behavior, and what can actually be verified.
3. **Schema and contracts:** specify object metadata and independent context, access, validity, retention, and deletion dimensions.
4. **Local prototype:** implement and test requirement-driven selective recall and context exclusion without deleting records.
5. **Lifecycle operations:** add retention, restriction, expiry, revocation, and controlled local deletion with explicit outcomes.
6. **Kubo/IPFS integration:** test registry references, add/retrieve, pin/unpin, publication withdrawal, and failure handling using the current content contracts.
7. **Privacy and key management:** define encryption boundaries, key storage, backups, and destructive-operation safeguards before implementing cryptographic forgetting.
8. **Evidence and identity integration:** connect personal records, credentials, selective disclosure, and contextual reputation only after their schemas and authorization rules are defined.
9. **UI and documentation:** expose actual capabilities and limitations in the web interface; label planned features as planned until tests verify them.
10. **CI and release gates:** add deterministic tests for successful and failed operations, restarts, unavailable Kubo, stale references, revocation, and backup/restore behavior.

## 10. Minimum acceptance criteria

- A record can be excluded from active context without being deleted.
- A request recalls only the minimum relevant history permitted by policy.
- An existing record does not automatically grant access or permission to use it.
- Context state, validity, authorization, storage, and deletion are not conflated.
- Local deletion reports only the scope actually verified.
- IPFS unpinning or reference removal is never represented as network-wide deletion.
- A failed deletion remains visibly incomplete and can be retried or reviewed.
- Sensitive content and metadata are not published by default.
- Tests cover success, failure, restart, and unavailable-storage scenarios.
- Documentation and the public website clearly distinguish planned behavior from implemented and tested behavior.

## 11. Non-goals and guarantees

This proposal does not promise that a node can erase copies controlled by third parties, prove the real-world truth of every stored claim, or make all past records legally erasable. Applicable retention, safety, and legal requirements need separate policies. The goal is explicit control over context and storage operations with truthful, verifiable reporting.

## 12. Related project architecture

This specification extends the existing **Forget / Remember Context Model** in the project README. It should be reconciled with the current local content registry and Kubo lifecycle documented in [ARCHITECTURE.md](./ARCHITECTURE.md) before runtime changes are made.
