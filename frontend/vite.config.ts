import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import path from 'node:path';

/**
 * Vite stamps the bundled entry tags as `<script type="module" crossorigin>`
 * (and the stylesheet link likewise). Under the iOS `capacitor://localhost`
 * custom scheme, WKWebView applies a CORS check to that crossorigin module
 * fetch and rejects it, so the entry module never executes — the app shows a
 * blank white screen with no login and no JS error. At an https origin (the
 * web build and Android's `androidScheme: 'https'`) the attribute is harmless,
 * which is why the bug is iOS-only. Strip it so the native WKWebView loads the
 * bundle. Build-only; the dev server is unaffected.
 */
function stripCrossorigin() {
  return {
    name: 'strip-crossorigin',
    transformIndexHtml(html: string) {
      return html.replace(/\s+crossorigin(?:=["'][^"']*["'])?/g, '');
    },
  };
}

export default defineConfig({
  plugins: [react(), tailwindcss(), stripCrossorigin()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  server: {
    port: 5173,
    proxy: {
      '/auth': 'http://localhost:8000',
      '/users': 'http://localhost:8000',
      '/modules': {
        target: 'http://localhost:8000',
        bypass(req) {
          if (req.headers.accept?.includes('text/html')) return '/index.html';
        },
      },
      '/lessons': {
        target: 'http://localhost:8000',
        bypass(req) {
          if (req.headers.accept?.includes('text/html')) return '/index.html';
        },
      },
      '/consent': {
        target: 'http://localhost:8000',
        bypass(req) {
          // Let browser navigation (text/html) fall through to index.html (SPA routing).
          // Only proxy JSON API calls.
          if (req.headers.accept?.includes('text/html')) return '/index.html';
        },
      },
      '/parent': {
        target: 'http://localhost:8000',
        bypass(req) {
          if (req.headers.accept?.includes('text/html')) return '/index.html';
        },
      },
      '/market': {
        target: 'http://localhost:8000',
        bypass(req) {
          if (req.headers.accept?.includes('text/html')) return '/index.html';
        },
      },
      '/portfolio': {
        target: 'http://localhost:8000',
        bypass(req) {
          if (req.headers.accept?.includes('text/html')) return '/index.html';
        },
      },
      '/challenges': {
        target: 'http://localhost:8000',
        bypass(req) {
          if (req.headers.accept?.includes('text/html')) return '/index.html';
        },
      },
      '/leaderboard': {
        target: 'http://localhost:8000',
        bypass(req) {
          if (req.headers.accept?.includes('text/html')) return '/index.html';
        },
      },
      '/badges': {
        target: 'http://localhost:8000',
        bypass(req) {
          if (req.headers.accept?.includes('text/html')) return '/index.html';
        },
      },
      '/tutor': {
        target: 'http://localhost:8000',
      },
      '/recommendations': {
        target: 'http://localhost:8000',
      },
      '/profile/mastery': {
        target: 'http://localhost:8000',
      },
      '/health': 'http://localhost:8000',
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './tests/setup.ts',
    css: false,
    exclude: ['node_modules', 'dist', 'tests/e2e/**'],
  },
});
