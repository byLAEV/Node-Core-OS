'use strict';

const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const DOSSIER_VERSION = '1.0.0';
const MAX_EVIDENCE_FILES = 100;
const MAX_EVIDENCE_FILE_BYTES = 64 * 1024 * 1024;

function canonicalJson(value) {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return '[' + value.map(canonicalJson).join(',') + ']';
  return '{' + Object.keys(value).sort().map(key => JSON.stringify(key) + ':' + canonicalJson(value[key])).join(',') + '}';
}

function publicKeyFingerprint(publicKeyPem) {
  const key = crypto.createPublicKey(publicKeyPem);
  if (key.asymmetricKeyType !== 'rsa') throw new Error('Applicant public key must be RSA.');
  return crypto.createHash('sha256').update(key.export({ type: 'spki', format: 'der' })).digest('hex');
}

function ensurePrivateDirectory(directory) {
  fs.mkdirSync(directory, { recursive: true, mode: 0o700 });
  fs.chmodSync(directory, 0o700);
  if (!fs.statSync(directory).isDirectory()) throw new Error('Identity path is not a directory.');
}

function identityDirectory() {
  return process.env.NODE_CORE_EULORA2_IDENTITY_DIR ||
    path.join(process.env.HOME || os.homedir(), '.node-core', 'eulora2-transponder', 'identity');
}

function generateIdentity({ directory = identityDirectory(), passphrase } = {}) {
  if (typeof passphrase !== 'string' || passphrase.length < 16) {
    throw new Error('Set NODE_CORE_EULORA2_PASSPHRASE to a passphrase of at least 16 characters.');
  }
  ensurePrivateDirectory(directory);
  const privatePath = path.join(directory, 'eulora2_rsa.priv.pem');
  const publicPath = path.join(directory, 'eulora2_rsa.pub.pem');
  if (fs.existsSync(privatePath) || fs.existsSync(publicPath)) throw new Error('Identity files already exist; refusing to overwrite them.');

  const pair = crypto.generateKeyPairSync('rsa', {
    modulusLength: 4096,
    publicExponent: 0x10001,
    publicKeyEncoding: { type: 'spki', format: 'pem' },
    privateKeyEncoding: { type: 'pkcs8', format: 'pem', cipher: 'aes-256-cbc', passphrase }
  });
  try {
    fs.writeFileSync(privatePath, pair.privateKey, { mode: 0o600, flag: 'wx' });
    fs.chmodSync(privatePath, 0o600);
    fs.writeFileSync(publicPath, pair.publicKey, { mode: 0o644, flag: 'wx' });
    fs.chmodSync(publicPath, 0o644);
  } catch (error) {
    try { fs.unlinkSync(privatePath); } catch {}
    try { fs.unlinkSync(publicPath); } catch {}
    throw error;
  }
  return { privatePath, publicPath, fingerprint_sha256: publicKeyFingerprint(pair.publicKey), algorithm: 'RSA-4096', private_key_encrypted: true };
}

function readIdentity(directory = identityDirectory()) {
  const publicPath = path.join(directory, 'eulora2_rsa.pub.pem');
  const privatePath = path.join(directory, 'eulora2_rsa.priv.pem');
  const publicKeyPem = fs.readFileSync(publicPath, 'utf8');
  const privateKeyPem = fs.readFileSync(privatePath, 'utf8');
  return { publicPath, privatePath, publicKeyPem, privateKeyPem, fingerprint: publicKeyFingerprint(publicKeyPem) };
}

function collectEvidence(paths = []) {
  if (!Array.isArray(paths) || paths.length > MAX_EVIDENCE_FILES) throw new Error('Evidence list must contain no more than ' + MAX_EVIDENCE_FILES + ' files.');
  return paths.map(inputPath => {
    const absolutePath = path.resolve(inputPath);
    const stat = fs.statSync(absolutePath);
    if (!stat.isFile()) throw new Error('Evidence path is not a regular file: ' + inputPath);
    if (stat.size > MAX_EVIDENCE_FILE_BYTES) throw new Error('Evidence file exceeds 64 MiB: ' + inputPath);
    const bytes = fs.readFileSync(absolutePath);
    return { name: path.basename(absolutePath), size_bytes: bytes.length, sha256: crypto.createHash('sha256').update(bytes).digest('hex') };
  });
}

function validateDossier(dossier) {
  const errors = [];
  const isObject = value => value !== null && typeof value === 'object' && !Array.isArray(value);
  if (!isObject(dossier)) return ['dossier must be an object'];
  const exactKeys = (object, keys, label) => {
    const actual = Object.keys(object).sort();
    const expected = [...keys].sort();
    if (actual.length !== expected.length || actual.some((key, index) => key !== expected[index])) errors.push(label + ' has missing or unexpected fields');
  };
  exactKeys(dossier, ['dossier_version', 'created_at_utc', 'identity', 'technical_evidence', 'declaration_and_proofs', 'bootstrap_routing'], 'dossier');
  if (dossier.dossier_version !== DOSSIER_VERSION) errors.push('dossier_version must equal 1.0.0');
  if (typeof dossier.created_at_utc !== 'string' || Number.isNaN(Date.parse(dossier.created_at_utc)) || !dossier.created_at_utc.endsWith('Z')) errors.push('created_at_utc must be a valid UTC date-time');
  if (!isObject(dossier.identity)) errors.push('identity must be an object');
  if (!isObject(dossier.technical_evidence)) errors.push('technical_evidence must be an object');
  if (!isObject(dossier.declaration_and_proofs)) errors.push('declaration_and_proofs must be an object');
  if (!isObject(dossier.bootstrap_routing)) errors.push('bootstrap_routing must be an object');
  if (errors.length) return errors;

  exactKeys(dossier.identity, ['alias', 'rsa_public_key_pem', 'fingerprint_sha256'], 'identity');
  exactKeys(dossier.technical_evidence, ['claimed_toolchain', 'artifacts', 'evidence_status'], 'technical_evidence');
  exactKeys(dossier.declaration_and_proofs, ['manifesto_text', 'signature_algorithm', 'rsa_signature_base64', 'ots_timestamp_proof'], 'declaration_and_proofs');
  exactKeys(dossier.bootstrap_routing, ['target_node_alias', 'endpoint_address', 'connection_protocol'], 'bootstrap_routing');
  const identity = dossier.identity;
  const evidence = dossier.technical_evidence;
  const proofs = dossier.declaration_and_proofs;
  const routing = dossier.bootstrap_routing;
  if (typeof identity.alias !== 'string' || !identity.alias.trim()) errors.push('identity.alias is required');
  if (typeof identity.rsa_public_key_pem !== 'string' || !identity.rsa_public_key_pem.includes('BEGIN PUBLIC KEY')) errors.push('identity.rsa_public_key_pem must be an SPKI PEM public key');
  if (typeof identity.fingerprint_sha256 !== 'string' || !/^[a-f0-9]{64}$/.test(identity.fingerprint_sha256)) errors.push('identity.fingerprint_sha256 must be a lowercase SHA-256 hex digest');
  if (!Array.isArray(evidence.artifacts)) errors.push('technical_evidence.artifacts must be an array');
  else evidence.artifacts.forEach((artifact, index) => {
    if (!isObject(artifact) || typeof artifact.name !== 'string' || !Number.isSafeInteger(artifact.size_bytes) || artifact.size_bytes < 0 || typeof artifact.sha256 !== 'string' || !/^[a-f0-9]{64}$/.test(artifact.sha256)) errors.push('technical_evidence.artifacts[' + index + '] is invalid');
  });
  if (typeof evidence.claimed_toolchain !== 'string') errors.push('technical_evidence.claimed_toolchain must be a string');
  if (!['HASHED_NOT_INDEPENDENTLY_ATTESTED', 'NO_ARTIFACTS_PROVIDED'].includes(evidence.evidence_status)) errors.push('technical_evidence.evidence_status is invalid');
  if (typeof proofs.manifesto_text !== 'string' || !proofs.manifesto_text.trim()) errors.push('declaration_and_proofs.manifesto_text is required');
  if (proofs.signature_algorithm !== 'RSA-PSS-SHA256') errors.push('signature_algorithm must be RSA-PSS-SHA256');
  if (typeof proofs.rsa_signature_base64 !== 'string' || !/^[A-Za-z0-9+/]+={0,2}$/.test(proofs.rsa_signature_base64)) errors.push('declaration_and_proofs.rsa_signature_base64 must be base64');
  if (proofs.ots_timestamp_proof !== null) {
    const proof = proofs.ots_timestamp_proof;
    if (!isObject(proof)) errors.push('declaration_and_proofs.ots_timestamp_proof must be null or an object');
    else {
      exactKeys(proof, ['file_name', 'encoding', 'proof_base64', 'proof_sha256', 'attested_digest_sha256', 'verification_status'], 'ots_timestamp_proof');
      if (typeof proof.file_name !== 'string' || !proof.file_name) errors.push('OTS proof file_name is required');
      if (proof.encoding !== 'base64') errors.push('OTS proof encoding must be base64');
      if (typeof proof.proof_base64 !== 'string' || !proof.proof_base64) errors.push('OTS proof data is required');
      if (typeof proof.proof_sha256 !== 'string' || !/^[a-f0-9]{64}$/.test(proof.proof_sha256)) errors.push('OTS proof hash is invalid');
      if (typeof proof.attested_digest_sha256 !== 'string' || !/^[a-f0-9]{64}$/.test(proof.attested_digest_sha256)) errors.push('OTS attested digest is invalid');
      if (proof.verification_status !== 'NOT_VERIFIED_BY_THIS_TOOL') errors.push('OTS proof status is invalid');
    }
  }
  if (typeof routing.target_node_alias !== 'string' || !routing.target_node_alias.trim()) errors.push('bootstrap_routing.target_node_alias is required');
  if (routing.endpoint_address !== null && typeof routing.endpoint_address !== 'string') errors.push('bootstrap_routing.endpoint_address must be null or a string');
  if (routing.connection_protocol !== null && typeof routing.connection_protocol !== 'string') errors.push('bootstrap_routing.connection_protocol must be null or a string');
  return errors;
}

function unsignedDossier(dossier) {
  const copy = JSON.parse(JSON.stringify(dossier));
  delete copy.declaration_and_proofs.rsa_signature_base64;
  return copy;
}

function buildDossier({
  alias, manifestoText, identityDirectory: directory = identityDirectory(),
  passphrase = process.env.NODE_CORE_EULORA2_PASSPHRASE, evidencePaths = [], otsProofPath = null,
  claimedToolchain = 'NOT_ASSERTED', targetNodeAlias = 'UNCONFIRMED_RECIPIENT',
  endpointAddress = null, connectionProtocol = null, now = new Date()
}) {
  if (typeof alias !== 'string' || !alias.trim() || alias.length > 128) throw new Error('Provide a non-empty applicant alias (maximum 128 characters).');
  if (typeof manifestoText !== 'string' || !manifestoText.trim()) throw new Error('A non-empty admission declaration is required.');
  if (typeof passphrase !== 'string' || passphrase.length < 16) throw new Error('Set NODE_CORE_EULORA2_PASSPHRASE to the passphrase for the encrypted private key.');
  const identity = readIdentity(directory);
  const artifacts = collectEvidence(evidencePaths);
  const dossier = {
    dossier_version: DOSSIER_VERSION,
    created_at_utc: now.toISOString(),
    identity: { alias: alias.trim(), rsa_public_key_pem: identity.publicKeyPem, fingerprint_sha256: identity.fingerprint },
    technical_evidence: {
      claimed_toolchain: claimedToolchain, artifacts,
      evidence_status: artifacts.length ? 'HASHED_NOT_INDEPENDENTLY_ATTESTED' : 'NO_ARTIFACTS_PROVIDED'
    },
    declaration_and_proofs: {
      manifesto_text: manifestoText, signature_algorithm: 'RSA-PSS-SHA256',
      rsa_signature_base64: '', ots_timestamp_proof: null
    },
    bootstrap_routing: { target_node_alias: targetNodeAlias, endpoint_address: endpointAddress, connection_protocol: connectionProtocol }
  };
  if (otsProofPath) {
    const proof = fs.readFileSync(otsProofPath);
    if (!proof.length) throw new Error('OpenTimestamps proof file is empty.');
    dossier.declaration_and_proofs.ots_timestamp_proof = {
      file_name: path.basename(otsProofPath), encoding: 'base64', proof_base64: proof.toString('base64'),
      proof_sha256: crypto.createHash('sha256').update(proof).digest('hex'),
      attested_digest_sha256: crypto.createHash('sha256').update(canonicalJson(unsignedDossier(dossier))).digest('hex'),
      verification_status: 'NOT_VERIFIED_BY_THIS_TOOL'
    };
  }
  const privateKey = crypto.createPrivateKey({ key: identity.privateKeyPem, format: 'pem', passphrase });
  const signature = crypto.sign('sha256', Buffer.from(canonicalJson(unsignedDossier(dossier))), {
    key: privateKey, padding: crypto.constants.RSA_PKCS1_PSS_PADDING, saltLength: 32
  });
  dossier.declaration_and_proofs.rsa_signature_base64 = signature.toString('base64');
  const errors = validateDossier(dossier);
  if (errors.length) throw new Error('Generated dossier failed schema validation: ' + errors.join('; '));
  return dossier;
}

function verifyDossier(dossier) {
  const errors = validateDossier(dossier);
  if (errors.length) return { valid: false, errors };
  try {
    const fingerprint = publicKeyFingerprint(dossier.identity.rsa_public_key_pem);
    if (fingerprint !== dossier.identity.fingerprint_sha256) return { valid: false, errors: ['Public-key fingerprint does not match public key.'] };
    const publicKey = crypto.createPublicKey(dossier.identity.rsa_public_key_pem);
    const signature = Buffer.from(dossier.declaration_and_proofs.rsa_signature_base64, 'base64');
    const validSignature = crypto.verify('sha256', Buffer.from(canonicalJson(unsignedDossier(dossier))), {
      key: publicKey, padding: crypto.constants.RSA_PKCS1_PSS_PADDING, saltLength: 32
    }, signature);
    if (!validSignature) return { valid: false, errors: ['Dossier signature verification failed.'] };
    return {
      valid: true, errors: [], fingerprint_sha256: fingerprint, signature_valid: true,
      evidence_status: dossier.technical_evidence.evidence_status,
      ots_proof_present: dossier.declaration_and_proofs.ots_timestamp_proof !== null,
      ots_proof_verified: false,
      admission_decision: 'NOT_DETERMINED_BY_CRYPTOGRAPHIC_VERIFICATION'
    };
  } catch (error) {
    return { valid: false, errors: ['Verification error: ' + error.message] };
  }
}

function parseArgs(argv) {
  const options = {};
  const repeated = new Set(['evidence']);
  for (let i = 0; i < argv.length; i++) {
    const token = argv[i];
    if (!token.startsWith('--')) throw new Error('Unexpected positional argument: ' + token);
    const key = token.slice(2);
    if (key === 'allow-unverified-protocol') { options[key] = true; continue; }
    if (i + 1 >= argv.length || argv[i + 1].startsWith('--')) throw new Error('Missing value for --' + key);
    const value = argv[++i];
    if (repeated.has(key)) (options[key] ||= []).push(value);
    else if (Object.hasOwn(options, key)) throw new Error('Option --' + key + ' may only be specified once.');
    else options[key] = value;
  }
  return options;
}

module.exports = { DOSSIER_VERSION, canonicalJson, publicKeyFingerprint, identityDirectory, generateIdentity, readIdentity, collectEvidence, validateDossier, buildDossier, verifyDossier, parseArgs };
