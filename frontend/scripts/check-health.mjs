import assert from 'node:assert/strict';
import { normalizeHealth } from '../src/lib/health.ts';

const publicHealth = {
  status: 'degraded', mode: 'real',
  extraction: { ready: true, ocr: { available: false, languages: [] } },
  ml: { available: false },
};
assert.equal(normalizeHealth(publicHealth).extraction_ready, true);
assert.equal(normalizeHealth(publicHealth).model_ready, false);
assert.deepEqual(normalizeHealth(publicHealth).ocr_languages, []);
assert.deepEqual(normalizeHealth(publicHealth).tested_matrix, { input: [], output: [] });
assert.equal(normalizeHealth({ ...publicHealth, ml: { available: true } }).model_ready, true);
assert.equal(normalizeHealth({ ...publicHealth, mode: 'fixture', ml: { available: true } }).model_ready, false);
assert.equal(normalizeHealth({}).extraction_ready, false);
console.log('Health-contract regression checks passed.');
