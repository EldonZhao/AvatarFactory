import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import tailwindcss from '@tailwindcss/vite';

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
  output: 'static',
  build: {
    assets: 'assets'
  }
});
