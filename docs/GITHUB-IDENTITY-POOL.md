# GitHub Identity Pool and Personal Node Client

**Status:** initial implementation in the Node Core BIOS development branch. Not a production identity-verification service or global consensus protocol.

## Architecture
- Main Node Core OS remains the canonical installer, BIOS, protocol and release source.
- Each participating GitHub account owns a small client repository, independent of the full Node Core OS source.
- That repository can publish its own static GitHub Pages site.
- The BIOS administrator maintains a local pool of GitHub logins and client repositories.
- A member-specific client is exported from the administrator node and configured to encrypt records to the administrator pool's public encryption key.
- The browser encrypts each record using a random AES-256-GCM key; RSA-OAEP-256 wraps the AES key.
- The administrator node's RSA private key is kept locally with mode 0600. It decrypts records after synchronization.
- GitHub repositories and IPFS receive ciphertext envelopes only. IPFS CIDs are not access control and cannot promise erasure.

## BIOS workflow
Open Node Core BIOS -> 12. GitHub Identity Pool.
1. Initialize / inspect administrator pool. This creates the local encryption keypair and pool metadata under ~/.node-core/identity/github-pool/.
2. Configure this node's own GitHub client repository, if the administrator also wants a Pages client.
3. Add a GitHub node to the administrator pool. The record starts as pending_admin_verification; adding a login is not proof of account ownership.
4. List pool members.
5. Revoke a member. Revocation prevents future member-client export and pool sync for that entry. It cannot erase published commits or IPFS copies.
6. Export a Pages client for the local account or an admitted member. Export writes only the minimal static template plus a generated public configuration; it never copies the full Node Core OS repository.
7. Synchronize encrypted records from the local repository or a selected member repository.
8. Inspect the public encryption key.

## Member setup
1. The account owner creates an empty repository under their own GitHub account.
2. The pool administrator adds owner/repository to the pool.
3. The administrator exports a member-specific client package. Its config includes the member repository identity and administrator pool public encryption key.
4. Copy the exported files into that repository, commit them, and enable GitHub Pages from the main branch/root.
5. The page accepts a fine-grained token scoped to that single repository with Contents read/write. The token is held only in current-page JavaScript memory, never localStorage or committed files.
6. The user submits a record. WebCrypto encrypts it before the GitHub API upload.
7. The administrator node synchronizes the public member repository and decrypts the record locally.

## GitHub API credential limitation
GitHub Pages is static hosting. A static page cannot securely hold a GitHub App private key or issue its own server-side installation token. The current browser flow uses a user-supplied fine-grained PAT restricted to one repository. This is a bootstrap mechanism and carries browser-session/XSS risk. For production, replace it with a GitHub App and trusted token broker or a local node-mediated write API. Never request a classic PAT or broad account token.
Public member repositories can be fetched without a token. Private repositories require a token authorized by the member account; do not share one broad administrator token across users.

## Privacy and trust
- Only ciphertext is written to GitHub and replicated into shared local storage/IPFS.
- Decrypted personal fields are stored only in the administrator's private local directory.
- A record contains an explicit consent declaration; the form cannot independently prove submitter authority or legal consent.
- GitHub username association is not personhood, legal identity, unique-human or Sybil verification.
- Membership is pending until an independent account-control challenge is implemented.
- The administrator is a trusted processor because it holds the decryption key. Members must be informed before submitting records.
- Distributing the admin private key to all nodes would defeat the privacy boundary. Other nodes may replicate ciphertext but cannot decrypt.
- Ciphertext and commit metadata in public repositories remain public. Never put secrets, private documents or unencrypted personal fields in public files.
- Key backup, rotation, recovery, deletion and retention policies must be implemented before production.
- Revoking a pool member does not remove old commits or content already replicated to IPFS.

## Implemented and not yet implemented
Implemented: local administrator pool; GitHub login/repository validation; pending admission/revocation; local RSA keypair; browser-compatible hybrid encryption; minimal static Pages client; repository read/sync for public records; local private record storage; ciphertext-only shared storage; optional Kubo pinning.
Not yet implemented: cryptographic GitHub account-control proof; automatic repository creation; secure OAuth/GitHub App broker; production write API; authenticated sync for private member repositories; background multi-node replication and conflict/finality protocol; key rotation and recovery; ZKP personhood or document verification. Do not advertise these as available until separately implemented and tested.