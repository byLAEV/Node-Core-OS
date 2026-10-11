# OpenTimestamps runtime validation

Node Core OS uses the official OpenTimestamps client, not a locally reimplemented
timestamp protocol. The installer creates a user-owned virtual environment at
`~/.node-core/runtime/opentimestamps-venv` and installs
`opentimestamps-client` there. The official client package declares and installs
its Python OpenTimestamps library dependency; Node Core OS should not vendor a
second copy of that library or install it into Termux's system Python.

## Why Node Core OS does not start an OpenTimestamps calendar server

A calendar server is infrastructure for accepting timestamp requests and
aggregating commitments. It is not required for a node to request timestamps
from existing calendars, update proofs, or verify proofs. Running a calendar
server would add operational requirements (publicly reachable service,
availability, abuse controls, monitoring, and potentially Bitcoin-related
infrastructure). It should be a separate opt-in deployment project, not a
default installer step.

## Normal user installation

Run the HashPaper installer or Node Core OS updater as the regular Termux/Linux
user, never as root. The helper validates the `ots` executable in the private
environment. HashPaper calls the official CLI and distinguishes pending proofs
from proofs that report a Bitcoin block attestation.

## Tests

The standard CI suite uses deterministic fake-client tests for adapter behavior
and does not submit real documents to public calendars.

For an opt-in end-to-end test that contacts public OpenTimestamps calendars,
run:

```bash
bash installer/tests/opentimestamps-live-integration.sh
```

This creates a temporary Python virtual environment, installs the official
client, submits a synthetic document, and asks the client to verify the
resulting proof. Network access and public calendar availability are required.
The test never uses personal documents and removes its temporary files on exit.
A newly created proof may remain pending until Bitcoin confirmation; pending is
a valid result for the initial cycle and must not be reported as confirmed.
