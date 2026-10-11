import { describe, it, expect } from 'vitest';
import {
  hasTimestampValue,
  parseTimestamp,
  parseLegacyDate,
  formatTimestamp,
  formatCreateDate,
  compareTimestamps,
} from '../src/utils/deviceTime.mjs';

describe('hasTimestampValue', () => {
  it('returns false for null', () => expect(hasTimestampValue(null)).toBe(false));
  it('returns false for undefined', () => expect(hasTimestampValue(undefined)).toBe(false));
  it('returns false for empty string', () => expect(hasTimestampValue('')).toBe(false));
  it('returns false for whitespace-only string', () => expect(hasTimestampValue('   ')).toBe(false));
  it('returns true for number', () => expect(hasTimestampValue(1234567890)).toBe(true));
  it('returns true for non-empty string', () => expect(hasTimestampValue('2026-09-02')).toBe(true));
});

describe('parseTimestamp', () => {
  it('returns null for null', () => expect(parseTimestamp(null)).toBe(null));
  it('returns null for empty string', () => expect(parseTimestamp('')).toBe(null));
  it('parses numeric string', () => {
    const ts = parseTimestamp('1234567890000');
    expect(typeof ts).toBe('number');
    expect(ts).toBe(1234567890000);
  });
  it('returns null for non-numeric string', () => expect(parseTimestamp('not-a-date')).toBe(null));
  it('parses number directly', () => expect(parseTimestamp(1234567890000)).toBe(1234567890000));
});

describe('parseLegacyDate', () => {
  it('returns null for empty', () => expect(parseLegacyDate('')).toBe(null));
  it('parses ISO date string', () => {
    const ts = parseLegacyDate('2026-09-02T10:00:00Z');
    expect(typeof ts).toBe('number');
    expect(ts).toBeGreaterThan(0);
  });
});

describe('formatTimestamp', () => {
  it('returns dash for null', () => expect(formatTimestamp(null)).toBe('-'));
  it('uses default formatter', () => {
    const out = formatTimestamp(0);
    expect(typeof out).toBe('string');
    expect(out).not.toBe('-');
  });
  it('accepts custom formatter', () => {
    expect(formatTimestamp(0, () => 'CUSTOM')).toBe('CUSTOM');
  });
});

describe('formatCreateDate', () => {
  it('falls back to legacy date when timestamp missing', () => {
    expect(formatCreateDate(null, 'fallback')).toBe('fallback');
  });
  it('falls back to dash when both missing', () => {
    expect(formatCreateDate(null, null)).toBe('-');
  });
});

describe('compareTimestamps', () => {
  it('returns negative when first < second', () => {
    expect(compareTimestamps(100, 200)).toBeLessThan(0);
  });
  it('returns positive when first > second', () => {
    expect(compareTimestamps(200, 100)).toBeGreaterThan(0);
  });
  it('returns 0 when both equal', () => {
    expect(compareTimestamps(100, 100)).toBe(0);
  });
  it('treats invalid as greater than nothing', () => {
    expect(compareTimestamps(100, NaN)).toBeLessThan(0);
  });
});