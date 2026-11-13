# Node Core Music byLAEV

Node Core Music is a modular music application inside Node Core OS.

- GitHub Pages: https://bylaev.github.io/Node-Core-OS/music/
- Application source: `applications/node-core-music/`
- Catalog: `catalog/catalog.json`
- Catalog schema: `node-core-music-catalog-v1`
- Current catalog version: `1.2.1`

## Current catalog

| Track ID | Title | Version | Artist | Label |
|---|---|---:|---|---|
| NCM-001 | BLOCK BY BLOCK — THE HUMAN LEGACY · Trilema Records byLAEV | — | The Blockchain OG's | Trilema Records byLAEV |
| NCM-002 | THE SYSTEM KEEPS THE RECORD | 1.0 | The Blockchain OG's | Trilema Records byLAEV |
| NCM-003 | THE SYSTEM KEEPS THE RECORD | 2.0 | The Blockchain OG's | Trilema Records byLAEV |

The two versions of THE SYSTEM KEEPS THE RECORD are separate catalog entries with independent track IDs and source URLs. Both original MP3 links supplied for the submissions are preserved in the catalog.

## Delivery architecture

The existing `.github/workflows/pages.yml` workflow publishes a single Pages artifact:

- `web-test-bench/` remains the root site.
- `applications/node-core-music/` is staged at `/music/`.

One shared Pages deployment workflow avoids competing deployments overwriting one another.

## Player and audio delivery

The application reads the catalog JSON and renders an individual player for each track. It provides a direct link to each original MP3 source.

GitHub Pages hosts the static interface and metadata; it is not an audio streaming backend. Playback depends on the external host remaining available and allowing browser access. Audio files are not copied into the Git repository or cached for offline playback.

## Attribution, provenance, and rights

Credits and artist/label information are recorded as submitted. The catalog does not assert ownership, licensing, copyright clearance, or a verified content hash. Those remain unspecified until supporting evidence is supplied and checked.

## Current implementation scope

- Responsive catalog and per-track HTML audio player.
- Stable catalog IDs and source URL records.
- Installable PWA shell.
- Offline caching of application files and catalog metadata; audio itself is not cached.
- Future Node Core local-storage, Kubo/IPFS, identity, and stronger provenance integration are not yet implemented.
