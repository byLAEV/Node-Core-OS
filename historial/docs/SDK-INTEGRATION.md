# Node Core OS SDK and Integration Guide

## Status

**Status: integration guide and roadmap.** This document does not claim that an official SDK has already been implemented or released.

## Goal

An SDK should make it straightforward for another project to use supported Node Core OS capabilities without duplicating the core or depending on private implementation details.

## Recommended integration order

1. Read the repository README and implementation documentation.
2. Check the API contract and its status.
3. Confirm that the required operation is implemented and tested.
4. Select an SDK only if the repository publishes one for the required language and API version.
5. If no supported SDK exists, use only a documented API directly or propose an SDK before building a dependency on internal modules.
6. Test authorization failures, backend failures, invalid input, and version compatibility.
7. Document the exact Node Core OS and API versions supported by the integration.

## SDK requirements

Every official SDK should provide:

- clear installation and supported-runtime instructions;
- explicit API-version compatibility;
- typed or otherwise well-documented inputs and outputs;
- predictable error handling;
- configurable connection settings without hard-coded secrets;
- timeouts and safe handling of interrupted requests;
- no implicit publication or propagation of private data;
- minimal permissions and no secret logging;
- unit tests and integration tests against the real implementation;
- runnable examples and upgrade guidance;
- a license and third-party dependency inventory.

SDKs should be thin clients of documented public interfaces. They should not silently duplicate core state, bypass authorization, or access internal files as an alternative to the public contract.

## Security and privacy

An application must request only the capabilities it needs. Installation of an integration is not blanket consent to read, publish, or propagate personal data.

Credentials should be supplied through an appropriate local secret mechanism or protected runtime configuration, never committed to source control. Logs and examples must use fake credentials and synthetic data.

## Compatibility policy

Each SDK release must state:

- SDK version;
- supported Node Core OS API versions;
- supported runtime versions;
- breaking changes;
- migration steps;
- known limitations.

When the API contract changes incompatibly, the SDK must either preserve compatibility or explicitly declare the new supported API version.

## Community proposal template

When proposing a new SDK, include:

1. Target language and runtime.
2. Intended users and use cases.
3. Required API capabilities.
4. Authentication and permission model.
5. Small example showing intended usage.
6. Testing and CI strategy.
7. Maintenance ownership and release plan.
8. Dependencies and licensing.

## Current implementation rule

Do not describe an SDK as official, stable, or available until source code, tests, release/version information, usage examples, and compatibility documentation exist in this repository.
