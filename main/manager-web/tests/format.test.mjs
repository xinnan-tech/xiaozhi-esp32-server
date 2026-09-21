import { describe, it, expect } from 'vitest';
import * as format from '../src/utils/format.js';

describe('format utilities', () => {
  it('module loads and exports functions', () => {
    expect(format).toBeDefined();
    expect(Object.keys(format).length).toBeGreaterThan(0);
  });

  describe('formatDate', () => {
    it('returns empty string for falsy values', () => {
      expect(format.formatDate(null)).toBe('');
      expect(format.formatDate(undefined)).toBe('');
      expect(format.formatDate('')).toBe('');
      expect(format.formatDate(0)).toBe('');
    });

    it('formats a Date object as YYYY-MM-DD HH:mm:ss', () => {
      const date = new Date(2026, 8, 2, 13, 4, 5); // Sep 2, 2026 13:04:05 (local)
      expect(format.formatDate(date)).toBe('2026-09-02 13:04:05');
    });

    it('accepts ISO date strings', () => {
      expect(format.formatDate('2026-01-15T08:30:00Z')).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/);
    });

    it('zero-pads single digit components', () => {
      const date = new Date(2026, 0, 5, 7, 8, 9); // Jan 5, 2026 07:08:09
      expect(format.formatDate(date)).toBe('2026-01-05 07:08:09');
    });
  });

  describe('formatFileSize', () => {
    it('returns 0 B for falsy values', () => {
      expect(format.formatFileSize(0)).toBe('0 B');
      expect(format.formatFileSize(null)).toBe('0 B');
      expect(format.formatFileSize(undefined)).toBe('0 B');
    });

    it('formats bytes in B', () => {
      expect(format.formatFileSize(512)).toBe('512 B');
    });

    it('formats kilobytes', () => {
      expect(format.formatFileSize(1024)).toBe('1 KB');
      expect(format.formatFileSize(1536)).toBe('1.5 KB');
    });

    it('formats megabytes and above', () => {
      expect(format.formatFileSize(1024 * 1024)).toBe('1 MB');
      expect(format.formatFileSize(2.5 * 1024 * 1024)).toBe('2.5 MB');
      expect(format.formatFileSize(1024 ** 3)).toBe('1 GB');
      expect(format.formatFileSize(1024 ** 4)).toBe('1 TB');
    });
  });
});