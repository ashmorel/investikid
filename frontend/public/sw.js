// Minimal service worker — satisfies PWA install prompt.
// No caching, no fetch interception. Install-only.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));
