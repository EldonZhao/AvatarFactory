import { defineMiddleware } from 'astro:middleware';

// Routes that don't require authentication
const PUBLIC_ROUTES = ['/login', '/api/'];

// Check if a route is public
function isPublicRoute(pathname: string): boolean {
  return PUBLIC_ROUTES.some(route => pathname.startsWith(route) || pathname === route);
}

export const onRequest = defineMiddleware(async (context, next) => {
  const { pathname } = context.url;

  // Allow public routes
  if (isPublicRoute(pathname)) {
    return next();
  }

  // Get the admin_token cookie
  const token = context.cookies.get('admin_token')?.value;

  // If no token, redirect to login
  if (!token) {
    return context.redirect('/login');
  }

  // Verify the token by calling the backend API
  try {
    // Use the internal API URL for server-side requests
    const apiBase = import.meta.env.ADMIN_API_BASE || 'http://localhost:8000';
    const response = await fetch(`${apiBase}/api/admin/auth/verify`, {
      headers: {
        Cookie: `admin_token=${token}`,
      },
    });

    if (!response.ok) {
      return context.redirect('/login');
    }

    const data = await response.json();

    if (!data.valid) {
      // Clear invalid cookie and redirect to login
      context.cookies.delete('admin_token', { path: '/' });
      return context.redirect('/login');
    }

    // Store user info in locals for use in pages
    context.locals.user = {
      username: data.username,
    };

  } catch (error) {
    // On verification error, redirect to login
    console.error('Auth verification error:', error);
    return context.redirect('/login');
  }

  return next();
});
