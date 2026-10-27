# Evidence and Testing — Identity Authenticity and Key-Protection Assessment

**Profile:** `identity-key-protection`  
**Evidence status:** Test plan required; do not imply complete security-effectiveness validation.

## Existing evidence boundary

The current certificate unit test suite includes a valid `identity-key-protection` certificate case and tests tampering, unknown issuers, revocation inputs, expiry, maximum lifetime, and unsupported profiles. These tests validate certificate-handling behavior, not a complete operational key-custody audit.

The certificate implementation and its unit tests are linked from the [catalog-wide test and evidence matrix](../CERTIFICATE-TEST-AND-EVIDENCE-MATRIX.md). Existing format tests should be cited as certificate-envelope evidence only. A workflow definition is not itself proof of a successful run; record a completed GitHub Actions run tied to the exact commit before reporting a test as passed.

## Test plan

1. **Baseline:** record the exact software revision, configuration, environment, and expected behavior.
2. **Positive case:** demonstrate the authorized, valid workflow.
3. **Negative case:** exercise invalid, altered, unauthorized, stale, or otherwise disallowed inputs relevant to this product.
4. **Boundary case:** test configured limits, partial failure, restart/recovery, and ambiguous results where applicable.
5. **Multi-node case:** where relevant, test coordination and disagreement among multiple test identities without assuming that separate keys imply independent operators.
6. **Evidence review:** verify result provenance, integrity, timestamps, and reproducibility.
7. **Safety review:** confirm authorization, scope boundaries, abort criteria, and data handling.
8. **Report:** publish what was tested, what passed or failed, what remains untested, and the exact commit and workflow run.

## Evidence record template

For each test execution, record:
- Test ID and scenario.
- Work-order ID and authorization reference.
- Target system and scope.
- Repository commit SHA and software version.
- Environment and configuration.
- Tool and dependency versions.
- Command or reproducible procedure.
- Expected and observed outcomes.
- Result status and failure details.
- Artifact hashes or signed evidence references.
- Timestamp and test operator identity.
- Reviewer identity and conflicts of interest.
- Limitations, exclusions, and remediation items.
- GitHub Actions workflow run URL, if CI executed the test.

## Publication rules

- Never label a test as passed without a successful recorded run for the relevant code.
- Never infer attack resistance from a certificate profile being recognized.
- Never state that all eight certificates have dedicated effectiveness coverage unless the test matrix and actual CI runs establish it.
- Keep sensitive customer evidence access-controlled; publish only approved summaries and integrity references.
- Mark unimplemented, untested, or externally unreviewed controls explicitly.

## Next implementation step

Create a dedicated automated test suite for this profile's security objective, using synthetic identities and isolated lab assets. Add the suite to a maintained GitHub Actions workflow, define expected positive and negative results, and update this document only after reviewing a successful run. Do not conduct uncontrolled denial-of-service or unauthorized testing.
