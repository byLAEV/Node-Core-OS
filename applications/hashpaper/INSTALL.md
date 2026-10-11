# HashPaper Installation Plan

HashPaper is currently a source-tree prototype and is not yet wired into the Node Core OS installer or updater.

## Development tests

From the repository root on GNU/Linux with Python 3.10 or newer:

```bash
python3 -m unittest discover -s applications/hashpaper/tests -v
```

## Integration requirements before installation is supported

1. Add HashPaper to the versioned application inventory and verify its files during installation.
2. Install code under the replaceable application directory, but store documents, `.ots` proofs, packages, and application state under a persistent data directory outside that code directory.
3. Update the installer and updater without deleting existing Node Core OS configuration, local storage, Kubo repository, identity profile, or HashPaper data.
4. Add clean-install and upgrade tests, including an upgrade from a release without HashPaper.
5. Verify the OpenTimestamps executable/client is installed or report a clear actionable dependency error; do not silently substitute an unverified timestamp implementation.
6. Verify Kubo API availability before publishing and confirm the returned CID by retrieving the package and comparing its bytes.

Do not install this prototype on a production node or publish real personal data until the end-to-end workflow and update-preservation tests pass.
