import { create } from 'zustand';

/** Authenticated user identity derived from the JWT payload. */
export interface AuthUser {
  /** Subject (JWT `sub` claim) — the login username or API-key identity. */
  identity: string;
  /** Role (JWT `role` claim) — `admin` gates admin-only endpoints. */
  role: string;
}

interface AuthState {
  /** JWT access token, or null when signed out. */
  token: string | null;
  /** Decoded user identity, or null when signed out. */
  user: AuthUser | null;
  /** Persist credentials + decoded user after a successful login. */
  login: (token: string, user: AuthUser) => void;
  /** Clear credentials (called by the user or on a 401 response). */
  logout: () => void;
}

/** localStorage key for the raw JWT. */
export const AUTH_TOKEN_KEY = 'adl_auth_token';

/** localStorage key for the decoded user payload. */
export const AUTH_USER_KEY = 'adl_auth_user';

function readLocalStorage(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeLocalStorage(key: string, value: string): void {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // localStorage can be unavailable (privacy mode / tests); auth still
    // works for the current session even when persistence fails.
  }
}

function removeLocalStorage(key: string): void {
  try {
    window.localStorage.removeItem(key);
  } catch {
    // Ignore — nothing to recover from a failed removal.
  }
}

function readStoredUser(): AuthUser | null {
  const raw = readLocalStorage(AUTH_USER_KEY);
  if (!raw) {
    return null;
  }
  try {
    const parsed = JSON.parse(raw) as Partial<AuthUser>;
    if (typeof parsed.identity === 'string' && typeof parsed.role === 'string') {
      return { identity: parsed.identity, role: parsed.role };
    }
    return null;
  } catch {
    return null;
  }
}

/** Zustand auth store backed by localStorage persistence. */
export const useAuthStore = create<AuthState>((set) => ({
  token: readLocalStorage(AUTH_TOKEN_KEY),
  user: readStoredUser(),
  login: (token: string, user: AuthUser) => {
    writeLocalStorage(AUTH_TOKEN_KEY, token);
    writeLocalStorage(AUTH_USER_KEY, JSON.stringify(user));
    set({ token, user });
  },
  logout: () => {
    removeLocalStorage(AUTH_TOKEN_KEY);
    removeLocalStorage(AUTH_USER_KEY);
    set({ token: null, user: null });
  },
}));

/** Convenience predicate: is the user an admin (role === 'admin')? */
export function isAdminUser(user: AuthUser | null): boolean {
  return user !== null && user.role === 'admin';
}
