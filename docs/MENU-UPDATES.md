# Menu update check

Node Core OS checks the repository's `VERSION` file whenever the main menu opens.

- Matching local and GitHub versions: the menu shows a green `UPDATED` status.
- Different versions: the menu shows a yellow `UPDATE AVAILABLE` status and tells the user to type `Update`.
- No network or GitHub error: the menu still opens and reports that the update status could not be checked.
- Typing `Update` runs the existing user-level `~/.node-core/bin/node-core-update` launcher. It does not require root and does not install or replace Kubo/IPFS.

The updater fetches the latest source from the configured branch, verifies Python compilation, backs up the application, and records the source commit. The user should reopen Node Core OS after an update so the new Python code is loaded.

## Versioning rule

Whenever a release changes the menu or application, update the root `VERSION` file before publishing the change to `main`. The version file is the public contract used by the menu checker. The initial version in this implementation is `1.0.0`.

The version endpoint can be overridden for tests using `NODE_CORE_VERSION_URL`. This setting is optional and intended for testing; normal installations use the official repository's `main/VERSION` file.
