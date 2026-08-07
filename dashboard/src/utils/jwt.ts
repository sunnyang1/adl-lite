/** Decoded JWT payload claims (display-only — signature is NOT verified here). */
export interface DecodedJwtPayload {
  sub?: string;
  role?: string;
  exp?: number;
  [key: string]: unknown;
}

/**
 * Decode the payload segment of a JWT without verifying its signature.
 *
 * The backend signs tokens with HS256; the client only needs the claims for
 * display (identity + role). Signature verification happens server-side.
 *
 * @param token - Raw JWT string (`header.payload.signature`).
 * @returns The decoded payload, or null when the token is malformed.
 */
export function decodeJwtPayload(token: string): DecodedJwtPayload | null {
  try {
    const parts: string[] = token.split('.');
    if (parts.length < 2) {
      return null;
    }
    const base64Url: string = parts[1] ?? '';
    const base64: string = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const padded: string = base64.padEnd(Math.ceil(base64.length / 4) * 4, '=');
    const percentEncoded: string = atob(padded)
      .split('')
      .map((char) => `%${`00${char.charCodeAt(0).toString(16)}`.slice(-2)}`)
      .join('');
    return JSON.parse(decodeURIComponent(percentEncoded)) as DecodedJwtPayload;
  } catch {
    return null;
  }
}
