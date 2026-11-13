# Node Core Music byLAEV

Node Core Music is a modular application inside Node Core OS. Its static web interface is published under the existing GitHub Pages deployment at:

- Production route: https://bylaev.github.io/Node-Core-OS/music/
- Application source: `applications/node-core-music/`
- Catalog: `catalog/catalog.json`

## Current catalog

| Track ID | Title | Artist | Label |
|---|---|---|---|
| NCM-001 | BLOCK BY BLOCK — THE HUMAN LEGACY | The Blockchain OG's | HL Music · Trilema Records byLAEV |

The original MP3 URL supplied for this catalog entry is preserved in `catalog/catalog.json`. The repository stores metadata and the player interface, not a copy of the audio file.

## Delivery architecture

The existing `.github/workflows/pages.yml` workflow validates the existing Web Test Bench and the music app, then assembles a single Pages artifact:

- `web-test-bench/` remains the root site.
- `applications/node-core-music/` is copied to `/music/`.

There is intentionally one Pages deployment workflow to avoid competing deployments overwriting one another.

## Audio and rights boundaries

GitHub Pages serves static HTML, CSS, JavaScript, manifest, service worker, and catalog metadata. It is not an audio hosting or streaming backend. Playback depends on the availability, CORS/range behavior, and terms of the external MP3 host. The original source link remains available as a fallback.

The catalog entry records the credits provided with the submission. It does not assert ownership, licensing, copyright clearance, or a content hash. Those fields remain unspecified until evidence is supplied and verified.

## Current implementation scope

- Responsive browser audio player.
- Catalog metadata for NCM-001.
- Installable PWA shell and offline caching of application files.
- Audio itself is not cached for offline playback.
- Future Node Core local-storage, Kubo/IPFS, identity, and provenance integration is not yet implemented.
