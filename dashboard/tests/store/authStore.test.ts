import { describe, it, expect, beforeEach, vi } from 'vitest';
import { AUTH_TOKEN_KEY, AUTH_USER_KEY } from '@/store/authStore';
import { isAdminUser } from '@/store/authStore';

/**
 * Load a fresh module instance of the auth store. The store reads
 * localStorage at module scope, so `vi.resetModules()` + dynamic import is
 * used to exercise the persistence-restore path deterministically.
 */
async function loadFreshStore(): Promise<typeof import('@/store/authStore')> {
  vi.resetModules();
  return import('@/store/authStore');
}

describe('authStore', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it('starts signed out with no token', async () => {
    const { useAuthStore } = await loadFreshStore();
    expect(useAuthStore.getState().token).toBeNull();
    expect(useAuthStore.getState().user).toBeNull();
    expect(isAdminUser(useAuthStore.getState().user)).toBe(false);
  });

  it('persists token and user after login', async () => {
    const { useAuthStore } = await loadFreshStore();
    useAuthStore.getState().login('jwt-token-123', {
      identity: 'alice',
      role: 'admin',
    });

    expect(useAuthStore.getState().token).toBe('jwt-token-123');
    expect(useAuthStore.getState().user).toEqual({
      identity: 'alice',
      role: 'admin',
    });
    expect(window.localStorage.getItem(AUTH_TOKEN_KEY)).toBe('jwt-token-123');
    expect(isAdminUser(useAuthStore.getState().user)).toBe(true);
  });

  it('clears credentials after logout', async () => {
    const { useAuthStore } = await loadFreshStore();
    useAuthStore.getState().login('jwt-token-123', {
      identity: 'alice',
      role: 'user',
    });
    useAuthStore.getState().logout();

    expect(useAuthStore.getState().token).toBeNull();
    expect(useAuthStore.getState().user).toBeNull();
    expect(window.localStorage.getItem(AUTH_TOKEN_KEY)).toBeNull();
    expect(window.localStorage.getItem(AUTH_USER_KEY)).toBeNull();
  });

  it('restores a persisted session on store creation', async () => {
    window.localStorage.setItem(AUTH_TOKEN_KEY, 'restored-token');
    window.localStorage.setItem(
      AUTH_USER_KEY,
      JSON.stringify({ identity: 'bob', role: 'user' }),
    );

    const { useAuthStore } = await loadFreshStore();
    expect(useAuthStore.getState().token).toBe('restored-token');
    expect(useAuthStore.getState().user).toEqual({
      identity: 'bob',
      role: 'user',
    });
  });

  it('ignores corrupted persisted user data', async () => {
    window.localStorage.setItem(AUTH_TOKEN_KEY, 'token');
    window.localStorage.setItem(AUTH_USER_KEY, '{not-json');

    const { useAuthStore } = await loadFreshStore();
    expect(useAuthStore.getState().token).toBe('token');
    expect(useAuthStore.getState().user).toBeNull();
  });
});
