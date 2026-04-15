/**
 * API Proxy for Astro SSR
 *
 * This proxies all /api/* requests to the backend server,
 * preserving cookies for authentication.
 */
import type { APIRoute } from 'astro';

const API_BASE = import.meta.env.API_BASE_URL || 'http://localhost:8000';

export const ALL: APIRoute = async ({ request, params, cookies }) => {
  const path = params.path || '';
  const targetUrl = `${API_BASE}/api/${path}`;

  // Get all cookies to forward
  const cookieHeader = request.headers.get('cookie') || '';

  // Build headers, forwarding relevant ones
  const headers = new Headers();
  headers.set('Content-Type', request.headers.get('content-type') || 'application/json');
  if (cookieHeader) {
    headers.set('Cookie', cookieHeader);
  }

  // Forward the request
  const fetchOptions: RequestInit = {
    method: request.method,
    headers,
  };

  // Forward body for POST/PUT/PATCH/DELETE
  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(request.method)) {
    try {
      const body = await request.text();
      if (body) {
        fetchOptions.body = body;
      }
    } catch {
      // No body to forward
    }
  }

  try {
    const response = await fetch(targetUrl, fetchOptions);

    // Build response headers
    const responseHeaders = new Headers();

    // Forward Set-Cookie headers from backend
    const setCookie = response.headers.get('set-cookie');
    if (setCookie) {
      responseHeaders.set('Set-Cookie', setCookie);
    }

    // Forward content type
    const contentType = response.headers.get('content-type');
    if (contentType) {
      responseHeaders.set('Content-Type', contentType);
    }

    // Return the proxied response
    const responseBody = await response.text();
    return new Response(responseBody, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    });
  } catch (error) {
    console.error('API Proxy Error:', error);
    return new Response(JSON.stringify({ error: 'Proxy error', detail: String(error) }), {
      status: 502,
      headers: { 'Content-Type': 'application/json' },
    });
  }
};
