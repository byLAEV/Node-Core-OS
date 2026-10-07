# Node Core OS + Pinata

Node Core OS does not log into Pinata with Google or GitHub.

The user logs into the Pinata web console, creates a restricted API credential, and provides that credential to Node Core OS. Node Core OS then uses HTTPS API authentication with a Bearer credential.

The credential is a provider secret and must not be placed in config.json, Git history, or a Node Core backup.

V1 uploads only encrypted .ncb backups and records the resulting CID as backup metadata.
