# My Life / Node Blog — Entry Management

## Purpose

My Life is the personal blog and record subsystem in menu **3** of Node Core OS. It remains local-first: generating an entry never uploads it to IPFS. Existing Markdown entries and their index remain readable.

## Menu

- `0. Back`
- `1. Carpetas`: counts entries in Private, Public, IPFS CID and Olvidar temporal.
- `2. My Life Blog`: browse existing entries.
- `3. Crear publicación`: collect title, summary, body, tags, image URLs, video URLs and destination, then generate a standalone HTML document.

The terminal editor currently accepts HTTP(S), IPFS and IPNS media references. Local-file upload and a browser-based rich editor are follow-up work; the current terminal flow does not copy local media into the publication.

## Storage layout

- `storage/my-life/private/`
- `storage/my-life/public/`
- `storage/my-life/ipfs/`
- `storage/my-life/forget-temporary/`
- Existing Markdown entries remain under `storage/my-life/entries/`.
- `storage/my-life/index.json` remains the metadata index.

The four logical folders are created when a publication is saved there. Existing entries without a folder field remain compatible and are interpreted as private for folder counts.

## IPFS publication

HTML generation and IPFS publication are separate operations. A generated HTML entry has no CID until the operator explicitly publishes that selected entry. Pinning preserves content on the local Kubo node; a CID alone does not guarantee network availability. Do not publish private material.

## Node access metadata — current limitation

The editor records the Node IDs supplied for a publication as metadata. This is **not yet an access-control boundary**: IPFS content is public to anyone who obtains its CID, and a list of node IDs does not encrypt content or authenticate readers. A future private-sharing implementation must encrypt the content for authorized node public keys, authenticate requests, support revocation/key rotation, and test the complete receive path before describing the blog as restricted.

## Forget temporary — current limitation

This folder is a logical local destination only. It does not yet implement automatic expiration, secure deletion, or removal of copies already distributed to IPFS or other nodes.

## Verification

Unit tests cover local-only HTML generation, metadata persistence, media URL scheme validation, escaping of HTML input and preservation of existing Markdown behavior.
