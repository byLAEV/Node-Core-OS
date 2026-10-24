# byLAEV Eulora 2 Applicant Transponder

**Status:** experimental local dossier builder. This is not an official Eulora 2 client, a verified EuComms implementation, a WoT admission service, or an endorsement by Ossa Sepia or any individual.

## Security and protocol boundary

The supplied design names EuComms and VaMP/TCP but does not provide a verified packet grammar, framing, authenticated endpoint, port, server acknowledgement format, or admission API. The published material should be reviewed before claiming interoperability. Consequently, this application does not hard-code a host, port, recipient fingerprint, or claim that raw TCP is compatible with Eulora 2.

The optional json-line-v1 transport is an experimental generic transport for a receiver you control or have explicit authorization to test. It is **not** EuComms/VaMP. Transmission requires explicit host, port, protocol, and opt-in flags, and it only reports delivery confirmation if the receiver returns a JSON acknowledgement matching the exact payload SHA-256. That acknowledgement is not admission, identity endorsement, or a WoT rating.

## Requirements

- Node.js 20 or later
- A normal, unprivileged Linux user account
- No external npm runtime dependencies; cryptography, JSON handling, TCP sockets and tests use Node.js built-ins.
- Optional OpenTimestamps proof file generated with the separate ots tool. This application stores the supplied proof but does not claim to verify it.

No script invokes sudo, su, a shell, or a package manager. Do not run as root. Do not use personal keys in tests.

## User-level identity

The default identity directory is ~/.node-core/eulora2-transponder/identity, or NODE_CORE_EULORA2_IDENTITY_DIR if set. The directory is mode 0700, private key mode 0600, and public key mode 0644. The private RSA-4096 key is encrypted at rest with AES-256-CBC in PKCS#8 PEM format. The passphrase is read from NODE_CORE_EULORA2_PASSPHRASE; never put it in a command-line argument or commit it to a file. The variable is still sensitive and should be set only for the process that needs it, then unset.

Fingerprint is SHA-256 of the DER-encoded SubjectPublicKeyInfo, not a hash of PEM text. Signatures use RSA-PSS with SHA-256 and 32-byte salt. This applicant key is independent of Node Core OS's existing identities until a separately reviewed binding process is implemented.

## Commands

From this directory:

    node index.js help
    NODE_CORE_EULORA2_PASSPHRASE='use-a-long-unique-secret-here' npm run generate-key

Provide a declaration file and optional evidence artifacts:

    NODE_CORE_EULORA2_PASSPHRASE='use-a-long-unique-secret-here' npm run build-payload -- --alias byLAEV-Applicant --manifesto ./declaration.txt --evidence ./build/client-binary --claimed-toolchain 'GNAT version verified locally' --target-node UNCONFIRMED_RECIPIENT --output ./payload_eulora2_dossier.json

The evidence option may be repeated. Each regular file is hashed with SHA-256 and its basename and byte size are recorded. This is only a content hash, not proof that a compiler built or executed the file. If no evidence is supplied, the dossier says NO_ARTIFACTS_PROVIDED. Never assert PASSED_VERIFIED unless a real, reproducible test result has been collected and independently checked.

To validate the signature and fingerprint:

    npm run verify-dossier -- --file ./payload_eulora2_dossier.json

To run tests:

    npm test

Tests create a temporary RSA identity and synthetic evidence under the OS temporary directory. They never read the default identity directory or contact a network.

## OpenTimestamps

If an actual proof file exists, provide --ots-proof PATH during dossier generation. The proof is included verbatim as base64, with its SHA-256. The dossier marks its verification status as NOT_VERIFIED_BY_THIS_TOOL; presence is not proof of successful anchoring or verification. A timestamp for a changing payload cannot be represented as a valid proof merely by adding a placeholder. For a rigorous workflow, timestamp the canonical unsigned dossier digest, verify it with OpenTimestamps, and record the verified result in a separately specified schema version.

## Transmission (explicit opt-in, generic protocol only)

Only use this against a receiver you control or are explicitly authorized to test:

    node scripts/transmit_payload.js --file ./payload_eulora2_dossier.json --host 127.0.0.1 --port 43191 --protocol json-line-v1 --allow-unverified-protocol

The receiver must support the experimental protocol and reply with one JSON line:

    {"protocol":"json-line-v1-ack","status":"accepted","payload_sha256":"<exact SHA-256 of canonical dossier JSON>"}

No default endpoint is configured. Do not send the dossier to e2.ossasepia.com or any other third-party host until the recipient, endpoint, protocol, and authorization have been independently confirmed. An acknowledgement means only that a receiver claims to have accepted the exact payload digest.

## Dossier semantics

The whole dossier (except its signature field) is serialized with deterministic key ordering and signed. The signature therefore protects the declaration, fingerprint, routing metadata, and evidence hashes from tampering. A valid signature proves control of the corresponding private key for this payload; it does not prove the applicant's real-world identity, the truth of the evidence, successful compilation, admission, a WoT rating, or recipient acceptance.

The JSON Schema is in schema/eulora2-admission-payload.schema.json. The runtime validator is implemented using Node.js built-ins to avoid installing an external schema package at runtime; changes to the schema and runtime validator must be kept in sync.

## Next steps before real Eulora integration

1. Verify current official documentation and client source for the actual EuComms/VaMP wire format and supported transport.
2. Independently authenticate the intended recipient's public key and endpoint.
3. Implement protocol framing, authentication, timeouts, replay controls, and acknowledgements from the documented protocol—not guessed TCP payloads.
4. Verify OTS proofs with the official tool and define exactly which digest is timestamped.
5. Have a receiver test harness and explicit authorization before enabling external transmission.
