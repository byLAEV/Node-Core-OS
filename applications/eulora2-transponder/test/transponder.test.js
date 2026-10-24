'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {
  generateIdentity, buildDossier, verifyDossier, publicKeyFingerprint, canonicalJson
} = require('../lib/transponder');

const PASSPHRASE = 'test-only-passphrase-for-eulora2';
let temporary;
let identityDir;
let evidencePath;
let dossier;

test.before(() => {
  temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'bylaev-eulora2-test-'));
  identityDir = path.join(temporary, 'identity');
  const generated = generateIdentity({ directory: identityDir, passphrase: PASSPHRASE });
  assert.equal(generated.algorithm, 'RSA-4096');
  assert.equal(fs.statSync(generated.privatePath).mode & 0o777, 0o600);
  assert.equal(fs.statSync(identityDir).mode & 0o777, 0o700);
  evidencePath = path.join(temporary, 'synthetic-client.bin');
  fs.writeFileSync(evidencePath, Buffer.from('synthetic test artifact only\n'));
  dossier = buildDossier({
    alias: 'test-applicant',
    manifestoText: 'Synthetic test declaration. No real admission request.',
    identityDirectory: identityDir,
    passphrase: PASSPHRASE,
    evidencePaths: [evidencePath],
    claimedToolchain: 'NOT_ASSERTED',
    now: new Date('2026-01-01T00:00:00.000Z')
  });
});

test.after(() => {
  fs.rmSync(temporary, { recursive: true, force: true });
});

test('fingerprint uses canonical DER SubjectPublicKeyInfo bytes', () => {
  assert.match(publicKeyFingerprint(dossier.identity.rsa_public_key_pem), /^[a-f0-9]{64}$/);
});

test('generated dossier verifies and records evidence as unattested', () => {
  const result = verifyDossier(dossier);
  assert.equal(result.valid, true, result.errors.join('; '));
  assert.equal(result.evidence_status, 'HASHED_NOT_INDEPENDENTLY_ATTESTED');
  assert.equal(result.admission_decision, 'NOT_DETERMINED_BY_CRYPTOGRAPHIC_VERIFICATION');
  assert.equal(result.ots_proof_verified, false);
});

test('tampering with dossier metadata invalidates the signature', () => {
  const changed = structuredClone(dossier);
  changed.identity.alias = 'someone-else';
  assert.equal(verifyDossier(changed).valid, false);
});

test('tampering with declaration invalidates the signature', () => {
  const changed = structuredClone(dossier);
  changed.declaration_and_proofs.manifesto_text += ' altered';
  assert.equal(verifyDossier(changed).valid, false);
});

test('tampering with artifact hash invalidates the signature', () => {
  const changed = structuredClone(dossier);
  changed.technical_evidence.artifacts[0].sha256 = '0'.repeat(64);
  assert.equal(verifyDossier(changed).valid, false);
});

test('fingerprint mismatch is rejected', () => {
  const changed = structuredClone(dossier);
  changed.identity.fingerprint_sha256 = '0'.repeat(64);
  assert.equal(verifyDossier(changed).valid, false);
});

test('existing identity files are never overwritten', () => {
  assert.throws(() => generateIdentity({ directory: identityDir, passphrase: PASSPHRASE }), /already exist/);
});

test('passphrase policy rejects short values', () => {
  assert.throws(() => generateIdentity({ directory: path.join(temporary, 'bad'), passphrase: 'short' }), /at least 16/);
});

test('canonical JSON is deterministic for object key order', () => {
  assert.equal(canonicalJson({ b: 2, a: 1 }), canonicalJson({ a: 1, b: 2 }));
});

test('malformed dossier and substituted public key are rejected', () => {
  assert.equal(verifyDossier(null).valid, false);
  const changed = structuredClone(dossier);
  changed.identity.rsa_public_key_pem = 'not a public key';
  assert.equal(verifyDossier(changed).valid, false);
});
