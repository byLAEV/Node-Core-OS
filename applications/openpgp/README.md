# Node Core OS OpenPGP CLI

Status: initial implementation under review. This module is not a claim that the whole Node Core OS security architecture has been audited.

## Design

- Linux terminal application written in Python and backed by the installed GnuPG executable. OpenPGP packet and cryptographic operations are delegated to GnuPG; this project does not implement a custom OpenPGP format.
- Runs as the ordinary logged-in user. It does not invoke sudo, su, a shell, package managers, or privileged services.
- Uses a dedicated keyring at ~/.node-core/openpgp/gnupg by default. Set NODE_CORE_OPENPGP_HOME or pass --home to choose a different user-owned directory. The keyring directory is set to mode 0700.
- Generates an Ed25519 signing primary key and a Cv25519 encryption subkey. Private-key passphrases are read interactively and passed to GnuPG over stdin, never as command-line arguments.
- Supports public-key export/import, file encryption/decryption, detached signatures, and signature verification using standard GnuPG/OpenPGP operations.

## Requirements

- GNU/Linux
- Python 3.10+
- GnuPG (gpg) available in PATH

No additional Python packages are required by this module. The root requirements.txt already declares cryptography for Node Core OS; this module does not add another Python cryptography implementation or a new dependency.

## Run from the repository checkout

    python3 applications/openpgp/main.py status
    python3 applications/openpgp/main.py keygen --name "Example User" --email "user@example.org"
    python3 applications/openpgp/main.py list
    python3 applications/openpgp/main.py export-public --fingerprint FULL_FINGERPRINT --output ./public-key.asc
    python3 applications/openpgp/main.py import-public --input ./peer-public-key.asc
    python3 applications/openpgp/main.py encrypt --recipient RECIPIENT_FULL_FINGERPRINT --input ./document.txt --output ./document.txt.gpg
    python3 applications/openpgp/main.py decrypt --input ./document.txt.gpg --output ./document.txt
    python3 applications/openpgp/main.py sign --fingerprint SIGNER_FULL_FINGERPRINT --input ./document.txt --output ./document.txt.sig
    python3 applications/openpgp/main.py verify --signature ./document.txt.sig --input ./document.txt

Run key generation from a real terminal so the passphrase prompt is private. The CLI rejects empty passphrases and requires at least 12 characters. Output files are not overwritten.

## Trust and data handling

Encryption uses an explicitly supplied full recipient fingerprint. The non-interactive GnuPG trust model avoids a prompt; it does not authenticate the recipient's identity. Confirm the full fingerprint with the recipient through an independent trusted channel before encrypting sensitive information. Importing a key alone does not establish identity.

A valid detached signature proves that the signature matches the exact file and signing key; it does not independently prove human identity, truth, ownership, or intent behind that key. Verify the fingerprint independently.

This first module does not publish content to IPFS, transmit data over P2P, or integrate with Node Core OS identity profiles yet. No network publication is performed here. Do not place private keys, passphrases, or sensitive plaintext in public repositories or CI artifacts.

## Tests

Run from the repository root:

    python3 -m unittest discover -s applications/openpgp/tests -v

Tests generate disposable synthetic keys in temporary, separate keyrings. They cover public-key export/import, encryption and decryption between two keyrings, valid detached signatures, rejection of modified content, fingerprint validation, and protection against overwriting existing output files. They do not use personal data or the user's default GnuPG keyring.
