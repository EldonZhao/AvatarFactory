import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import tailwindcss from '@tailwindcss/vite';
import node from '@astrojs/node';

// Check for production build with /admin base
const isProduction = process.env.NODE_ENV === 'production' || process.env.ASTRO_BASE;
const base = isProduction ? '/admin' : '';

// API base URL for development proxy
const apiBase = process.env.ADMIN_API_BASE || 'http://localhost:8000';

export default defineConfig({
  integrations: [react()],
  base: base,
  vite: {
    plugins: [tailwindcss()],
    resolve: {
      alias: {
        '@': '/src'
      }
    },
    server: {
      proxy: {
        // Proxy all API routes to backend
        '/api': {
          target: apiBase,
          changeOrigin: true
        },
        '/personas': {
          target: apiBase,
          changeOrigin: true
        },
        '/chat': {
          target: apiBase,
          changeOrigin: true
        },
        '/scheduler': {
          target: apiBase,
          changeOrigin: true
        },
        '/connectors': {
          target: apiBase,
          changeOrigin: true
        },
        '/content': {
          target: apiBase,
          changeOrigin: true
        },
        '/health': {
          target: apiBase,
          changeOrigin: true
        },
        '/topology': {
          target: apiBase,
          changeOrigin: true
        }
      }
    }
  },
  // SSR mode for runtime data fetching from API
  output: 'server',
  adapter: node({
    mode: 'standalone'
  }),
  build: {
    assets: 'assets'
  }
});
