import { useMemo } from 'react';
import { computeEwmaCurve } from '@/utils/ewma';
import { EventDict, EwmaPoint } from '@/api/types';

/**
 * Compute EWMA curve from capability history events.
 *
 * Extracts timestamps and confidence-related values from events,
 * then computes EWMA-smoothed series for visualization.
 *
 * @param events - Array of events from the capability history
 * @param alpha - EWMA smoothing factor (default: 0.3)
 * @returns Array of EwmaPoint data for charting
 */
export function useEwmaCurve(
  events: EventDict[],
  alpha: number = 0.3,
): EwmaPoint[] {
  const ewmaPoints = useMemo(() => {
    const timestamps: string[] = events.map(
      (event: EventDict) => event.timestamp,
    );

    const rawValues: number[] = events.map((event: EventDict) => {
      const payloadConfidence: number =
        (event.payload?.confidence as number) ?? 0;
      return payloadConfidence;
    });

    return computeEwmaCurve(timestamps, rawValues, alpha);
  }, [events, alpha]);

  return ewmaPoints;
}
