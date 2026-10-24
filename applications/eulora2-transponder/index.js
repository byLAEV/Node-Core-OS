#!/usr/bin/env node
'use strict';

const { spawnSync } = require('node:child_process');
const commands = new Set(['generate-key', 'build-payload', 'verify-dossier', 'transmit', 'test']);
const command = process.argv[2] || 'help';

if (command === 'help' || command === '--help' || command === '-h') {
  console.log('byLAEV Eulora 2 Applicant Transponder\n\nUsage:\n  node index.js generate-key\n  node index.js build-payload --alias ALIAS [--evidence FILE ...] [--ots-proof FILE]\n  node index.js verify-dossier [--file FILE]\n  node index.js transmit --host HOST --port PORT --protocol json-line-v1 --allow-unverified-protocol\n  node index.js test\n\nNo recipient endpoint or Eulora 2 wire protocol is assumed. Transmission is disabled unless explicit opt-in flags are supplied.');
  process.exit(0);
}
if (!commands.has(command)) {
  console.error('Unknown command: ' + command);
  process.exit(2);
}
if (command === 'test') {
  const result = spawnSync(process.execPath, ['--test'], { stdio: 'inherit', cwd: __dirname });
  process.exit(result.status === null ? 1 : result.status);
}
const scriptByCommand = {
  'generate-key': 'scripts/generate_keys.js',
  'build-payload': 'scripts/build_payload.js',
  'verify-dossier': 'scripts/verify_dossier.js',
  'transmit': 'scripts/transmit_payload.js'
};
const result = spawnSync(process.execPath, [scriptByCommand[command], ...process.argv.slice(3)], { stdio: 'inherit', cwd: __dirname });
process.exit(result.status === null ? 1 : result.status);
