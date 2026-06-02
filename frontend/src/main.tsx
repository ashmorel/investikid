import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './App';
import './index.css';

const queryClient = new QueryClient({
  defaultOptions: {
    // refetchOnWindowFocus: refresh stale data when the app returns to the
    // foreground. On native (WKWebView) the page never remounts on resume, so
    // without this, server-side changes (e.g. new quests/progress) only appear
    // after a full cold start. TanStack's focus manager listens to
    // `visibilitychange`, which fires when the app is foregrounded.
    queries: { retry: 2, refetchOnWindowFocus: true },
    mutations: { retry: 0 },
  },
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
);

if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js');
}
