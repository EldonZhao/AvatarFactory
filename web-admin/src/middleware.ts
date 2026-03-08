import { defineMiddleware } from 'astro:middleware';

// Routes that don't require authentication (relative to base path)
const PUBLIC_ROUTES = ['/login', '/api/'];

// Get base path from environment, remove trailing slash for consistent path joining
const rawBasePath = import.meta.env.BASE_URL || '';
const BASE_PATH = rawBasePath.endsWith('/') ? rawBasePath.slice(0, -1) : rawBasePath;

// API base URL for proxying
const API_BASE = import.meta.env.API_BASE_URL || import.meta.env.ADMIN_API_BASE || 'http://127.0.0.1:8000';

// Check if a route is public
function isPublicRoute(pathname: string): boolean {
  // Strip base path if present for route matching
  const relativePath = BASE_PATH && pathname.startsWith(BASE_PATH)
    ? pathname.slice(BASE_PATH.length) || '/'
    : pathname;
  return PUBLIC_ROUTES.some(route => relativePath.startsWith(route) || relativePath === route);
}

// Build login URL with optional returnUrl parameter
function buildLoginUrl(returnPath?: string): string {
  const loginUrl = BASE_PATH ? `${BASE_PATH}/login` : '/login';

  // Calculate relative path first
  const relativePath = BASE_PATH && returnPath?.startsWith(BASE_PATH)
    ? returnPath.slice(BASE_PATH.length) || '/'
    : returnPath || '/';

  // Don't add returnUrl for root, base path, or login page itself
  const excludedPaths = ['/', '/login', ''];
  if (returnPath && !excludedPaths.includes(relativePath) &&
      returnPath !== BASE_PATH && returnPath !== `${BASE_PATH}/`) {
    return `${loginUrl}?returnUrl=${encodeURIComponent(relativePath)}`;
  }
  return loginUrl;
}

export const onRequest = defineMiddleware(async (context, next) => {
  const { pathname } = context.url;

  // Proxy API requests to backend
  if (pathname.startsWith('/api/')) {
    const targetUrl = `${API_BASE}${pathname}${context.url.search}`;

    // Forward the request to backend
    const headers = new Headers();
    context.request.headers.forEach((value, key) => {
      // Skip host header
      if (key.toLowerCase() !== 'host') {
        headers.set(key, value);
      }
    });

    try {
      const response = await fetch(targetUrl, {
        method: context.request.method,
        headers,
        body: context.request.method !== 'GET' && context.request.method !== 'HEAD'
          ? await context.request.text()
          : undefined,
      });

      // Create response with all headers from backend
      const responseHeaders = new Headers();
      response.headers.forEach((value, key) => {
        responseHeaders.set(key, value);
      });

      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: responseHeaders,
      });
    } catch (error) {
      console.error('API proxy error:', error);
      return new Response(JSON.stringify({ detail: 'Backend unavailable' }), {
        status: 502,
        headers: { 'Content-Type': 'application/json' },
      });
    }
  }

  // Allow public routes
  if (isPublicRoute(pathname)) {
    return next();
  }

  // Get the admin_token cookie
  const token = context.cookies.get('admin_token')?.value;

  // If no token, redirect to login with return URL
  if (!token) {
    return context.redirect(buildLoginUrl(pathname));
  }

  // Verify the token by calling the backend API
  try {
    // Use the internal API URL for server-side requests
    const apiBase = import.meta.env.API_BASE_URL || import.meta.env.ADMIN_API_BASE || 'http://127.0.0.1:8000';
    const response = await fetch(`${apiBase}/api/admin/auth/verify`, {
      headers: {
        Cookie: `admin_token=${token}`,
      },
    });

    if (!response.ok) {
      return context.redirect(buildLoginUrl(pathname));
    }

    const data = await response.json();

    if (!data.valid) {
      // Clear invalid cookie and redirect to login
      context.cookies.delete('admin_token', { path: '/' });
      return context.redirect(buildLoginUrl(pathname));
    }

    // Store user info in locals for use in pages
    context.locals.user = {
      username: data.username,
    };

  } catch (error) {
    // On verification error, redirect to login
    console.error('Auth verification error:', error);
    return context.redirect(buildLoginUrl(pathname));
  }

  return next();
});
