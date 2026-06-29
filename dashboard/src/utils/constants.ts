/** Polling interval in milliseconds (30 seconds) */
export const POLL_INTERVAL = 30_000;

/** EWMA smoothing factor */
export const EWMA_ALPHA = 0.3;

/** API base URL from environment */
export const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

/** Confidence color thresholds */
export const CONFIDENCE_THRESHOLDS = {
  HIGH: 0.8,
  MEDIUM: 0.5,
  LOW: 0,
} as const;

/** Status emoji mapping */
export const STATUS_EMOJI_MAP: Record<string, string> = {
  provisional: '🟡',
  validated: '🟢',
  deprecated: '🔴',
  forked: '🔵',
  archived: '⚪',
};

/** Default pagination limit */
export const DEFAULT_PAGE_LIMIT = 20;

/** Default pagination offset */
export const DEFAULT_PAGE_OFFSET = 0;
