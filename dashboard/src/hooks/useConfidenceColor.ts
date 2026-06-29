import { useMemo } from 'react';
import {
  getConfidenceColorLevel,
  getConfidenceColorHex,
  getConfidenceMuiColor,
  ConfidenceColorLevel,
} from '@/utils/confidenceColor';

/**
 * Hook wrapper for the confidenceColor utility functions.
 *
 * Provides memoized color mappings for a given confidence value.
 *
 * @param confidence - Confidence value between 0 and 1
 * @returns Object with color level, hex color, and MUI color name
 */
export function useConfidenceColor(confidence: number): {
  level: ConfidenceColorLevel;
  hexColor: string;
  muiColor: 'success' | 'warning' | 'error';
} {
  const level = useMemo(
    () => getConfidenceColorLevel(confidence),
    [confidence],
  );
  const hexColor = useMemo(
    () => getConfidenceColorHex(confidence),
    [confidence],
  );
  const muiColor = useMemo(
    () => getConfidenceMuiColor(confidence),
    [confidence],
  );

  return { level, hexColor, muiColor };
}
