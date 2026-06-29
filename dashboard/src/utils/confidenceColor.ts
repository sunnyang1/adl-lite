import { CONFIDENCE_THRESHOLDS } from '@/utils/constants';

/**
 * Confidence color thresholds:
 * - γ ≥ 0.8 → green (MUI success)
 * - γ ≥ 0.5 → yellow (MUI warning)
 * - γ < 0.5 → red (MUI error)
 */
export type ConfidenceColorLevel = 'high' | 'medium' | 'low';

/**
 * Map a confidence value (γ) to a color level.
 *
 * @param confidence - Confidence value between 0 and 1
 * @returns Color level: 'high' (≥0.8), 'medium' (≥0.5), 'low' (<0.5)
 */
export function getConfidenceColorLevel(
  confidence: number,
): ConfidenceColorLevel {
  if (confidence >= CONFIDENCE_THRESHOLDS.HIGH) {
    return 'high';
  }
  if (confidence >= CONFIDENCE_THRESHOLDS.MEDIUM) {
    return 'medium';
  }
  return 'low';
}

/**
 * Map a confidence value to a hex color string.
 *
 * @param confidence - Confidence value between 0 and 1
 * @returns Hex color string
 */
export function getConfidenceColorHex(confidence: number): string {
  const level: ConfidenceColorLevel = getConfidenceColorLevel(confidence);
  switch (level) {
    case 'high':
      return '#4caf50';
    case 'medium':
      return '#ff9800';
    case 'low':
      return '#f44336';
  }
}

/**
 * Map a confidence value to a MUI color name.
 *
 * @param confidence - Confidence value between 0 and 1
 * @returns MUI color name ('success', 'warning', or 'error')
 */
export function getConfidenceMuiColor(
  confidence: number,
): 'success' | 'warning' | 'error' {
  const level: ConfidenceColorLevel = getConfidenceColorLevel(confidence);
  switch (level) {
    case 'high':
      return 'success';
    case 'medium':
      return 'warning';
    case 'low':
      return 'error';
  }
}
