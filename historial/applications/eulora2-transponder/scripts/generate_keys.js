#!/usr/bin/env node
'use strict';
const { generateIdentity, identityDirectory } = require('../lib/transponder');
try {
  const result = generateIdentity({ directory: identityDirectory(), passphrase: process.env.NODE_CORE_EULORA2_PASSPHRASE });
  console.log('[byLAEV Transponder] RSA identity generated.');
  console.log('Private key (encrypted): ' + result.privatePath);
  console.log('Public key: ' + result.publicPath);
  console.log('Fingerprint SHA-256 (DER/SPKI): ' + result.fingerprint_sha256);
  console.log('Private key permissions: 0600; identity directory permissions: 0700.');
} catch (error) {
  console.error('[Identity generation failed] ' + error.message);
  process.exitCode = 1;
}
