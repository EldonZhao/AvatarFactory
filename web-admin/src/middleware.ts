import { defineMiddleware } from 'astro:middleware';

// Routes that don't require authentication (relative to base path)
const PUBLIC_ROUTES = ['/login', '/api/'];

// Get base path from environment, remove trailing slash for consistent path joining
const rawBasePath = import.meta.env.BASE_URL || '';
const BASE_PATH = rawBasePath.endsWith('/') ? rawBasePath.slice(0, -1) : rawBasePath;

// Check if a route is public
function isPublicRoute(pathname: string): boolean {
  // Strip base path if present for route matching
  const relativePath = BASE_PATH && pathname.startsWith(BASE_PATH)
    ? pathname.slice(BASE_PATH.length) || '/'
    : pathname;
  return PUBLIC_ROUTES.some(route => relativePath.startsWith(route) || relativePath === route);
}

export const onRequest = defineMiddleware(async (context, next) => {
  const { pathname } = context.url;

  // Allow public routes
  if (isPublicRoute(pathname)) {
    return next();
  }

  // Get the admin_token cookie
  const token = context.cookies.get('admin_token')?.value;

  // Build login redirect URL with base path
  const loginUrl = BASE_PATH ? `${BASE_PATH}/login` : '/login';

  // If no token, redirect to login
  if (!token) {
    return context.redirect(loginUrl);
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
      return context.redirect(loginUrl);
    }

    const data = await response.json();

    if (!data.valid) {
      // Clear invalid cookie and redirect to login
      context.cookies.delete('admin_token', { path: '/' });
      return context.redirect(loginUrl);
    }

    // Store user info in locals for use in pages
    context.locals.user = {
      username: data.username,
    };

  } catch (error) {
    // On verification error, redirect to login
    console.error('Auth verification error:', error);
    return context.redirect(loginUrl);
  }

  return next();
});
