import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import tailwindcss from '@tailwindcss/vite';
import node from '@astrojs/node';

// Check for production build with /chronicle base
const isProduction = process.env.NODE_ENV === 'production' || process.env.ASTRO_BASE;
const base = isProduction ? '/chronicle' : '';

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
