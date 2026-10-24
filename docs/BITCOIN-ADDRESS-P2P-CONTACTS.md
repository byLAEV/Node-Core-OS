# Bitcoin address aliases for native P2P messaging

Node Core OS can let a user type a Bitcoin address as a convenient contact alias.
The local contact book maps that address to a canonical Node Core OS node ID and
a reachable host/port endpoint. It is a directory convenience, not a Bitcoin
transaction and not a proof that the peer controls the address.

## Fee and network separation

A text message sent over native Node Core OS P2P does not create a Bitcoin
transaction and does not pay a Bitcoin miner fee. The message is transmitted over
the computer network, so the internet connection or hosting provider may still
have its own costs. No Bitcoin transaction, inscription, OP_RETURN, or blockchain
write is required.

## Required setup

1. Exchange the recipient's Bitcoin address, Node ID, TLS certificate and endpoint.
2. Verify the certificate fingerprint with the recipient through a separate channel.
3. Explicitly trust the recipient certificate in Node Core OS.
4. Save the contact mapping locally.
5. Send the message over the existing authenticated native P2P TLS connection.

The recipient must be reachable and online, and the recipient must have explicitly
trusted the sender certificate. The address itself cannot discover a node, establish
a connection, or receive a message. For internet-wide delivery, a reachable endpoint,
port forwarding, or a future relay/rendezvous service is required.

## Security and validation

The contact book is local-only at `~/.node-core/p2p/contacts.json`, with restrictive
POSIX file permissions where supported. It accepts common Bitcoin mainnet address
formats as an input-format check, but full Base58Check/Bech32 checksum verification
should be added before relying on address validation as a financial-integrity check.
A syntactically valid address is not proof of ownership. Do not claim a contact
owns a Bitcoin address unless a separate cryptographic challenge has been verified.
