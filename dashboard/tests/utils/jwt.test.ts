import { describe, it, expect } from 'vitest';
import { decodeJwtPayload } from '@/utils/jwt';

function makeJwt(payload: Record<string, unknown>): string {
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
  const body = btoa(JSON.stringify(payload));
  return `${header}.${body}.signature`;
}

describe('decodeJwtPayload', () => {
  it('decodes sub and role claims', () => {
    const token = makeJwt({ sub: 'alice', role: 'admin' });
    const payload = decodeJwtPayload(token);
    expect(payload).toEqual({ sub: 'alice', role: 'admin' });
  });

  it('returns null for a malformed token', () => {
    expect(decodeJwtPayload('')).toBeNull();
    expect(decodeJwtPayload('no-dots')).toBeNull();
    expect(decodeJwtPayload('a.b.c.d')).toBeNull();
  });

  it('returns null for invalid base64 payload', () => {
    expect(decodeJwtPayload('header.%%%not-base64%%%.sig')).toBeNull();
  });

  it('returns null for non-JSON payload', () => {
    const header = btoa(JSON.stringify({ alg: 'HS256' }));
    expect(decodeJwtPayload(`${header}.bm90LWpzb24=.sig`)).toBeNull();
  });
});
