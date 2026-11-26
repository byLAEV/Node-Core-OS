# Basic communication between two Node Core OS nodes

This guide documents the first peer-connectivity milestone. It uses the Kubo repository configured by Node Core OS and does not replace Kubo, local storage, or the existing main menu.

## What this feature does

- Displays this node's Kubo peer ID.
- Lists directly connected IPFS peers and reports the direct-peer count.
- Connects to another node when given its complete IPFS multiaddress.
- Sends one Kubo ping to a peer ID to test basic round-trip reachability.

The count is **this node plus its directly connected peers**, not a count of every node in the wider IPFS network. A successful ping demonstrates peer reachability; it does not implement authenticated application messaging or a consensus protocol.

## Requirements

- Node Core OS and Kubo installed on both devices.
- Kubo daemon running on both devices.
- Both devices can reach each other over the network.
- TCP port 4001 is reachable between devices, subject to each device's network and firewall.
- Use each Node Core OS installation's own configured IPFS repository. Do not point two Kubo daemons at the same repository directory.

## Device A: start Kubo and find its peer address

Start the Node Core OS application and use **Node Core BIOS → IPFS / Kubo → Start**, or start Kubo using the existing installation's configured repository. On Termux, do not start a second daemon against the same repository if one is already running.

Then display the peer identity and advertised addresses using the configured repository:

```bash
DATA_DIR="${NODE_CORE_DATA_DIR:-$HOME/.node-core}"
IPFS_PATH="$DATA_DIR/ipfs" "$PREFIX/bin/ipfs" id
```

Find an address that is reachable from Device B. For two devices on the same Wi-Fi network, this normally has the form:

```text
/ip4/192.168.1.20/tcp/4001/p2p/<DEVICE_A_PEER_ID>
```

The IP address is only an example. Use the real address reported by Device A that Device B can reach. Do not use `127.0.0.1` as the remote address.

## Device B: connect to Device A

1. Start Kubo on Device B.
2. Open Node Core OS.
3. Select **5. Network / Nodes**.
4. Select **2. Connect to peer**.
5. Paste Device A's complete multiaddress.

Then choose **1. Refresh network status**. Device B should show Device A in its directly connected peer list if the connection succeeded.

## Test communication

From Device B's **Network / Nodes** menu, choose **3. Ping a peer**, and enter Device A's peer ID. A successful Kubo ping reports a round-trip result.

Repeat the status check on Device A. Direct peer connections are often visible from both sides, but the observed list may vary with connection timing and network conditions.

## Limitations and next milestones

This is a connectivity milestone, not yet an application-level messaging system. The next phase can add an explicit, bounded message exchange using IPFS PubSub or a dedicated authenticated protocol, with message IDs, timeouts, and tests. Identity claims, authorization, consensus, and reputation must not be inferred from network connectivity alone.
