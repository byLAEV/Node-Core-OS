#!/usr/bin/env node
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const { buildDossier, parseArgs } = require('../lib/transponder');
try {
  const options = parseArgs(process.argv.slice(2));
  const alias = options.alias || process.env.NODE_CORE_EULORA2_ALIAS;
  if (!alias) throw new Error('Provide --alias or NODE_CORE_EULORA2_ALIAS.');
  const manifestoText = options.manifesto ? fs.readFileSync(path.resolve(options.manifesto), 'utf8') : process.env.NODE_CORE_EULORA2_MANIFESTO;
  if (!manifestoText) throw new Error('Provide --manifesto PATH or NODE_CORE_EULORA2_MANIFESTO.');
  const dossier = buildDossier({
    alias, manifestoText, evidencePaths: options.evidence || [], otsProofPath: options['ots-proof'] || null,
    claimedToolchain: options['claimed-toolchain'] || 'NOT_ASSERTED',
    targetNodeAlias: options['target-node'] || 'UNCONFIRMED_RECIPIENT',
    endpointAddress: options.endpoint || null, connectionProtocol: options.protocol || null
  });
  const outputPath = path.resolve(options.output || 'payload_eulora2_dossier.json');
  if (fs.existsSync(outputPath)) throw new Error('Refusing to overwrite existing dossier: ' + outputPath);
  fs.writeFileSync(outputPath, JSON.stringify(dossier, null, 2) + '\n', { mode: 0o600, flag: 'wx' });
  fs.chmodSync(outputPath, 0o600);
  console.log('[byLAEV Transponder] Dossier generated and locally signed.');
  console.log('Output: ' + outputPath);
  console.log('Evidence artifacts hashed: ' + dossier.technical_evidence.artifacts.length);
  console.log('Applicant fingerprint: ' + dossier.identity.fingerprint_sha256);
  console.log('Evidence status: ' + dossier.technical_evidence.evidence_status);
  console.log('No admission, external timestamp, recipient identity, or network delivery is implied.');
} catch (error) {
  console.error('[Dossier generation failed] ' + error.message);
  process.exitCode = 1;
}
