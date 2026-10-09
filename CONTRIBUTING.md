# Contributing to Node Core OS

Thank you for helping improve Node Core OS.

Node Core OS is intended to grow through community review, practical testing, documented proposals, and reusable interfaces. Contributions are welcome: bug fixes, tests, documentation, security reports, installer improvements, API design, SDKs, adapters, and protocol integrations.

## Collaboration model

The canonical repository is the shared project. A fork or working branch is a contribution workspace, not a substitute for community review. Changes become part of the canonical project only after they have been reviewed and accepted by maintainers.

You do not need to create a long-lived fork to participate. You may open an issue, propose a design, improve documentation, add tests, or submit a focused pull request.

## Before changing code

1. Read the README and relevant documents under `docs/`.
2. Search existing issues and pull requests to avoid duplicate work.
3. For substantial changes, open an issue or design proposal first.
4. Keep changes focused and explain the problem they solve.
5. Do not claim a capability is implemented unless the code and tests demonstrate it.

## Pull request workflow

1. Work in a branch in your own workspace.
2. Explain the motivation, design, compatibility impact, and any security or privacy implications.
3. Add or update tests for changed behavior.
4. Update documentation and examples when interfaces or behavior change.
5. Run the relevant tests and report the exact commands and results. Never report tests as passing if they were not run.
6. Submit a pull request against the canonical repository.
7. Respond constructively to review and revise the change when needed.

Maintainers may request changes, defer a proposal, or decline changes that conflict with project goals, quality, security, maintainability, or compatibility. A pull request is a proposal, not an automatic merge.

## API and SDK integrations

Node Core OS aims to be reusable infrastructure. Integrations should prefer documented, stable APIs and SDKs over depending on internal implementation details.

- Treat API and SDK interfaces as explicit compatibility contracts.
- Document authentication, authorization, permissions, errors, versioning, and data formats.
- Follow least privilege; an integration must not gain unrestricted access to a Node merely because it can call an interface.
- Preserve the distinction between local storage and Kubo/IPFS.
- Do not assume that stored data is authorized to be shared, propagated, or published.
- Include runnable examples and tests for new interfaces.
- Keep credentials, private keys, personal data, and local configuration out of commits, logs, examples, and issue reports.

If a suitable public API or SDK does not exist yet, propose its interface first. Do not describe a proposed interface as available functionality.

## Quality and scope

Prefer simple, readable, testable changes over speculative abstractions. Preserve supported installation and update behavior. Avoid destructive changes to user data, existing installations, or Kubo repositories. Clearly document migration steps for any incompatible change.

## Licensing

By submitting a contribution that you intend to be incorporated into Node Core OS, you agree that it is submitted for consideration under the repository's Apache License 2.0, unless you explicitly state otherwise or a separate written agreement applies. You must have the right to submit the contribution and must identify third-party code or assets and their licenses. Do not submit material copied from sources whose terms are incompatible.

## Community conduct

Be respectful, specific, and constructive. Critique ideas and implementations, not people. Do not publish private information, credentials, or security-sensitive details in public issues.

## Security vulnerabilities

Please do not disclose exploitable vulnerabilities in public issues. Report them privately through the repository's GitHub security reporting feature if enabled, or contact the maintainers through a verified channel listed in the repository.

Thank you for helping make Node Core OS more reliable, interoperable, and useful.
