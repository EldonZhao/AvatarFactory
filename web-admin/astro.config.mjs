import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import tailwindcss from '@tailwindcss/vite';
import node from '@astrojs/node';

// Check for production build with /admin base
const isProduction = process.env.NODE_ENV === 'production' || process.env.ASTRO_BASE;
const base = isProduction ? '/admin' : '';

export default defineConfig({
  integrations: [react()],
  base: base,
  vite: {
    plugins: [tailwindcss()],
    resolve: {
      alias: {
        '@': '/src'
      }
    }
    // Note: API requests are proxied via Astro middleware (src/middleware.ts)
    // not Vite proxy, because Astro SSR handles requests before Vite
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
