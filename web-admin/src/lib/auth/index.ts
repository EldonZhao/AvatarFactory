/**
 * Auth utilities for Admin dashboard.
 * Handles login, logout, and session verification with JWT cookies.
 */

export interface LoginResponse {
  success: boolean;
  message: string;
  user?: {
    username: string;
  };
}

export interface VerifyResponse {
  valid: boolean;
  username?: string;
}

export interface User {
  username: string;
}

/**
 * Login with username and password.
 * On success, the server sets an HttpOnly cookie with the JWT.
 */
export async function login(username: string, password: string): Promise<LoginResponse> {
  const response = await fetch('/api/admin/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ username, password }),
    credentials: 'include', // Include cookies in request
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Login failed' }));
    return {
      success: false,
      message: error.detail || 'Invalid username or password',
    };
  }

  return response.json();
}

/**
 * Logout and clear the authentication cookie.
 */
export async function logout(): Promise<void> {
  await fetch('/api/admin/auth/logout', {
    method: 'POST',
    credentials: 'include',
  });
}

/**
 * Verify if the current session is valid.
 * Returns whether the user is authenticated.
 */
export async function verifyAuth(): Promise<VerifyResponse> {
  try {
    const response = await fetch('/api/admin/auth/verify', {
      credentials: 'include',
    });

    if (!response.ok) {
      return { valid: false };
    }

    return response.json();
  } catch {
    return { valid: false };
  }
}

/**
 * Get the current authenticated user info.
 * Throws if not authenticated.
 */
export async function getCurrentUser(): Promise<User | null> {
  try {
    const response = await fetch('/api/admin/auth/me', {
      credentials: 'include',
    });

    if (!response.ok) {
      return null;
    }

    return response.json();
  } catch {
    return null;
  }
}

/**
 * Check if we're on the client side.
 */
export function isClient(): boolean {
  return typeof window !== 'undefined';
}
