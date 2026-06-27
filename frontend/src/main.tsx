import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PersistQueryClientProvider } from '@tanstack/react-query-persist-client';
import { I18nextProvider } from 'react-i18next';
import App from './App';
import { createAppPersister, PERSIST_MAX_AGE, shouldDehydrateQuery } from './lib/queryPersistence';
import { registerBackButton } from './lib/backButton';
import { initNativeChrome } from './lib/nativeChrome';
import { ensureAndroidChannel } from './lib/notifications';
import { i18n, initI18n } from './i18n';
import { resolveBootLanguage } from './i18n/resolveLanguage';
import './index.css';

// Marker read by the boot watchdog in index.html: confirms the entry module
// actually executed (vs. being blocked from loading). See index.html.
(window as unknown as { __bootStarted?: boolean }).__bootStarted = true;

const queryClient = new QueryClient({
  defaultOptions: {
    // refetchOnWindowFocus: refresh stale data when the app returns to the
    // foreground. On native (WKWebView) the page never remounts on resume, so
    // without this, server-side changes (e.g. new quests/progress) only appear
    // after a full cold start. TanStack's focus manager listens to
    // `visibilitychange`, which fires when the app is foregrounded.
    // gcTime must be >= the persister's maxAge, otherwise allowlisted queries
    // are garbage-collected before they can be restored from disk.
    // staleTime floor: without it every query is stale-on-arrival, so each
    // foreground (visibilitychange) refetches *everything* at once — a refetch
    // storm on resume. 30s collapses rapid focus flaps while still refreshing
    // genuinely stale data; per-query staleTime overrides still win.
    queries: { retry: 2, refetchOnWindowFocus: true, staleTime: 30_000, gcTime: PERSIST_MAX_AGE },
    mutations: { retry: 0 },
  },
});

// Persist allowlisted queries to localStorage so previously-seen content
// renders instantly and stays readable offline. If localStorage is unusable
// (e.g. private browsing), fall back silently to the in-memory cache.
const persister = createAppPersister();

const appTree = (
  <BrowserRouter>
    <App />
  </BrowserRouter>
);

const rootTree = (
  <React.StrictMode>
    <I18nextProvider i18n={i18n}>
      {persister ? (
        <PersistQueryClientProvider
          client={queryClient}
          persistOptions={{
            persister,
            maxAge: PERSIST_MAX_AGE,
            dehydrateOptions: { shouldDehydrateQuery },
          }}
        >
          {appTree}
        </PersistQueryClientProvider>
      ) : (
        <QueryClientProvider client={queryClient}>{appTree}</QueryClientProvider>
      )}
    </I18nextProvider>
  </React.StrictMode>
);

async function bootstrap() {
  await initI18n(await resolveBootLanguage());

  ReactDOM.createRoot(document.getElementById('root')!).render(rootTree);

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js');
  }

  registerBackButton();
  void initNativeChrome();
  void ensureAndroidChannel();
}

bootstrap().catch((err) => {
  console.error('[bootstrap] i18n init failed; rendering without preloaded i18n:', err);
  ReactDOM.createRoot(document.getElementById('root')!).render(rootTree);
});
