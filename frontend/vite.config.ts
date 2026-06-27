import { defineConfig } from 'vitest/config';
import { loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { VitePWA } from 'vite-plugin-pwa';
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

export default defineConfig(({ mode }) => {
  // Vite's `import.meta.env` client replacement reads ONLY .env files, never the
  // build-time process environment — so a Vercel/CI-injected VITE_API_BASE_URL
  // is silently dropped, the web bundle ships an empty API base, and every
  // same-origin /auth call 405s (login breaks). `loadEnv` DOES merge process.env,
  // so we surface these two public config values through custom define globals
  // (Vite won't clobber a non-`import.meta.env` identifier). client.ts /
  // videoEmbed.ts still prefer import.meta.env first, so .env-file and test
  // overrides keep working; the global is the build-time fallback.
  const env = loadEnv(mode, process.cwd(), 'VITE_');
  return {
  define: {
    __API_BASE__: JSON.stringify(env.VITE_API_BASE_URL || ''),
    __WEB_ORIGIN__: JSON.stringify(env.VITE_WEB_ORIGIN || ''),
  },
  build: {
    rollupOptions: {
      output: {
        // Split stable vendors into their own chunks so they stay cached across
        // app releases (and so charts/motion aren't entangled with app code).
        // recharts only ships in the lazy chart routes; this keeps it in one
        // shared chunk loaded on demand rather than duplicated per route.
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          charts: ['recharts'],
          motion: ['framer-motion'],
          query: ['@tanstack/react-query', '@tanstack/react-query-persist-client'],
        },
      },
    },
  },
  plugins: [
    react(),
    tailwindcss(),
    stripCrossorigin(),
    VitePWA({
      registerType: 'autoUpdate',
      injectRegister: 'auto',
      manifest: false,
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
      },
      devOptions: { enabled: false },
    }),
  ],
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
  };
});
