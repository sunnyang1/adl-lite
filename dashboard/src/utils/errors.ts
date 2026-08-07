/**
 * Extract a human-readable message from an unknown error value.
 *
 * The API client rejects with an `ErrorResponse` shape `{ detail, status_code }`,
 * but mutations can also surface plain `Error` instances or unexpected values.
 *
 * @param error - The caught error value (unknown)
 * @param fallback - Message to use when the error cannot be interpreted
 * @returns A string suitable for display in an alert
 */
export function errorMessage(error: unknown, fallback: string = 'Request failed'): string {
  if (error && typeof error === 'object') {
    const record = error as Record<string, unknown>;
    if (typeof record.detail === 'string') {
      return record.detail;
    }
    if (typeof record.message === 'string') {
      return record.message;
    }
    if (typeof record.error === 'string') {
      return record.error;
    }
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
}
