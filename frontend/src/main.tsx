import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PersistQueryClientProvider } from '@tanstack/react-query-persist-client';
import App from './App';
import { createAppPersister, PERSIST_MAX_AGE, shouldDehydrateQuery } from './lib/queryPersistence';
import { registerBackButton } from './lib/backButton';
import { initNativeChrome } from './lib/nativeChrome';
import { ensureAndroidChannel } from './lib/notifications';
import './index.css';

const queryClient = new QueryClient({
  defaultOptions: {
    // refetchOnWindowFocus: refresh stale data when the app returns to the
    // foreground. On native (WKWebView) the page never remounts on resume, so
    // without this, server-side changes (e.g. new quests/progress) only appear
    // after a full cold start. TanStack's focus manager listens to
    // `visibilitychange`, which fires when the app is foregrounded.
    // gcTime must be >= the persister's maxAge, otherwise allowlisted queries
    // are garbage-collected before they can be restored from disk.
    queries: { retry: 2, refetchOnWindowFocus: true, gcTime: PERSIST_MAX_AGE },
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

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
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
  </React.StrictMode>,
);

if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js');
}

registerBackButton();
void initNativeChrome();
void ensureAndroidChannel();
