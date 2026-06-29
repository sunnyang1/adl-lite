import { describe, it, expect } from 'vitest';
import { computeEwma, computeEwmaCurve } from '@/utils/ewma';

describe('computeEwma', () => {
  it('returns empty array for empty input', () => {
    const result = computeEwma([]);
    expect(result).toEqual([]);
  });

  it('returns single value for single-item input', () => {
    const result = computeEwma([0.5]);
    expect(result).toEqual([0.5]);
  });

  it('computes EWMA correctly with default alpha=0.3', () => {
    const values = [1.0, 2.0, 3.0, 4.0];
    const result = computeEwma(values, 0.3);

    // s0 = 1.0
    expect(result[0]).toBeCloseTo(1.0);
    // s1 = 0.3 * 2.0 + 0.7 * 1.0 = 1.3
    expect(result[1]).toBeCloseTo(1.3);
    // s2 = 0.3 * 3.0 + 0.7 * 1.3 = 1.81
    expect(result[2]).toBeCloseTo(1.81);
    // s3 = 0.3 * 4.0 + 0.7 * 1.81 = 2.467
    expect(result[3]).toBeCloseTo(2.467);
  });

  it('computes EWMA correctly with custom alpha=0.5', () => {
    const values = [1.0, 2.0, 3.0];
    const result = computeEwma(values, 0.5);

    // s0 = 1.0
    expect(result[0]).toBeCloseTo(1.0);
    // s1 = 0.5 * 2.0 + 0.5 * 1.0 = 1.5
    expect(result[1]).toBeCloseTo(1.5);
    // s2 = 0.5 * 3.0 + 0.5 * 1.5 = 2.25
    expect(result[2]).toBeCloseTo(2.25);
  });

  it('handles all-zero values', () => {
    const values = [0, 0, 0, 0];
    const result = computeEwma(values);
    expect(result).toEqual([0, 0, 0, 0]);
  });

  it('handles decreasing values', () => {
    const values = [1.0, 0.8, 0.6, 0.4];
    const result = computeEwma(values, 0.3);

    expect(result[0]).toBeCloseTo(1.0);
    expect(result[1]).toBeCloseTo(0.94);
    expect(result[2]).toBeCloseTo(0.838);
  });
});

describe('computeEwmaCurve', () => {
  it('returns empty array for empty inputs', () => {
    const result = computeEwmaCurve([], []);
    expect(result).toEqual([]);
  });

  it('computes EwmaPoint objects with timestamps', () => {
    const timestamps = ['2024-01-01T00:00:00Z', '2024-01-02T00:00:00Z'];
    const rawValues = [0.5, 0.8];
    const result = computeEwmaCurve(timestamps, rawValues);

    expect(result.length).toBe(2);
    expect(result[0].timestamp).toBe('2024-01-01T00:00:00Z');
    expect(result[0].raw).toBe(0.5);
    expect(result[0].smoothed).toBe(0.5);
    expect(result[1].timestamp).toBe('2024-01-02T00:00:00Z');
    expect(result[1].raw).toBe(0.8);
    expect(result[1].smoothed).toBeCloseTo(0.3 * 0.8 + 0.7 * 0.5);
  });
});
