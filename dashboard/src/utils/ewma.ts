import { EWMA_ALPHA } from '@/utils/constants';
import { EwmaPoint } from '@/api/types';

/**
 * Compute the Exponentially Weighted Moving Average (EWMA) for a series of values.
 *
 * EWMA formula: s_t = α * x_t + (1 - α) * s_{t-1}
 *
 * @param values - Array of raw values to smooth
 * @param alpha - Smoothing factor (default: EWMA_ALPHA = 0.3)
 * @returns Array of smoothed values, same length as input
 */
export function computeEwma(
  values: number[],
  alpha: number = EWMA_ALPHA,
): number[] {
  if (values.length === 0) {
    return [];
  }

  const smoothed: number[] = [values[0]];

  for (let i = 1; i < values.length; i++) {
    const s: number = alpha * values[i] + (1 - alpha) * smoothed[i - 1];
    smoothed.push(s);
  }

  return smoothed;
}

/**
 * Compute EWMA curve data points from an array of events with timestamps and confidence values.
 *
 * @param timestamps - Array of timestamp strings
 * @param rawValues - Array of raw confidence values
 * @param alpha - Smoothing factor (default: EWMA_ALPHA = 0.3)
 * @returns Array of EwmaPoint objects with timestamp, raw, and smoothed values
 */
export function computeEwmaCurve(
  timestamps: string[],
  rawValues: number[],
  alpha: number = EWMA_ALPHA,
): EwmaPoint[] {
  const smoothedValues: number[] = computeEwma(rawValues, alpha);

  return timestamps.map((timestamp: string, index: number) => ({
    timestamp,
    raw: rawValues[index],
    smoothed: smoothedValues[index],
  }));
}
