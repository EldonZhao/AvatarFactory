/**
 * API base URL utility for SSR pages
 *
 * In Docker: set ADMIN_API_BASE=http://avatarfactory:8000 (container service name)
 * In local dev: defaults to http://127.0.0.1:8000
 */
export function getApiBaseUrl(): string {
  // Server-side: use process.env (available at runtime)
  if (typeof process !== 'undefined' && process.env?.ADMIN_API_BASE) {
    return process.env.ADMIN_API_BASE;
  }
  // Fallback for local development
  return 'http://127.0.0.1:8000';
}
