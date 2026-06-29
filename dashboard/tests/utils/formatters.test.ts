import { describe, it, expect } from 'vitest';
import {
  formatTimestamp,
  formatRelativeTime,
  formatConfidence,
  formatConfidenceDecimal,
  truncateId,
} from '@/utils/formatters';

describe('formatTimestamp', () => {
  it('formats ISO timestamp to readable date/time', () => {
    const result = formatTimestamp('2024-01-15T14:30:00Z');
    // Result depends on local timezone, so check the format structure
    expect(result).toMatch(/\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}/);
  });

  it('handles empty string gracefully', () => {
    const result = formatTimestamp('');
    // Invalid date produces "NaN" values
    expect(result).toContain('NaN');
  });
});

describe('formatRelativeTime', () => {
  it('returns seconds ago for recent timestamps', () => {
    const now = new Date();
    const fiveSecondsAgo = new Date(now.getTime() - 5000).toISOString();
    const result = formatRelativeTime(fiveSecondsAgo);
    expect(result).toContain('sec');
  });

  it('returns minutes ago for timestamps within an hour', () => {
    const now = new Date();
    const tenMinutesAgo = new Date(now.getTime() - 600_000).toISOString();
    const result = formatRelativeTime(tenMinutesAgo);
    expect(result).toContain('min');
  });

  it('returns hours ago for timestamps within a day', () => {
    const now = new Date();
    const twoHoursAgo = new Date(now.getTime() - 7200_000).toISOString();
    const result = formatRelativeTime(twoHoursAgo);
    expect(result).toContain('hour');
  });

  it('returns days ago for older timestamps', () => {
    const now = new Date();
    const threeDaysAgo = new Date(now.getTime() - 259200_000).toISOString();
    const result = formatRelativeTime(threeDaysAgo);
    expect(result).toContain('day');
  });
});

describe('formatConfidence', () => {
  it('formats confidence as percentage with default 1 decimal', () => {
    expect(formatConfidence(0.92)).toBe('92.0%');
    expect(formatConfidence(0.5)).toBe('50.0%');
    expect(formatConfidence(0)).toBe('0.0%');
  });

  it('formats confidence with custom decimals', () => {
    expect(formatConfidence(0.9234, 2)).toBe('92.34%');
    expect(formatConfidence(0.9234, 0)).toBe('92%');
  });
});

describe('formatConfidenceDecimal', () => {
  it('formats confidence as decimal with default 3 decimals', () => {
    expect(formatConfidenceDecimal(0.92)).toBe('0.920');
    expect(formatConfidenceDecimal(0.5)).toBe('0.500');
  });

  it('formats confidence with custom decimals', () => {
    expect(formatConfidenceDecimal(0.92, 2)).toBe('0.92');
  });
});

describe('truncateId', () => {
  it('returns full ID when shorter than max length', () => {
    expect(truncateId('cap-nlp')).toBe('cap-nlp');
  });

  it('truncates long IDs with ellipsis', () => {
    const longId = 'cap-very-long-capability-id-that-exceeds-max';
    expect(truncateId(longId, 24)).toBe('cap-very-long-capabil...');
  });

  it('uses default max length of 24', () => {
    const id23 = 'a'.repeat(23);
    const id24 = 'a'.repeat(24);
    const id25 = 'a'.repeat(25);
    expect(truncateId(id23)).toBe(id23);
    expect(truncateId(id24)).toBe(id24);
    expect(truncateId(id25)).toBe(`${'a'.repeat(21)}...`);
  });
});
