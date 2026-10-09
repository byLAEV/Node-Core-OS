# Menu update check

Node Core OS checks the repository's `VERSION` file whenever the main menu opens.

- Matching local and GitHub versions: the menu shows a green `UPDATED` status.
- A newer GitHub version: the menu shows a yellow `UPDATE AVAILABLE` status and asks the user to type `Update`.
- No network or GitHub error: the menu still opens and reports that update status could not be checked.
- Typing `Update` runs the existing user-level `~/.node-core/bin/node-core-update` launcher. It does not require root and does not install or replace Kubo/IPFS.

The updater downloads the latest source from the configured branch, verifies Python compilation, backs up the application, and records the source commit. Reopen Node Core OS after an update so the new Python code is loaded.

## Versioning rule

Whenever a release changes the menu or application, increase the root `VERSION` file before publishing to `main`. The version file is the public contract used by the menu checker. The version introduced with the menu update checker is `1.1.0`.

The endpoint can be overridden for tests using `NODE_CORE_VERSION_URL`; normal installations use the official repository's `main/VERSION` file.
