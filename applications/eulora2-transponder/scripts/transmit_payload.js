#!/usr/bin/env node
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const net = require('node:net');
const crypto = require('node:crypto');
const { parseArgs, verifyDossier, canonicalJson } = require('../lib/transponder');

const MAX_PAYLOAD_BYTES = 1024 * 1024;
const ACK_TIMEOUT_MS = 10000;

async function transmit(options) {
  if (!options.host || !options.port) throw new Error('Transmission requires explicit --host and --port.');
  if (options.protocol !== 'json-line-v1') throw new Error('Only experimental json-line-v1 is implemented; EuComms/VaMP compatibility is unverified.');
  if (!options['allow-unverified-protocol']) throw new Error('Transmission blocked. Add --allow-unverified-protocol only after confirming recipient, endpoint, wire protocol, and authorization independently.');
  const port = Number(options.port);
  if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error('--port must be an integer from 1 to 65535.');
  const filePath = path.resolve(options.file || 'payload_eulora2_dossier.json');
  const raw = fs.readFileSync(filePath);
  if (raw.length > MAX_PAYLOAD_BYTES) throw new Error('Dossier exceeds 1 MiB transmission limit.');
  const dossier = JSON.parse(raw.toString('utf8'));
  const verification = verifyDossier(dossier);
  if (!verification.valid) throw new Error('Local dossier verification failed: ' + verification.errors.join('; '));
  const digest = crypto.createHash('sha256').update(canonicalJson(dossier)).digest('hex');
  const wireMessage = Buffer.from(JSON.stringify({ protocol: 'json-line-v1', payload_sha256: digest, dossier }) + '\n', 'utf8');

  await new Promise((resolve, reject) => {
    let response = '';
    let settled = false;
    const socket = net.createConnection({ host: options.host, port });
    const timer = setTimeout(() => finish(new Error('Timed out waiting for a matching JSON acknowledgement.')), ACK_TIMEOUT_MS);
    function finish(error) {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      socket.destroy();
      if (error) reject(error); else resolve();
    }
    socket.setTimeout(ACK_TIMEOUT_MS);
    socket.on('connect', () => socket.write(wireMessage));
    socket.on('data', chunk => {
      response += chunk.toString('utf8');
      if (response.length > 65536) return finish(new Error('Receiver response exceeded 64 KiB.'));
      const newline = response.indexOf('\n');
      if (newline < 0) return;
      let acknowledgement;
      try { acknowledgement = JSON.parse(response.slice(0, newline)); }
      catch { return finish(new Error('Receiver did not return valid JSON acknowledgement.')); }
      if (acknowledgement.protocol !== 'json-line-v1-ack' || acknowledgement.status !== 'accepted' || acknowledgement.payload_sha256 !== digest) {
        return finish(new Error('Receiver acknowledgement did not confirm acceptance of this exact payload digest.'));
      }
      finish();
    });
    socket.on('timeout', () => finish(new Error('Socket timed out before a matching acknowledgement.')));
    socket.on('error', error => finish(new Error('Transmission failed: ' + error.message)));
    socket.on('close', () => { if (!settled) finish(new Error('Connection closed before a matching acknowledgement.')); });
  });
  console.log('Receiver acknowledged payload digest: ' + digest);
  console.log('This confirms only the receiver response; it does not establish Eulora admission or a WoT rating.');
}
transmit(parseArgs(process.argv.slice(2))).catch(error => {
  console.error('[Transmission blocked/failed] ' + error.message);
  process.exitCode = 1;
});
