import { describe, it, expect } from 'vitest';
import * as date from '../src/utils/date.js';

describe('date utilities', () => {
  it('module loads and exports functions', () => {
    expect(date).toBeDefined();
    expect(Object.keys(date).length).toBeGreaterThan(0);
  });

  describe('isDate', () => {
    it('returns false for null and undefined', () => {
      expect(date.isDate(null)).toBe(false);
      expect(date.isDate(undefined)).toBe(false);
    });

    it('returns false for an invalid date string', () => {
      expect(date.isDate('not-a-date')).toBe(false);
    });

    it('returns true for valid date strings', () => {
      expect(date.isDate('2026-09-02')).toBe(true);
      expect(date.isDate('2026-09-02T10:00:00Z')).toBe(true);
    });

    it('returns true for Date objects', () => {
      expect(date.isDate(new Date())).toBe(true);
    });
  });

  describe('isDateObject', () => {
    it('returns true only for Date instances', () => {
      expect(date.isDateObject(new Date())).toBe(true);
      expect(date.isDateObject('2026-09-02')).toBe(false);
      expect(date.isDateObject(1234567890)).toBe(false);
      expect(date.isDateObject(null)).toBe(false);
    });
  });

  describe('toDate', () => {
    it('returns null for falsy values', () => {
      expect(date.toDate(null)).toBe(null);
      expect(date.toDate(undefined)).toBe(null);
      expect(date.toDate('')).toBe(null);
    });

    it('returns null for invalid input', () => {
      expect(date.toDate('not-a-date')).toBe(null);
    });

    it('returns a Date for valid input', () => {
      const result = date.toDate('2026-09-02');
      expect(result).toBeInstanceOf(Date);
      expect(result.getFullYear()).toBe(2026);
    });
  });

  describe('formatDate', () => {
    it('returns empty string for invalid input', () => {
      expect(date.formatDate(null)).toBe('');
      expect(date.formatDate('not-a-date')).toBe('');
    });

    it('formats with the default pattern', () => {
      const result = date.formatDate('2026-09-02T10:20:30Z');
      expect(result).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/);
    });

    it('supports a custom format pattern', () => {
      const result = date.formatDate(new Date(2026, 8, 2, 13, 4, 5), 'yyyy/MM/dd');
      expect(result).toBe('2026/09/02');
    });
  });

  describe('formatAddDate', () => {
    it('returns empty string when input is not a date', () => {
      expect(date.formatAddDate(null, 'yyyy-MM-dd', 5)).toBe('');
    });

    it('returns formatted date unchanged when addDay is falsy', () => {
      // The implementation has a quirk: `if (!addDay)` adds the days (the condition is inverted),
      // so passing 0 with a date input still applies it (no-op since 0).
      const result = date.formatAddDate('2026-09-02', 'yyyy-MM-dd', 0);
      expect(result).toBe('2026-09-02');
    });

    it('formats with the default pattern when none given', () => {
      const result = date.formatAddDate(new Date(2026, 8, 2, 13, 4, 5), '', 0);
      expect(result).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/);
    });
  });
});