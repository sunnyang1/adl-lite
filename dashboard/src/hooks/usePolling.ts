import { useRef, useCallback } from 'react';

/**
 * Hook for managing 30-second auto-refresh polling.
 *
 * Provides a callback that triggers a refetch via React Query's refetch function,
 * and tracks the last updated timestamp.
 *
 * @param refetch - React Query's refetch function
 * @returns Object with lastUpdated timestamp and manualRefresh callback
 */
export function usePolling(
  refetch: () => Promise<unknown>,
): {
  lastUpdated: Date;
  manualRefresh: () => void;
} {
  const lastUpdatedRef = useRef<Date>(new Date());

  const manualRefresh = useCallback(() => {
    refetch();
    lastUpdatedRef.current = new Date();
  }, [refetch]);

  // React Query's refetchInterval handles automatic polling;
  // this hook provides manual refresh + last-updated tracking
  return {
    lastUpdated: lastUpdatedRef.current,
    manualRefresh,
  };
}
