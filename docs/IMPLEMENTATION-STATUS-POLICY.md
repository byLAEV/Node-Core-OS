# Implementation Status and Evidence Policy

**Status of this document:** policy proposal on branch `docs/implementation-status-policy`. It is not active on `main` until reviewed and merged.

## Purpose

Node Core OS byLAEV must not describe a proposal, catalog entry, specification, planned service, or unfinished implementation as an available or operational capability. Repository presence proves only that the corresponding files exist in that revision.

This policy applies to source code, product and service catalogs, certificates, identity components, installers, network protocols, examples, reports, release notes, pull requests, and project presentations.

## Required status vocabulary

Use one explicit status for each capability. If a capability contains multiple independently implemented parts, report their statuses separately.

| Status | Required meaning | Minimum evidence |
| --- | --- | --- |
| `PROPOSED` | An idea or intended capability has been described. | A proposal or requirement document. |
| `IN_DESIGN` | Requirements or architecture are being specified. | Design document with scope, assumptions, interfaces, and open questions. |
| `IN_DEVELOPMENT` | Implementation work is in progress. | Identifiable branch, code changes, or tracked work. |
| `IMPLEMENTED` | Relevant code or artifact exists in the stated revision. | Exact path and commit; do not imply tests passed. |
| `TESTED` | Named tests were actually executed. | Commands/workflow, environment, commit, and actual results. Report failures as well as passes. |
| `VERIFIED` | Defined acceptance criteria passed in a stated environment. | Reproducible evidence linked to the exact revision and criteria. |
| `SECURITY_REVIEWED` | A documented security review was completed for a defined scope. | Review scope, reviewer/process, date, findings, and unresolved risks. |
| `OPERATIONAL` | The capability was demonstrated in its intended operating environment. | Deployment/environment, observed behavior, monitoring or operational evidence, and known limitations. |
| `DEFERRED` | Work is intentionally postponed. | Reason and conditions for resuming. |
| `REJECTED` | The proposal was evaluated and not accepted. | Decision and rationale. |

Do not treat statuses as automatic synonyms. `IMPLEMENTED` does not mean `TESTED`; `TESTED` does not necessarily mean `VERIFIED`; `VERIFIED` does not mean `SECURITY_REVIEWED`; and none of these alone establishes production readiness.

## Catalog rules

1. A catalog is an inventory of documented entries, not proof that its entries are implemented.
2. Every entry must show its current status, scope, dependencies, evidence, limitations, and next acceptance criteria.
3. A directory, README, manifest, schema, specification, or example is documentation unless executable implementation is identified separately.
4. A count such as “eight profiles” means eight documented or implemented profiles only when the stated evidence supports that exact description. Never infer runtime availability from the number of directories.
5. Distinguish automated consistency checks from functional tests, integration tests, adversarial tests, independent audits, and production operation.
6. A successful workflow proves only the checks actually executed by that workflow at the recorded commit. Skipped jobs are not passes.
7. Historical failed runs remain historical evidence. Do not describe them as fixed merely because another commit or run passed. Link the corrective commit and the successful run.
8. Do not claim that a security mechanism “prevents all attacks,” “guarantees privacy,” or is “fully secure.” State the threat model, test scope, and residual risks.

## Pull request and release reporting

Every pull request that changes behavior or claims implementation must state:

- what changed and what did not change;
- exact paths and revision;
- tests actually run and their outcomes;
- checks skipped, unavailable, or not yet run;
- remaining gaps and follow-up work;
- whether the change is documentation-only, code-only, or both.

Do not mark a proposal as operational just because a pull request is merged. Merging means the change was incorporated into the target branch; it is not an independent verification of its claims.

## Evidence record template

Use this compact template in reports and catalog entries:

```text
Capability:
Status:
Revision / commit:
Scope:
Evidence:
Tests passed:
Tests failed or skipped:
Limitations / residual risks:
Next acceptance criteria:
Last checked (UTC):
```

If a field has not been checked, write `UNKNOWN` or `NOT RUN`; do not fill it with an assumption.

## Security, privacy, and transparency

Transparency means explaining behavior, evidence, limitations, and data handling. It does not mean publishing secrets. Never commit private keys, seed phrases, passwords, access tokens, or unnecessary personal data. Public visibility of source code does not authorize publication of private operational data.

## Adoption

This document becomes repository policy only after it is reviewed and merged into `main`. After adoption, update affected documentation incrementally and report discrepancies as work in progress until corrected. Do not claim that the whole repository is compliant until a repository-wide audit has been completed and its findings recorded.
