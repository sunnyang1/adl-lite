/**
 * Format a timestamp string into a human-readable date/time.
 *
 * @param timestamp - ISO 8601 timestamp string
 * @returns Formatted date string (e.g., "2024-01-15 14:30:00")
 */
export function formatTimestamp(timestamp: string): string {
  const date: Date = new Date(timestamp);
  const year: number = date.getFullYear();
  const month: string = String(date.getMonth() + 1).padStart(2, '0');
  const day: string = String(date.getDate()).padStart(2, '0');
  const hours: string = String(date.getHours()).padStart(2, '0');
  const minutes: string = String(date.getMinutes()).padStart(2, '0');
  const seconds: string = String(date.getSeconds()).padStart(2, '0');
  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
}

/**
 * Format a timestamp string into a relative time description.
 *
 * @param timestamp - ISO 8601 timestamp string
 * @returns Relative time string (e.g., "2 hours ago", "3 days ago")
 */
export function formatRelativeTime(timestamp: string): string {
  const date: Date = new Date(timestamp);
  const now: Date = new Date();
  const diffMs: number = now.getTime() - date.getTime();

  const seconds: number = Math.floor(diffMs / 1000);
  const minutes: number = Math.floor(seconds / 60);
  const hours: number = Math.floor(minutes / 60);
  const days: number = Math.floor(hours / 24);

  if (days > 0) return `${days} day${days > 1 ? 's' : ''} ago`;
  if (hours > 0) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
  if (minutes > 0) return `${minutes} min${minutes > 1 ? 's' : ''} ago`;
  return `${seconds} sec${seconds > 1 ? 's' : ''} ago`;
}

/**
 * Format a confidence value as a percentage string.
 *
 * @param confidence - Confidence value between 0 and 1
 * @param decimals - Number of decimal places (default: 1)
 * @returns Formatted percentage string (e.g., "92.0%")
 */
export function formatConfidence(
  confidence: number,
  decimals: number = 1,
): string {
  const percentage: number = confidence * 100;
  return `${percentage.toFixed(decimals)}%`;
}

/**
 * Format a confidence value as a decimal string.
 *
 * @param confidence - Confidence value between 0 and 1
 * @param decimals - Number of decimal places (default: 3)
 * @returns Formatted decimal string (e.g., "0.920")
 */
export function formatConfidenceDecimal(
  confidence: number,
  decimals: number = 3,
): string {
  return confidence.toFixed(decimals);
}

/**
 * Truncate a long identifier string for display.
 *
 * @param id - The identifier string
 * @param maxLength - Maximum length before truncation (default: 24)
 * @returns Truncated string with ellipsis if needed
 */
export function truncateId(id: string, maxLength: number = 24): string {
  if (id.length <= maxLength) {
    return id;
  }
  return `${id.slice(0, maxLength - 3)}...`;
}
