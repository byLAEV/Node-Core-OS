#!/usr/bin/env node
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const { parseArgs, verifyDossier } = require('../lib/transponder');
try {
  const options = parseArgs(process.argv.slice(2));
  const filePath = path.resolve(options.file || 'payload_eulora2_dossier.json');
  const dossier = JSON.parse(fs.readFileSync(filePath, 'utf8'));
  const result = verifyDossier(dossier);
  console.log('[Dossier audit] ' + filePath);
  console.log('Fingerprint: ' + (result.fingerprint_sha256 || 'INVALID'));
  console.log('Signature: ' + (result.signature_valid ? 'VALID' : 'INVALID'));
  console.log('Evidence: ' + (result.evidence_status || 'INVALID'));
  console.log('OTS proof present: ' + (result.ots_proof_present ? 'YES' : 'NO'));
  console.log('OTS proof cryptographically verified by this tool: NO');
  console.log('Admission decision: NOT DETERMINED');
  if (!result.valid) {
    for (const error of result.errors) console.error('- ' + error);
    process.exitCode = 1;
  }
} catch (error) {
  console.error('[Dossier audit failed] ' + error.message);
  process.exitCode = 1;
}
