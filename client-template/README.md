# Node Core OS GitHub Identity Client

This is a lightweight static GitHub Pages client. It is not the full Node Core OS repository or installer.

## Setup
1. Open Node Core BIOS -> Identity Profile -> GitHub Identity Pool.
2. Configure the local GitHub account and an empty repository owned by that account.
3. Export this client package into that repository working tree.
4. Publish GitHub Pages from the repository main branch and root directory.
5. Open the Pages URL and submit a test record using a fine-grained PAT scoped to this repository only with Contents: read/write.
6. Keep the PAT only in the current tab session. Do not paste it into an issue, commit, or public configuration.
7. On the node, synchronize the repository using authenticated GitHub CLI (gh auth login) or NODE_CORE_GITHUB_TOKEN.

## Security boundary
- The browser encrypts each record with a fresh AES-256-GCM key.
- That AES key is wrapped with the owning node RSA-OAEP-256 public key.
- Only the owning node private key can decrypt records.
- The repository stores ciphertext envelopes only.
- The GitHub token is held in JavaScript memory only and is not written to localStorage/sessionStorage.
- GitHub Pages is public static hosting. Repository ciphertext, metadata and commit history are public.
- A fine-grained PAT in a browser is a bootstrap mechanism, not production authentication. Production should use a GitHub App and trusted server-side token broker or a local node-mediated write API. Never embed a GitHub App private key or broad token in Pages.
- Ciphertext copied to IPFS cannot be reliably erased. Key loss means records cannot be recovered.
- This client does not prove legal identity, personhood, uniqueness, or network consensus.