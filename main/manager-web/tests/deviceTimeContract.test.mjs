import assert from 'node:assert/strict';
import test from 'node:test';

import {
  compareTimestamps,
  formatCreateDate,
  formatTimestamp,
  parseTimestamp,
} from '../src/utils/deviceTime.mjs';

const TIMESTAMP = 1783689702000;

test('accepts epoch milliseconds as a number or numeric string', () => {
  assert.equal(parseTimestamp(TIMESTAMP), TIMESTAMP);
  assert.equal(parseTimestamp(String(TIMESTAMP)), TIMESTAMP);
  assert.equal(parseTimestamp(`  ${TIMESTAMP}  `), TIMESTAMP);
});

test('rejects missing, invalid and non-scalar timestamp values', () => {
  const invalidValues = [null, undefined, '', '   ', 'invalid', true, {}, [], Infinity, Number.MAX_VALUE];

  invalidValues.forEach(value => assert.equal(parseTimestamp(value), null));
  assert.equal(formatTimestamp('invalid'), '-');
});

test('falls back to the legacy createDate only when the timestamp is missing', () => {
  const legacyDate = '2026-07-10 21:21:42';
  const formatter = timestamp => `local:${timestamp}`;

  assert.equal(formatCreateDate(undefined, legacyDate, formatter), legacyDate);
  assert.equal(formatCreateDate('', legacyDate, formatter), legacyDate);
  assert.equal(formatCreateDate('invalid', legacyDate, formatter), '-');
  assert.equal(formatCreateDate(String(TIMESTAMP), legacyDate, formatter), `local:${TIMESTAMP}`);
});

test('formats the same instant consistently in each browser time zone', () => {
  const formatter = timeZone => timestamp => new Date(timestamp).toLocaleString('en-US', { timeZone });

  for (const timeZone of ['Asia/Shanghai', 'America/Sao_Paulo']) {
    assert.equal(
      formatTimestamp(TIMESTAMP, formatter(timeZone)),
      formatTimestamp(String(TIMESTAMP), formatter(timeZone)),
    );
  }
});

test('sorts valid epoch values first and leaves invalid values at the end', () => {
  const timestamps = [null, TIMESTAMP + 1, undefined, TIMESTAMP];

  assert.deepEqual(timestamps.sort(compareTimestamps), [TIMESTAMP, TIMESTAMP + 1, null, undefined]);
  assert.equal(compareTimestamps(null, undefined), 0);
});
