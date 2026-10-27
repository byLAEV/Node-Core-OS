# Smart TV Module — Implementation Status and Evidence Gates

**Status at creation:** proposal documentation. This status must be updated only after source code, CI and/or device evidence is available.

| Component | Specification | Software implementation | Real device evidence | Current honest status |
|---|---|---|---|---|
| Credential 1: acquisition/ownership | Drafted | Not added by this document | None | SPECIFIED / NOT IMPLEMENTED |
| Credential 2: firmware integrity | Test targets drafted | OEM-specific adapter absent | None | REQUIREMENTS ONLY |
| Credential 3: network threat observation | Test targets drafted | TV-specific sensor adapter absent | None | REQUIREMENTS ONLY |
| Credential 4: alert channel | Drafted | TV-specific transport not established | None | SPECIFIED / NOT IMPLEMENTED |
| Credential 5: support/settlement | Drafted | Dry-run/payment adapter absent | None | SPECIFIED / NO PAYMENTS |
| Credential 6: peripheral privacy | Test targets drafted | Hardware/OEM adapter absent | None | REQUIREMENTS ONLY |
| Credential 7: local peer trust | Drafted conceptually | TV-specific peer integration not established | None | REQUIREMENTS ONLY |
| Credential 8: emergency containment | Test targets drafted | Hardware kill-switch not established | None | REQUIREMENTS ONLY |
| Manufacturer trust registry | Not finalized | Not implemented here | None | OPEN |
| Owner transfer/recovery policy | Draft requirements | Not implemented here | None | OPEN |
| Strict schemas and canonical signatures | Envelope examples only | Not implemented here | None | OPEN |
| Per-capability CI attack suites | Test matrix only | Not added here | None | NOT RUN |
| OEM hardware/firmware validation | Device requirements listed | Not applicable to docs-only changes | None | NOT RUN |

## Claims that must not be made yet

- “Installed at factory” or “supported by all Smart TVs”.
- “Zero performance impact”.
- “Instantaneous, global, real-time defense”.
- “Legal ownership is cryptographically proven”.
- “The camera/microphone is physically disabled” without hardware enforcement evidence.
- “Firmware is rootkit-proof” without verified-boot/update-chain evidence.
- “Kill-switch physically isolates the bus” without a device-specific implementation and test.
- “Lightning/Liquid payments are enabled” without a reviewed and tested payment adapter.
- “The eight existing Node Core OS node-network certificate profiles are equivalent to these eight Smart TV capabilities”.

## Next implementation sequence

1. Review the threat model and choose a specific TV platform/OEM test target.
2. Finalize strict schemas for acquisition/ownership and alert events; implement canonical signatures and negative tests.
3. Implement a local-only alert processor with replay protection, bounded queue and deterministic test fixtures.
4. Add dry-run support work orders and settlement eligibility rules; keep actual payment disabled.
5. Define interfaces for OEM secure boot measurement, key storage and privacy controls; do not simulate these as hardware guarantees.
6. Create profile-specific test workflows and artifacts.
7. Execute cross-capability tests in an isolated lab and publish evidence.
8. Obtain independent review and explicit OEM/device-owner authorization before a pilot.
