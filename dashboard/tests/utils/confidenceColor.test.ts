import { describe, it, expect } from 'vitest';
import {
  getConfidenceColorLevel,
  getConfidenceColorHex,
  getConfidenceMuiColor,
} from '@/utils/confidenceColor';

describe('getConfidenceColorLevel', () => {
  it('returns "high" for confidence >= 0.8', () => {
    expect(getConfidenceColorLevel(0.8)).toBe('high');
    expect(getConfidenceColorLevel(0.92)).toBe('high');
    expect(getConfidenceColorLevel(1.0)).toBe('high');
  });

  it('returns "medium" for confidence >= 0.5 and < 0.8', () => {
    expect(getConfidenceColorLevel(0.5)).toBe('medium');
    expect(getConfidenceColorLevel(0.65)).toBe('medium');
    expect(getConfidenceColorLevel(0.79)).toBe('medium');
  });

  it('returns "low" for confidence < 0.5', () => {
    expect(getConfidenceColorLevel(0.0)).toBe('low');
    expect(getConfidenceColorLevel(0.35)).toBe('low');
    expect(getConfidenceColorLevel(0.49)).toBe('low');
  });
});

describe('getConfidenceColorHex', () => {
  it('returns green hex for high confidence', () => {
    expect(getConfidenceColorHex(0.9)).toBe('#4caf50');
  });

  it('returns yellow hex for medium confidence', () => {
    expect(getConfidenceColorHex(0.6)).toBe('#ff9800');
  });

  it('returns red hex for low confidence', () => {
    expect(getConfidenceColorHex(0.3)).toBe('#f44336');
  });
});

describe('getConfidenceMuiColor', () => {
  it('returns "success" for high confidence', () => {
    expect(getConfidenceMuiColor(0.9)).toBe('success');
  });

  it('returns "warning" for medium confidence', () => {
    expect(getConfidenceMuiColor(0.6)).toBe('warning');
  });

  it('returns "error" for low confidence', () => {
    expect(getConfidenceMuiColor(0.3)).toBe('error');
  });
});
