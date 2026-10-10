# My Life / Node Blog — Entry Management

## Purpose

My Life / Node Blog is a local-first personal record feature. Creating an entry stores a Markdown file under `storage/my-life/entries/` and adds its metadata to `storage/my-life/index.json`. Creation does not publish content to IPFS.

## Browse large collections

- The terminal interface shows 10 entries per page by default.
- `N` moves to the next page and `P` returns to the previous page.
- Numbered entries are local to the page currently displayed.
- Selecting a number opens the detail menu for exactly one entry.
- Search accepts a title, entry ID, or text found in the local entry file.
- Search results use the same paginated list and individual-entry menu.

## Publish one entry

Publication is a separate action inside the selected entry's detail menu. The operation receives the entry's stable `entry_id`, checks that its local file exists, adds that file to Kubo/IPFS with pinning, and stores the returned CID and pin state on that one index record.

If the entry already has a CID but is not marked as pinned, Node Core asks Kubo to pin that CID rather than re-adding the file. If publication fails, the local Markdown file remains intact and the failure is reported. The interface does not offer a bulk-publish action.

An IPFS CID identifies content; it does not by itself guarantee that content remains available across the network. Pinning preserves content on the local Kubo node. Users should consider privacy before publishing personal information.

## Updating an existing installation

The Node Core OS updater replaces the application directory from the selected repository commit and preserves the persistent storage directory, Kubo binary, Kubo repository, and existing configuration. The entry schema remains compatible with existing records, so this feature does not require a migration of `storage/my-life/index.json`.

## Verification

Automated tests cover local-only creation, explicit IPFS addition, publishing one selected entry without publishing another, preservation of local files, and rejection of unknown entry IDs. The UI and installer must be exercised in CI before this release is considered verified.
