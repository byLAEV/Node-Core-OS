# Node Core OS P2P Contracts — Version 0.1 (development)

## Status

This is an experimental development version. The terminal interface is in English. It supports local BTC-for-asset request records, request evidence with reputation ratings, local ID search, and an experimental Kubo PubSub propagation status/ten-minute timer.

## Main menu

1. Create Public Request
2. Create Private Request (disabled; OpenPGP is not implemented)
3. Create Request Closure
4. Search Request ID

The application requires the operator to consent to local use of the existing Node Core OS identity profile before entering the menu. Each public request separately asks which identity fields may be included. No private key is requested or generated.

## Public request flow

The submenu offers:
- Check Propagation Hash Status
- Accept a New Propagation Hash
- View Propagation Status
- Create BTC Exchange Request (locked until the local ten-minute timestamp)

The propagation module uses Kubo PubSub topic node-core-os/p2p-contracts/propagation/v1. PubSub is experimental and must already be enabled in the user's Kubo configuration (Pubsub.Enabled=true), then Kubo must be restarted. This app does not modify Kubo configuration automatically.

## Critical limitations

This version is not a production consensus protocol. PubSub messages are untrusted claims, not signed consensus certificates. There is no global validator membership, quorum, authenticated authorization, complete lease recovery, or proof that every network node observed the same proposal. No peer responses are not proof that a proposal is absent.

The timer unlocks local form creation after ten minutes. This version does NOT yet route submitted requests to the currently active remote proposer, automatically merge remote requests into the trusted local manifest, or guarantee that a node is globally exclusive. Requests created in this version are marked LOCAL_ONLY. Do not use this prototype to coordinate financial settlement or to assert verified reputation.

## Closure evidence and search

Closure records include request ID, reporter node ID, evaluated counterparty node ID, rating (1–5), declared final state, description and timestamp. Evidence is self-reported and unverified. The search checks the local manifest and validates the stored request/evidence hashes.

## Storage and tests

Data is stored under the configured Node Core OS local storage path in p2p_contracts/.

Run from the repository root:

    python -m unittest applications.p2p_contracts.tests.test_service
    python -m unittest applications.p2p_contracts.tests.test_propagation

No BTC or other asset transaction is executed. HashPaper is unchanged. Installer integration is not included in this PR.
