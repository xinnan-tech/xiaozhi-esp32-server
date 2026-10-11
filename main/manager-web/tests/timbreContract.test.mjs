import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const timbreApiSource = await readFile(
  new URL('../src/apis/module/timbre.js', import.meta.url),
  'utf8',
);

test('timbre update sends the current sort value to the backend', () => {
  const updateStart = timbreApiSource.indexOf('updateVoice(params, callback)');

  assert.notEqual(updateStart, -1);
  const updateSource = timbreApiSource.slice(updateStart);
  assert.match(updateSource, /\.method\('PUT'\)/);
  assert.match(updateSource, /sort:\s*params\.sort/);
});
